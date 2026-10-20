"""
Module d'injection des corrections de frappe.

Gère la suppression chirurgicale du mot erroné par envoi de n touches Backspace,
puis la frappe ultra-rapide du mot corrigé et du délimiteur final via uinput.
Fournit une protection anti-boucle (indicateur is_injecting).
"""

import time
from typing import Optional
from .layout import (
    KeyboardLayout,
    KEY_BACKSPACE,
    KEY_LEFTSHIFT,
    KEY_RIGHTALT,
    KEY_SPACE,
)
from .uinput_native import NativeUinputDevice


class KeyboardInjector:
    """Injecte les corrections au niveau matériel virtuel."""

    def __init__(self, uinput_device: NativeUinputDevice, layout: KeyboardLayout, key_delay_ms: float = 2.0):
        self.device = uinput_device
        self.layout = layout
        self.key_delay_s = key_delay_ms / 1000.0
        self.is_injecting = False

    def erase_and_type(
        self,
        backspace_count: int,
        replacement_text: str,
        trailing_char: Optional[str] = None,
        separator: bool = False,
    ):
        """
        Supprime le mot incorrect par backspace_count retours arrière,
        puis tape le mot de remplacement et le caractère final.
        """
        if self.device.fd is None:
            return

        self.is_injecting = True
        try:
            # Léger délai de stabilisation (15 ms) pour laisser à l'application cible (Chrome/KWrite)
            # le temps de traiter l'événement de saisie du délimiteur
            time.sleep(0.015)

            # 1. Envoi des retours arrière
            for _ in range(backspace_count):
                self.device.tap_key(KEY_BACKSPACE, delay_s=self.key_delay_s)

            # Petite pause entre l'effacement et la frappe pour les éditeurs complexes (Google Docs)
            time.sleep(0.010)

            # 2. Frappe du texte de remplacement
            full_text = replacement_text
            if trailing_char:
                full_text += trailing_char
            if separator and trailing_char != " ":
                full_text += " "

            for char in full_text:
                self._type_char(char)

        finally:
            # Léger délai pour s'assurer que le buffer matériel a vidé les paquets
            time.sleep(0.010)
            self.is_injecting = False

    def _type_char(self, char: str):
        """Frappe un caractère unique en respectant les modificateurs Shift / AltGr et touches mortes."""
        injections = self.layout.char_to_injections(char)
        if not injections:
            return

        for code, need_shift, need_altgr in injections:
            if need_shift:
                self.device.press_key(KEY_LEFTSHIFT)
                time.sleep(self.key_delay_s)
                self.device.tap_key(code, delay_s=self.key_delay_s)
                self.device.release_key(KEY_LEFTSHIFT)
                time.sleep(self.key_delay_s)
            elif need_altgr:
                self.device.press_key(KEY_RIGHTALT)
                time.sleep(self.key_delay_s)
                self.device.tap_key(code, delay_s=self.key_delay_s)
                self.device.release_key(KEY_RIGHTALT)
                time.sleep(self.key_delay_s)
            else:
                self.device.tap_key(code, delay_s=self.key_delay_s)
