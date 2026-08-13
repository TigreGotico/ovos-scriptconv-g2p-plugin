"""OPM Grapheme2Phoneme plugin backed by scriptconv's phonemizer registry.

scriptconv (https://github.com/TigreGotico/scriptconv) ships 45 phonemizer
backends behind a single registry and normalizes every one of them to IPA
output on request (``Alphabet.IPA``) - including backends that natively emit
ARPABET/X-SAMPA/etc, since notation conversion is exactly what scriptconv is
for. This plugin is a thin adapter: it does not implement any phonemization
itself, it only exposes scriptconv's registry through the OVOS Plugin
Manager G2P contract.

Which phonemizer runs is a matter of config, nothing else - set
``phonemizer`` to any :class:`scriptconv.phonemizers.Phonemizer` registry
name (``espeak``, ``orthography2ipa``, ``tugaphone``, ...). When unset,
scriptconv's own ``LANG_DEFAULTS``/fallback chain (explicit per-language
default -> orthography2ipa -> espeak) picks the backend per word, exactly as
``scriptconv.phonemizers.phonemize()`` does standalone.
"""
from typing import Optional, Set

from ovos_plugin_manager.templates.g2p import Grapheme2PhonemePlugin, OutOfVocabulary
from ovos_utils.log import LOG
from scriptconv.phonemizers import (
    Alphabet,
    LANG_DEFAULTS,
    Phonemizer,
    get_phonemizer_class,
    phonemize,
)

from ovos_scriptconv_g2p_plugin.version import __version__

# reserved config keys consumed by this plugin; everything else in the
# config dict is forwarded to scriptconv as phonemizer constructor kwargs
# (e.g. "model"/"engine"/"register" selectors, "normalizer", ...)
_RESERVED_KEYS = {"phonemizer", "lang", "module"}


class ScriptconvG2PPlugin(Grapheme2PhonemePlugin):
    """Grapheme2Phoneme plugin that delegates to scriptconv.

    Config:
        phonemizer (str, optional): registry name of the scriptconv
            phonemizer to use, e.g. ``"espeak"``, ``"orthography2ipa"``,
            ``"tugaphone"``. When omitted, scriptconv's per-language
            ``LANG_DEFAULTS``/fallback chain selects the backend.
        lang (str, optional): default language code used when callers don't
            pass one explicitly.

        Any other key is forwarded as a keyword argument to the underlying
        scriptconv phonemizer constructor (``model``, ``normalizer``, ...).
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        phonemizer_name = self.config.get("phonemizer")
        self.phonemizer: Optional[Phonemizer] = (
            Phonemizer(phonemizer_name) if phonemizer_name else None
        )
        self.default_lang = self.config.get("lang", "en-us")
        self._backend_kwargs = {
            k: v for k, v in self.config.items() if k not in _RESERVED_KEYS
        }

    def get_ipa(self, word, lang: Optional[str] = None, ignore_oov: bool = False):
        """Return the IPA phonemes for *word* as a list of characters.

        scriptconv is asked for ``Alphabet.IPA`` output directly - any
        backend that natively emits a different notation (ARPABET,
        X-SAMPA, ...) is converted internally by scriptconv before it
        reaches us, so callers always see IPA here regardless of which
        phonemizer is configured.
        """
        lang = lang or self.default_lang
        try:
            ipa_str = phonemize(
                word,
                lang,
                alphabet=Alphabet.IPA,
                override=self.phonemizer,
                **self._backend_kwargs,
            )
        except ImportError:
            # configured-but-missing backing package: scriptconv already
            # raises a clear, actionable error (names the pip extra) -
            # never swallow this behind ignore_oov, it's a config/env
            # problem, not an out-of-vocabulary word
            raise
        except (ValueError, KeyError) as e:
            LOG.debug(f"scriptconv could not phonemize {word!r} ({lang}): {e}")
            if ignore_oov:
                return None
            raise OutOfVocabulary(str(e)) from e
        if not ipa_str:
            if ignore_oov:
                return None
            raise OutOfVocabulary(f"empty phonemization for: {word!r}")
        return list(ipa_str)

    @property
    def available_languages(self) -> Set[str]:
        """Languages supported by the configured phonemizer.

        scriptconv's 45 backends expose language coverage inconsistently
        (some declare a ``*_LANGS`` list, some a ``supported_langs()``
        classmethod, some validate lazily per-call with no static list at
        all) so this is best-effort:

        - a specific ``phonemizer`` configured: read whatever static
          metadata that backend's class exposes (``ESPEAK_LANGS``,
          ``supported_langs()``); if the backend exposes none, fall back to
          the language(s) it is the declared default for in
          ``LANG_DEFAULTS``.
        - no ``phonemizer`` configured: scriptconv's own fallback chain
          (explicit defaults -> orthography2ipa -> espeak) can in practice
          cover essentially any language, so this returns the union of
          every language with an explicit ``LANG_DEFAULTS`` entry as a
          floor, not an exhaustive list.
        """
        if self.phonemizer is None:
            return set(LANG_DEFAULTS.keys())
        return self._langs_for(self.phonemizer)

    @staticmethod
    def _langs_for(phonemizer: Phonemizer) -> Set[str]:
        try:
            cls = get_phonemizer_class(phonemizer)
        except ImportError:
            cls = None
        langs: Set[str] = set()
        if cls is not None:
            for attr in ("ESPEAK_LANGS", "SUPPORTED_LANGS", "LANGS"):
                val = getattr(cls, attr, None)
                if val:
                    langs.update(val)
                    break
            if not langs and hasattr(cls, "supported_langs"):
                try:
                    langs.update(cls.supported_langs())
                except Exception as e:
                    LOG.debug(f"could not introspect supported_langs for {cls}: {e}")
        if not langs:
            langs = {
                lang
                for lang, chain in LANG_DEFAULTS.items()
                if phonemizer in chain
            }
        return langs
