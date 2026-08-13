# ovos-scriptconv-g2p-plugin

An OVOS Plugin Manager (OPM) [Grapheme2Phoneme](https://github.com/OpenVoiceOS/ovos-plugin-manager) plugin.

This plugin does not phonemize text itself. It is a thin adapter over
[scriptconv](https://github.com/TigreGotico/scriptconv)'s phonemizer
registry, which bundles 45 phonemizer backends behind one API and converts
every one of them to IPA on request - including backends that natively
emit ARPABET, X-SAMPA, or another notation, since notation conversion is
scriptconv's whole reason to exist.

Which backend runs is a matter of config, nothing else. Point `phonemizer`
at any [`scriptconv.phonemizers.Phonemizer`](https://github.com/TigreGotico/scriptconv)
registry name and this plugin uses it. Leave it unset and scriptconv's own
per-language `LANG_DEFAULTS`/fallback chain (explicit default ->
[orthography2ipa](https://github.com/TigreGotico/orthography2ipa) -> espeak)
picks a backend per word, same as calling `scriptconv.phonemizers.phonemize()`
directly.

Benchmarked and compared against the other G2P plugins in the
[ovos-plugin-arena](https://github.com/TigreGotico/ovos-plugin-arena).

## Install

```bash
pip install ovos-scriptconv-g2p-plugin
```

`scriptconv` and `ovos-plugin-manager` are the only hard dependencies.
Individual phonemizer backends are optional - scriptconv lazy-imports them,
and installing this plugin does **not** pull in any of the 45 backing
packages. If you configure a backend whose package isn't installed, you get
a clear `ImportError` naming the pip extra to install, e.g.:

```bash
pip install scriptconv[espeak]        # espeak backend
pip install scriptconv[o2i]           # orthography2ipa backend
pip install scriptconv[pt-phonemizers]  # tugaphone backend
```

See scriptconv's `pyproject.toml` for the full extras list - one per
backend or language family.

## Configuration

```json
"g2p": {
    "module": "ovos-scriptconv-g2p-plugin",
    "ovos-scriptconv-g2p-plugin": {
        "phonemizer": "espeak",
        "lang": "en-us"
    }
}
```

- `phonemizer` (optional): registry name of the scriptconv phonemizer to
  use, e.g. `"espeak"`, `"orthography2ipa"`, `"tugaphone"`. Omit it to let
  scriptconv pick the default backend per language.
- `lang` (optional): default language used when a caller doesn't pass one
  explicitly.
- any other key is forwarded as a keyword argument to the underlying
  scriptconv phonemizer constructor (`model`, `normalizer`, ...).

## Usage

```python
from ovos_plugin_manager.g2p import OVOSG2PFactory

config = {"g2p": {"module": "ovos-scriptconv-g2p-plugin",
                   "ovos-scriptconv-g2p-plugin": {"phonemizer": "espeak"}}}
g2p = OVOSG2PFactory.create(config)
print(g2p.get_ipa("hello", "en-us"))
```

## Links

- [scriptconv](https://github.com/TigreGotico/scriptconv) - the phonemizer
  registry and notation converter this plugin wraps
- [ovos-plugin-manager](https://github.com/OpenVoiceOS/ovos-plugin-manager) -
  defines the `Grapheme2PhonemePlugin` contract this plugin implements
- [ovos-plugin-arena](https://github.com/TigreGotico/ovos-plugin-arena) -
  benchmarks this plugin against other G2P engines
