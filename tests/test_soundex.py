import unittest

from famdb_helper_methods import soundex, sounds_like


class TestSoundex(unittest.TestCase):
    def test_soundex(self):
        # Some examples from https://en.wikipedia.org/wiki/Soundex
        self.assertEqual(soundex("Robert"), "R163")
        self.assertEqual(soundex("Rupert"), "R163")
        self.assertEqual(soundex("Rubin"), "R150")
        self.assertEqual(soundex("Ashcraft"), "A261")
        self.assertEqual(soundex("Ashcroft"), "A261")
        self.assertEqual(soundex("Tymczak"), "T522")
        self.assertEqual(soundex("Pfister"), "P236")
        self.assertEqual(soundex("Honeyman"), "H555")

        # A few typos we should be able to catch
        self.assertTrue(sounds_like("Homo", "Humo"))
        self.assertTrue(sounds_like("Musculs", "Musculus"))

        # A few difficult-to-spell names.
        #
        # TODO: In the future we should consider using an algorithm other
        # than soundex or make exceptions, so that some of these similar
        # sounds are discovered
        self.assertEqual(soundex("Cnidaria"), "C536")
        self.assertEqual(soundex("Nidaria"), "N360")
        self.assertEqual(soundex("Cichlidae"), "C243")
        self.assertEqual(soundex("Siklids"), "S243")
