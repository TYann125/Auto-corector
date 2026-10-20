"""
Module d'émulation de clavier virtuel via le sous-système noyau Linux /dev/uinput.

Permet d'injecter des touches physiques (Backspaces, caractères, modificateurs)
de manière totalement transparente sous Wayland (KDE Plasma, GNOME, Sway) et X11.
Ne requiert aucune bibliothèque C tierce (utilise fcntl.ioctl et struct standard).
"""

import os
import time
import fcntl
import struct
from typing import Optional, List, Tuple

# Constantes ioctl Linux uinput (x86_64 / arm64 Linux 64 bits)
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
UI_DEV_SETUP = 0x405c5503
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565

BUS_USB = 0x03

# Types d'événements
EV_SYN = 0
EV_KEY = 1
SYN_REPORT = 0

KEY_RELEASE = 0
KEY_PRESS = 1

# Format binaire d'un événement struct input_event
INPUT_EVENT_FORMAT = "qqHHi"

# Format struct uinput_setup: bustype (H), vendor (H), product (H), version (H), name (80s), ff_effects_max (I) = 92 octets
UINPUT_SETUP_FORMAT = "HHHH80sI"


class NativeUinputDevice:
    """Crée et contrôle un périphérique clavier virtuel via /dev/uinput."""

    def __init__(self, device_name: str = "AutoCorrect Virtual Keyboard", vendor_id: int = 0x1234, product_id: int = 0x5678):
        self.device_name = device_name
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.fd: Optional[int] = None

    def open(self) -> bool:
        """Initialise le périphérique virtuel uinput."""
        if not os.path.exists("/dev/uinput"):
            return False

        try:
            self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)

            # Active EV_KEY, EV_SYN et EV_REP (répétition de touches pour reconnaissance complète par libinput/KWin)
            fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
            fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_SYN)
            try:
                fcntl.ioctl(self.fd, UI_SET_EVBIT, 0x14)  # EV_REP
            except OSError:
                pass

            # Active l'ensemble des codes de touches standards (1 à 255)
            for keycode in range(1, 256):
                fcntl.ioctl(self.fd, UI_SET_KEYBIT, keycode)

            # Prépare struct uinput_setup
            name_bytes = self.device_name.encode("utf-8")[:79].ljust(80, b"\x00")
            setup_data = struct.pack(
                UINPUT_SETUP_FORMAT,
                BUS_USB,
                self.vendor_id,
                self.product_id,
                1,  # version
                name_bytes,
                0,  # ff_effects_max
            )

            # Configuration et enregistrement du périphérique auprès du noyau
            fcntl.ioctl(self.fd, UI_DEV_SETUP, setup_data)
            fcntl.ioctl(self.fd, UI_DEV_CREATE)

            # Délai de stabilisation pour permettre au compositeur (KWin Wayland / libinput)
            # de configurer et d'assigner le focus au nouveau périphérique virtuel
            time.sleep(0.3)
            return True

        except (PermissionError, OSError) as e:
            if self.fd is not None:
                try:
                    os.close(self.fd)
                except OSError:
                    pass
                self.fd = None
            return False

    def close(self):
        """Détruit le périphérique virtuel et libère les ressources."""
        if self.fd is not None:
            try:
                fcntl.ioctl(self.fd, UI_DEV_DESTROY)
            except OSError:
                pass
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def emit(self, ev_type: int, code: int, value: int):
        """Émet un événement noyau brut."""
        if self.fd is None:
            return
        # timestamp 0, 0 signifie que le noyau attribuera l'heure actuelle
        packet = struct.pack(INPUT_EVENT_FORMAT, 0, 0, ev_type, code, value)
        os.write(self.fd, packet)

    def syn(self):
        """Émet un rapport de synchronisation (SYN_REPORT)."""
        self.emit(EV_SYN, SYN_REPORT, 0)

    def press_key(self, code: int):
        """Appuie sur une touche."""
        self.emit(EV_KEY, code, KEY_PRESS)
        self.syn()

    def release_key(self, code: int):
        """Relâche une touche."""
        self.emit(EV_KEY, code, KEY_RELEASE)
        self.syn()

    def tap_key(self, code: int, delay_s: float = 0.002):
        """Effectue une frappe complète (appui + relâchement)."""
        self.press_key(code)
        if delay_s > 0:
            time.sleep(delay_s)
        self.release_key(code)
        if delay_s > 0:
            time.sleep(delay_s)
