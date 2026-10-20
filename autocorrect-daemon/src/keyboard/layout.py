"""
Module de gestion des dispositions de clavier (AZERTY / QWERTY) et mapping Scancodes <-> Caractères.

Ce module permet de :
1. Traduire un scancode evdev (ex: KEY_A) en caractère UTF-8 selon le layout actif et les modificateurs (Shift, AltGr, CapsLock).
2. Effectuer la traduction inverse : à partir d'un caractère UTF-8 (ex: 'é', 'A', '@'), déterminer la combinaison
   (scancode, requires_shift, requires_altgr) à injecter via uinput.
"""

from typing import Dict, Tuple, Optional

# Scancodes Linux EV_KEY standards (issus de linux/input-event-codes.h)
KEY_ESC = 1
KEY_1 = 2
KEY_2 = 3
KEY_3 = 4
KEY_4 = 5
KEY_5 = 6
KEY_6 = 7
KEY_7 = 8
KEY_8 = 9
KEY_9 = 10
KEY_0 = 11
KEY_MINUS = 12
KEY_EQUAL = 13
KEY_BACKSPACE = 14
KEY_TAB = 15
KEY_Q = 16
KEY_W = 17
KEY_E = 18
KEY_R = 19
KEY_T = 20
KEY_Y = 21
KEY_U = 22
KEY_I = 23
KEY_O = 24
KEY_P = 25
KEY_LEFTBRACE = 26
KEY_RIGHTBRACE = 27
KEY_ENTER = 28
KEY_LEFTCTRL = 29
KEY_A = 30
KEY_S = 31
KEY_D = 32
KEY_F = 33
KEY_G = 34
KEY_H = 35
KEY_J = 36
KEY_K = 37
KEY_L = 38
KEY_SEMICOLON = 39
KEY_APOSTROPHE = 40
KEY_GRAVE = 41
KEY_LEFTSHIFT = 42
KEY_BACKSLASH = 43
KEY_Z = 44
KEY_X = 45
KEY_C = 46
KEY_V = 47
KEY_B = 48
KEY_N = 49
KEY_M = 50
KEY_COMMA = 51
KEY_DOT = 52
KEY_SLASH = 53
KEY_RIGHTSHIFT = 54
KEY_KPASTERISK = 55
KEY_LEFTALT = 56
KEY_SPACE = 57
KEY_CAPSLOCK = 58
KEY_F1 = 59
KEY_F2 = 60
KEY_F3 = 61
KEY_F4 = 62
KEY_F5 = 63
KEY_F6 = 64
KEY_F7 = 65
KEY_F8 = 66
KEY_F9 = 67
KEY_F10 = 68
KEY_RIGHTCTRL = 97
KEY_RIGHTALT = 100  # AltGr sous Linux
KEY_102ND = 86      # Touche <> sur claviers européens


# Table AZERTY français (standard PC)
# Structure: scancode: (unshifted, shifted, altgr)
AZERTY_MAP: Dict[int, Tuple[str, str, Optional[str]]] = {
    # Ligne 1
    KEY_GRAVE: ("²", "", None),
    KEY_1: ("&", "1", None),
    KEY_2: ("é", "2", "~"),
    KEY_3: ('"', "3", "#"),
    KEY_4: ("'", "4", "{"),
    KEY_5: ("(", "5", "["),
    KEY_6: ("-", "6", "|"),
    KEY_7: ("è", "7", "`"),
    KEY_8: ("_", "8", "\\"),
    KEY_9: ("ç", "9", "^"),
    KEY_0: ("à", "0", "@"),
    KEY_MINUS: (")", "°", "]"),
    KEY_EQUAL: ("=", "+", "}"),

    # Ligne 2 (A Z E R T Y U I O P ^ $)
    KEY_Q: ("a", "A", None),
    KEY_W: ("z", "Z", None),
    KEY_E: ("e", "E", "€"),
    KEY_R: ("r", "R", None),
    KEY_T: ("t", "T", None),
    KEY_Y: ("y", "Y", None),
    KEY_U: ("u", "U", None),
    KEY_I: ("i", "I", None),
    KEY_O: ("o", "O", None),
    KEY_P: ("p", "P", None),
    KEY_LEFTBRACE: ("^", "¨", None),    # Touche morte accent circonflexe / tréma
    KEY_RIGHTBRACE: ("$", "£", "¤"),

    # Ligne 3 (Q S D F G H J K L M % *)
    KEY_A: ("q", "Q", None),
    KEY_S: ("s", "S", None),
    KEY_D: ("d", "D", None),
    KEY_F: ("f", "F", None),
    KEY_G: ("g", "G", None),
    KEY_H: ("h", "H", None),
    KEY_J: ("j", "J", None),
    KEY_K: ("k", "K", None),
    KEY_L: ("l", "L", None),
    KEY_SEMICOLON: ("m", "M", None),
    KEY_APOSTROPHE: ("ù", "%", None),
    KEY_BACKSLASH: ("*", "µ", None),

    # Ligne 4 (< W X C V B N , ; : !)
    KEY_102ND: ("<", ">", None),
    KEY_Z: ("w", "W", None),
    KEY_X: ("x", "X", None),
    KEY_C: ("c", "C", None),
    KEY_V: ("v", "V", None),
    KEY_B: ("b", "B", None),
    KEY_N: ("n", "N", None),
    KEY_M: (",", "?", None),
    KEY_COMMA: (";", ".", None),
    KEY_DOT: (":", "/", None),
    KEY_SLASH: ("!", "§", None),

    # Touche espace
    KEY_SPACE: (" ", " ", None),
}

# Table QWERTY US standard
QWERTY_MAP: Dict[int, Tuple[str, str, Optional[str]]] = {
    KEY_GRAVE: ("`", "~", None),
    KEY_1: ("1", "!", None),
    KEY_2: ("2", "@", None),
    KEY_3: ("3", "#", None),
    KEY_4: ("4", "$", None),
    KEY_5: ("5", "%", None),
    KEY_6: ("6", "^", None),
    KEY_7: ("7", "&", None),
    KEY_8: ("8", "*", None),
    KEY_9: ("9", "(", None),
    KEY_0: ("0", ")", None),
    KEY_MINUS: ("-", "_", None),
    KEY_EQUAL: ("=", "+", None),

    KEY_Q: ("q", "Q", None),
    KEY_W: ("w", "W", None),
    KEY_E: ("e", "E", None),
    KEY_R: ("r", "R", None),
    KEY_T: ("t", "T", None),
    KEY_Y: ("y", "Y", None),
    KEY_U: ("u", "U", None),
    KEY_I: ("i", "I", None),
    KEY_O: ("o", "O", None),
    KEY_P: ("p", "P", None),
    KEY_LEFTBRACE: ("[", "{", None),
    KEY_RIGHTBRACE: ("]", "}", None),
    KEY_BACKSLASH: ("\\", "|", None),

    KEY_A: ("a", "A", None),
    KEY_S: ("s", "S", None),
    KEY_D: ("d", "D", None),
    KEY_F: ("f", "F", None),
    KEY_G: ("g", "G", None),
    KEY_H: ("h", "H", None),
    KEY_J: ("j", "J", None),
    KEY_K: ("k", "K", None),
    KEY_L: ("l", "L", None),
    KEY_SEMICOLON: (";", ":", None),
    KEY_APOSTROPHE: ("'", '"', None),

    KEY_Z: ("z", "Z", None),
    KEY_X: ("x", "X", None),
    KEY_C: ("c", "C", None),
    KEY_V: ("v", "V", None),
    KEY_B: ("b", "B", None),
    KEY_N: ("n", "N", None),
    KEY_M: ("m", "M", None),
    KEY_COMMA: (",", "<", None),
    KEY_DOT: (".", ">", None),
    KEY_SLASH: ("/", "?", None),

    KEY_SPACE: (" ", " ", None),
}


class KeyboardLayout:
    """Gère la conversion bidirectionnelle scancode <-> caractère selon la disposition."""

    def __init__(self, name: str = "azerty"):
        self.name = name.lower()
        if self.name == "azerty":
            self.map = AZERTY_MAP
        elif self.name == "qwerty":
            self.map = QWERTY_MAP
        else:
            raise ValueError(f"Layout inconnu : {name}. Choisissez 'azerty' ou 'qwerty'.")

        # Construction de l'index inverse : char -> (scancode, with_shift, with_altgr, is_dead_key_combo)
        self.reverse_map: Dict[str, Tuple[int, bool, bool]] = {}
        self._build_reverse_map()

    def _build_reverse_map(self):
        for code, (unshifted, shifted, altgr) in self.map.items():
            if unshifted and unshifted not in self.reverse_map:
                self.reverse_map[unshifted] = (code, False, False)
            if shifted and shifted not in self.reverse_map:
                self.reverse_map[shifted] = (code, True, False)
            if altgr and altgr not in self.reverse_map:
                self.reverse_map[altgr] = (code, False, True)

        # Accents composés courants pour AZERTY avec touche morte
        # Touche morte ^ : KEY_LEFTBRACE (26)
        # Touche morte ¨ : Shift + KEY_LEFTBRACE (26)
        self.dead_key_map: Dict[str, List[Tuple[int, bool, bool]]] = {}
        if self.name == "azerty":
            self.dead_key_map = {
                "ê": [(KEY_LEFTBRACE, False, False), (KEY_E, False, False)],
                "Ê": [(KEY_LEFTBRACE, False, False), (KEY_E, True, False)],
                "î": [(KEY_LEFTBRACE, False, False), (KEY_I, False, False)],
                "Î": [(KEY_LEFTBRACE, False, False), (KEY_I, True, False)],
                "ô": [(KEY_LEFTBRACE, False, False), (KEY_O, False, False)],
                "Ô": [(KEY_LEFTBRACE, False, False), (KEY_O, True, False)],
                "û": [(KEY_LEFTBRACE, False, False), (KEY_U, False, False)],
                "Û": [(KEY_LEFTBRACE, False, False), (KEY_U, True, False)],
                "ë": [(KEY_LEFTBRACE, True, False), (KEY_E, False, False)],
                "Ë": [(KEY_LEFTBRACE, True, False), (KEY_E, True, False)],
                "ï": [(KEY_LEFTBRACE, True, False), (KEY_I, False, False)],
                "Ï": [(KEY_LEFTBRACE, True, False), (KEY_I, True, False)],
            }

    def scancode_to_char(self, scancode: int, shift: bool = False, altgr: bool = False, capslock: bool = False) -> Optional[str]:
        """Convertit un scancode en caractère UTF-8 selon l'état des modificateurs."""
        entry = self.map.get(scancode)
        if not entry:
            return None

        unshifted, shifted, altgr_char = entry

        if altgr and altgr_char:
            return altgr_char

        effective_shift = shift ^ capslock if unshifted.isalpha() else shift

        if effective_shift:
            return shifted if shifted else unshifted
        else:
            return unshifted

    def char_to_injection(self, char: str) -> Optional[Tuple[int, bool, bool]]:
        """
        Retourne (scancode, with_shift, with_altgr) nécessaire pour produire ce caractère simple.
        """
        if char in self.reverse_map:
            return self.reverse_map[char]

        # Cas de repli : majuscules non directement trouvées
        if char.isupper() and char.lower() in self.reverse_map:
            code, _, altgr = self.reverse_map[char.lower()]
            return (code, True, altgr)

        return None

    def char_to_injections(self, char: str) -> List[Tuple[int, bool, bool]]:
        """
        Retourne la liste des étapes [(scancode, with_shift, with_altgr), ...]
        nécessaires pour taper ce caractère (gère les caractères directs et les touches mortes).
        """
        if char in self.dead_key_map:
            return self.dead_key_map[char]

        single = self.char_to_injection(char)
        if single:
            return [single]

        return []
