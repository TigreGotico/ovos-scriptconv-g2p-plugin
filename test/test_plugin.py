import unittest

from ovos_scriptconv_g2p_plugin import ScriptconvG2PPlugin


class TestScriptconvG2PPlugin(unittest.TestCase):

    def test_entry_point_resolution(self):
        """the plugin resolves through OVOSG2PFactory via its opm.g2p entry point"""
        from ovos_plugin_manager.g2p import OVOSG2PFactory
        config = {"module": "ovos-scriptconv-g2p-plugin"}
        clazz = OVOSG2PFactory.get_class(config)
        self.assertIs(clazz, ScriptconvG2PPlugin)

    def test_factory_create(self):
        from ovos_plugin_manager.g2p import OVOSG2PFactory
        config = {"g2p": {"module": "ovos-scriptconv-g2p-plugin",
                           "ovos-scriptconv-g2p-plugin": {"phonemizer": "espeak"}}}
        g2p = OVOSG2PFactory.create(config)
        self.assertIsInstance(g2p, ScriptconvG2PPlugin)
        self.assertEqual(g2p.phonemizer.value, "espeak")

    def test_espeak_configured_phonemizer_is_honored(self):
        """when a phonemizer is configured, it (not the scriptconv default) is used"""
        plug = ScriptconvG2PPlugin({"phonemizer": "espeak"})
        ipa = plug.get_ipa("hello", "en-us")
        self.assertIsInstance(ipa, list)
        self.assertTrue(all(isinstance(p, str) for p in ipa))
        self.assertGreater(len(ipa), 0)
        # espeak's IPA for "hello" contains an 'l' articulation
        self.assertIn("l", "".join(ipa))

    def test_lang_defaults_fallback_when_unconfigured(self):
        """no phonemizer configured -> scriptconv's LANG_DEFAULTS/fallback chain decides"""
        plug = ScriptconvG2PPlugin({})
        self.assertIsNone(plug.phonemizer)
        ipa = plug.get_ipa("hello", "en-us")
        self.assertIsInstance(ipa, list)
        self.assertGreater(len(ipa), 0)

    def test_unicode_grapheme_fallback(self):
        """the 'unicode'/'graphemes' backends never fail to produce SOME output"""
        plug = ScriptconvG2PPlugin({"phonemizer": "graphemes"})
        ipa = plug.get_ipa("xyz", "en-us")
        self.assertIsInstance(ipa, list)
        self.assertGreater(len(ipa), 0)

    def test_orthography2ipa_pt(self):
        """orthography2ipa is installed in this env - exercise a real lattice phonemizer"""
        plug = ScriptconvG2PPlugin({"phonemizer": "orthography2ipa"})
        ipa = plug.get_ipa("mundo", "pt")
        self.assertIsInstance(ipa, list)
        self.assertGreater(len(ipa), 0)
        joined = "".join(ipa)
        self.assertIn("m", joined)

    def test_missing_backend_raises_clear_error(self):
        """a configured-but-uninstalled backend must raise ImportError naming the extra,
        never be silently swallowed by ignore_oov"""
        # goruut backend needs pygoruut, not installed in this env
        plug = ScriptconvG2PPlugin({"phonemizer": "goruut"})
        with self.assertRaises(ImportError) as ctx:
            plug.get_ipa("hello", "en-us", ignore_oov=True)
        self.assertIn("scriptconv[", str(ctx.exception))

    def test_invalid_phonemizer_name_raises_at_construction(self):
        with self.assertRaises(ValueError):
            ScriptconvG2PPlugin({"phonemizer": "not-a-real-backend"})

    def test_available_languages_configured(self):
        plug = ScriptconvG2PPlugin({"phonemizer": "espeak"})
        langs = plug.available_languages
        self.assertIsInstance(langs, set)
        self.assertGreater(len(langs), 0)

    def test_available_languages_unconfigured_uses_lang_defaults(self):
        from scriptconv.phonemizers import LANG_DEFAULTS
        plug = ScriptconvG2PPlugin({})
        langs = plug.available_languages
        self.assertEqual(langs, set(LANG_DEFAULTS.keys()))


if __name__ == "__main__":
    unittest.main()
