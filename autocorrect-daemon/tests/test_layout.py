"""
Tests unitaires pour la gestion des layouts de clavier (AZERTY et QWERTY).
"""

import unittest
from src.keyboard.layout import (
    KeyboardLayout,
    KEY_A,
    KEY_Q,
    KEY_Z,
    KEY_W,
    KEY_2,
    KEY_SEMICOLON,
    KEY_SPACE,
    KEY_BACKSPACE,
)


class TestKeyboardLayout(unittest.TestCase):

    def setUp(self):
        self.azerty = KeyboardLayout("azerty")
        self.qwerty = KeyboardLayout("qwerty")

    def test_azerty_scancode_to_char(self):
        # En AZERTY :
        # KEY_A -> 'q', Shift+KEY_A -> 'Q'
        self.assertEqual(self.azerty.scancode_to_char(KEY_A, shift=False), "q")
        self.assertEqual(self.azerty.scancode_to_char(KEY_A, shift=True), "Q")

        # KEY_Q -> 'a', Shift+KEY_Q -> 'A'
        self.assertEqual(self.azerty.scancode_to_char(KEY_Q, shift=False), "a")
        self.assertEqual(self.azerty.scancode_to_char(KEY_Q, shift=True), "A")

        # KEY_2 -> 'é', Shift+KEY_2 -> '2'
        self.assertEqual(self.azerty.scancode_to_char(KEY_2, shift=False), "é")
        self.assertEqual(self.azerty.scancode_to_char(KEY_2, shift=True), "2")

        # KEY_SEMICOLON -> 'm'
        self.assertEqual(self.azerty.scancode_to_char(KEY_SEMICOLON, shift=False), "m")

    def test_qwerty_scancode_to_char(self):
        # En QWERTY :
        # KEY_A -> 'a', Shift+KEY_A -> 'A'
        self.assertEqual(self.qwerty.scancode_to_char(KEY_A, shift=False), "a")
        self.assertEqual(self.qwerty.scancode_to_char(KEY_A, shift=True), "A")

        # KEY_Q -> 'q', Shift+KEY_Q -> 'Q'
        self.assertEqual(self.qwerty.scancode_to_char(KEY_Q, shift=False), "q")
        self.assertEqual(self.qwerty.scancode_to_char(KEY_Q, shift=True), "Q")

    def test_reverse_injection_azerty(self):
        # Vérifie qu'on sait quelle touche envoyer pour taper 'é' en AZERTY
        inj_e_acute = self.azerty.char_to_injection("é")
        self.assertIsNotNone(inj_e_acute)
        code, shift, altgr = inj_e_acute
        self.assertEqual(code, KEY_2)
        self.assertFalse(shift)
        self.assertFalse(altgr)

        # Vérifie qu'on sait comment taper 'A' en AZERTY (Shift + KEY_Q)
        inj_cap_a = self.azerty.char_to_injection("A")
        self.assertIsNotNone(inj_cap_a)
        code, shift, altgr = inj_cap_a
        self.assertEqual(code, KEY_Q)
        self.assertTrue(shift)

        # Vérifie l'espace
        inj_space = self.azerty.char_to_injection(" ")
        self.assertIsNotNone(inj_space)
        code, shift, altgr = inj_space
        self.assertEqual(code, KEY_SPACE)

    def test_dead_keys_azerty(self):
        # Vérifie les voyelles avec accent circonflexe (touche morte ^ puis lettre)
        e_circ = self.azerty.char_to_injections("ê")
        self.assertEqual(len(e_circ), 2)
        # 1ère étape : touche morte ^ (KEY_LEFTBRACE = 26)
        self.assertEqual(e_circ[0], (26, False, False))
        # 2ème étape : touche 'e' (KEY_E = 18)
        self.assertEqual(e_circ[1], (18, False, False))


if __name__ == "__main__":
    unittest.main()
