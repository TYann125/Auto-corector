"""
Machine à états traquant la saisie au clavier, la détection des mots et des délimiteurs.

Reconstitue fidèlement le texte saisi en tenant compte des modificateurs (Shift, AltGr, CapsLock),
des retours arrière (Backspace), des touches de déplacement du curseur, et déclenche
l'évaluation lors de l'appui sur un délimiteur (espace, ponctuation, saut de ligne).
"""

import time
from typing import List, Optional, Callable, Tuple
from ..keyboard.layout import (
    KeyboardLayout,
    KEY_LEFTSHIFT,
    KEY_RIGHTSHIFT,
    KEY_RIGHTALT,
    KEY_LEFTALT,
    KEY_LEFTCTRL,
    KEY_RIGHTCTRL,
    KEY_CAPSLOCK,
    KEY_BACKSPACE,
    KEY_SPACE,
    KEY_ENTER,
    KEY_TAB,
    KEY_ESC,
)

# Codes de navigation et contrôle à réinitialisation immédiate du buffer
NAVIGATION_KEYS = {
    KEY_ESC,
    103,  # KEY_UP
    105,  # KEY_LEFT
    106,  # KEY_RIGHT
    108,  # KEY_DOWN
    102,  # KEY_HOME
    107,  # KEY_END
    104,  # KEY_PAGEUP
    109,  # KEY_PAGEDOWN
    111,  # KEY_DELETE
}

# Délimiteurs entraînant l'évaluation du mot
DELIMITER_CHARS = {" ", "\t", "\n", ".", ",", ";", ":", "!", "?", "(", ")", "[", "]", "{", "}", "\"", "'"}


class WordTracker:
    """Suivi d'état de la frappe et détection des frontières de mots."""

    def __init__(self, layout: KeyboardLayout, on_word_complete: Optional[Callable[[str, str, List[str]], None]] = None):
        self.layout = layout
        self.on_word_complete = on_word_complete

        # État des modificateurs
        self.shift = False
        self.altgr = False
        self.ctrl = False
        self.alt = False
        self.capslock = False

        # Buffers de saisie
        self.current_word_chars: List[str] = []
        self.recent_words: List[str] = []
        self.last_activity_time = time.time()

    def reset_word_buffer(self):
        """Réinitialise le mot en cours (après navigation ou inactivité)."""
        self.current_word_chars.clear()

    def process_key_event(self, ev_type: int, code: int, value: int):
        """
        Traite un événement noyau evdev EV_KEY.
        value: 1 = appui, 0 = relâchement, 2 = répétition.
        """
        # Mise à jour du temps de dernière activité
        now = time.time()
        if now - self.last_activity_time > 10.0:
            # Plus de 10s d'inactivité : l'utilisateur a changé de contexte
            self.reset_word_buffer()
        self.last_activity_time = now

        # Gestion des relâchements de touches modificateurs
        if value == 0:
            if code in (KEY_LEFTSHIFT, KEY_RIGHTSHIFT):
                self.shift = False
            elif code == KEY_RIGHTALT:
                self.altgr = False
            elif code in (KEY_LEFTCTRL, KEY_RIGHTCTRL):
                self.ctrl = False
            elif code == KEY_LEFTALT:
                self.alt = False
            return

        # Gestion des appuis et répétitions (value == 1 ou 2)
        if code in (KEY_LEFTSHIFT, KEY_RIGHTSHIFT):
            self.shift = True
            return
        elif code == KEY_RIGHTALT:
            self.altgr = True
            return
        elif code in (KEY_LEFTCTRL, KEY_RIGHTCTRL):
            self.ctrl = True
            return
        elif code == KEY_LEFTALT:
            self.alt = True
            return
        elif code == KEY_CAPSLOCK and value == 1:
            self.capslock = not self.capslock
            return

        # Raccourcis clavier (Ctrl+C, Alt+Tab, etc.) -> réinitialisation du mot
        if self.ctrl or self.alt:
            self.reset_word_buffer()
            return

        # Touches de navigation ou d'échappement -> réinitialisation
        if code in NAVIGATION_KEYS:
            self.reset_word_buffer()
            return

        # Touche Backspace (efface le dernier caractère tapé)
        if code == KEY_BACKSPACE:
            if self.current_word_chars:
                self.current_word_chars.pop()
            return

        # Touche Espace
        if code == KEY_SPACE:
            self._trigger_word_completion(" ")
            return

        # Touche Entrée
        if code == KEY_ENTER:
            self._trigger_word_completion("\n")
            return

        # Touche Tab
        if code == KEY_TAB:
            self._trigger_word_completion("\t")
            return

        # Conversion du scancode en caractère selon le layout
        char = self.layout.scancode_to_char(code, shift=self.shift, altgr=self.altgr, capslock=self.capslock)
        if not char:
            return

        # Si le caractère est un délimiteur (ponctuation)
        if char in DELIMITER_CHARS:
            self._trigger_word_completion(char)
        else:
            self.current_word_chars.append(char)

    def _trigger_word_completion(self, delimiter: str):
        """Déclenche l'évaluation du mot terminé."""
        word = "".join(self.current_word_chars)
        self.current_word_chars.clear()

        if word:
            if self.on_word_complete:
                self.on_word_complete(word, delimiter, list(self.recent_words))

            # Mise à jour de l'historique récent
            self.recent_words.append(word)
            if len(self.recent_words) > 15:
                self.recent_words.pop(0)

        # Réinitialisation si saut de phrase
        if delimiter in {".", "!", "?", "\n"}:
            self.recent_words.clear()
