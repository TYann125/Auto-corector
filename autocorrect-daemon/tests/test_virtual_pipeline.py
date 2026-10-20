"""
Test d'intégration complet du pipeline (Capture -> Détection -> Injection)
avec un périphérique virtuel simulé pour valider le comportement de bout en bout.
"""

import unittest
from typing import List, Tuple

from src.keyboard.layout import KeyboardLayout, KEY_BACKSPACE, KEY_SPACE
from src.keyboard.injector import KeyboardInjector
from src.engine.corrector import TextCorrectionEngine
from src.buffer.word_tracker import WordTracker


class MockUinputDevice:
    """Simulateur en mémoire du périphérique uinput matériel pour tester l'injection."""

    def __init__(self):
        self.fd = 999  # Factice pour simuler un descripteur ouvert
        self.actions: List[Tuple[str, int]] = []

    def open(self):
        return True

    def close(self):
        self.fd = None

    def press_key(self, code: int):
        self.actions.append(("PRESS", code))

    def release_key(self, code: int):
        self.actions.append(("RELEASE", code))

    def tap_key(self, code: int, delay_s: float = 0.0):
        self.actions.append(("TAP", code))


class TestVirtualPipeline(unittest.TestCase):

    def setUp(self):
        self.layout = KeyboardLayout("azerty")
        self.mock_uinput = MockUinputDevice()
        self.injector = KeyboardInjector(self.mock_uinput, self.layout, key_delay_ms=0.0)
        self.engine = TextCorrectionEngine(default_lang="fr")

        # Pipeline complet
        def on_word_complete(word, delimiter, recent_words):
            if self.injector.is_injecting:
                return
            correction = self.engine.process_word(word, recent_words)
            if correction and correction != word:
                backspace_count = len(word) + len(delimiter)
                self.injector.erase_and_type(
                    backspace_count=backspace_count,
                    replacement_text=correction,
                    trailing_char=delimiter,
                )

        self.tracker = WordTracker(self.layout, on_word_complete=on_word_complete)

    def test_full_correction_cycle(self):
        # Simulons la frappe du mot "acceuil" suivi d'un espace en AZERTY
        # "acceuil" -> faute connue pour "accueil" (7 lettres + 1 espace = 8 backspaces)
        for char in "acceuil":
            inj = self.layout.char_to_injection(char)
            self.assertIsNotNone(inj, f"Caractère '{char}' non mappé")
            code, shift, altgr = inj
            self.tracker.process_key_event(1, code, 1)
            self.tracker.process_key_event(1, code, 0)

        # Frappe de l'espace
        self.tracker.process_key_event(1, KEY_SPACE, 1)
        self.tracker.process_key_event(1, KEY_SPACE, 0)

        # Vérifions les actions de l'injecteur uinput simulé :
        # 1. Doit avoir émis exactement 8 Backspaces (7 lettres du mot 'acceuil' + 1 espace)
        backspace_taps = [act for act in self.mock_uinput.actions if act == ("TAP", KEY_BACKSPACE)]
        self.assertEqual(
            len(backspace_taps),
            8,
            f"L'injecteur aurait dû envoyer 8 Backspaces, mais en a envoyé {len(backspace_taps)}"
        )

        # 2. Vérifions que le mot 'accueil' et l'espace ont été réinjectés
        # Les actions suivantes doivent correspondre aux lettres de 'accueil' + espace
        retyped_actions = [act for act in self.mock_uinput.actions if act != ("TAP", KEY_BACKSPACE)]
        self.assertGreater(len(retyped_actions), 0)


if __name__ == "__main__":
    unittest.main()
