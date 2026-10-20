"""
Tests unitaires pour la machine à états de suivi des touches (WordTracker).
"""

import unittest
from src.keyboard.layout import (
    KeyboardLayout,
    KEY_Q,
    KEY_W,
    KEY_E,
    KEY_LEFTSHIFT,
    KEY_SPACE,
    KEY_BACKSPACE,
    KEY_SEMICOLON,
)
from src.buffer.word_tracker import WordTracker


class TestWordTracker(unittest.TestCase):

    def setUp(self):
        self.layout = KeyboardLayout("azerty")
        self.captured_words = []

        def on_complete(word, delim, recents):
            self.captured_words.append((word, delim, recents))

        self.tracker = WordTracker(self.layout, on_word_complete=on_complete)

    def test_word_reconstruction_azerty(self):
        # En AZERTY, taper KEY_Q produit 'a', KEY_SEMICOLON produit 'm', KEY_E produit 'e'
        # Tapons 'a' -> 'm' -> 'i' ...
        # Testons : appui KEY_Q (1), relâchement (0)
        self.tracker.process_key_event(1, KEY_Q, 1)
        self.tracker.process_key_event(1, KEY_Q, 0)

        # Appui KEY_SEMICOLON (m)
        self.tracker.process_key_event(1, KEY_SEMICOLON, 1)
        self.tracker.process_key_event(1, KEY_SEMICOLON, 0)

        # Appui KEY_E (e)
        self.tracker.process_key_event(1, KEY_E, 1)
        self.tracker.process_key_event(1, KEY_E, 0)

        # Appui Espace (KEY_SPACE) -> déclenche la complétion
        self.tracker.process_key_event(1, KEY_SPACE, 1)
        self.tracker.process_key_event(1, KEY_SPACE, 0)

        self.assertEqual(len(self.captured_words), 1)
        word, delim, recents = self.captured_words[0]
        self.assertEqual(word, "ame")
        self.assertEqual(delim, " ")

    def test_backspace_handling(self):
        # Tape 'a' (KEY_Q), puis 'z' (KEY_W), puis Backspace, puis 'm' (KEY_SEMICOLON), puis Espace
        self.tracker.process_key_event(1, KEY_Q, 1)
        self.tracker.process_key_event(1, KEY_Q, 0)

        self.tracker.process_key_event(1, KEY_W, 1)
        self.tracker.process_key_event(1, KEY_W, 0)

        # Backspace
        self.tracker.process_key_event(1, KEY_BACKSPACE, 1)
        self.tracker.process_key_event(1, KEY_BACKSPACE, 0)

        # Tape 'm'
        self.tracker.process_key_event(1, KEY_SEMICOLON, 1)
        self.tracker.process_key_event(1, KEY_SEMICOLON, 0)

        # Espace
        self.tracker.process_key_event(1, KEY_SPACE, 1)
        self.tracker.process_key_event(1, KEY_SPACE, 0)

        self.assertEqual(len(self.captured_words), 1)
        word, delim, _ = self.captured_words[0]
        self.assertEqual(word, "am")


if __name__ == "__main__":
    unittest.main()
