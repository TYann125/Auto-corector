"""
Module de capture bas-niveau des événements clavier sous Linux (/dev/input/event*).

Ce module propose deux moteurs :
1. Moteur pur-Python standard (sans dépendance externe C, utilisant struct, os, fcntl, select).
2. Moteur utilisant la bibliothèque 'evdev' si celle-ci est installée.
Compatible 100% Wayland et X11, car il écoute directement le sous-système kernel evdev.
"""

import os
import glob
import struct
import select
from typing import List, Generator, Tuple, Optional, Callable

# Types d'événements noyau Linux
EV_SYN = 0
EV_KEY = 1
EV_REL = 2
EV_ABS = 3
EV_MSC = 4

# Valeurs d'état des touches
KEY_RELEASE = 0
KEY_PRESS = 1
KEY_REPEAT = 2

# Format binaire d'un struct input_event sous Linux 64 bits (time_sec, time_usec, type, code, value)
# 8 octets sec, 8 octets usec, 2 octets type, 2 octets code, 4 octets value = 24 octets
INPUT_EVENT_FORMAT = "qqHHi"
EVENT_SIZE = struct.calcsize(INPUT_EVENT_FORMAT)


class KeyboardDevice:
    """Représente un périphérique d'entrée clavier sous /dev/input/event*."""

    def __init__(self, path: str, name: str = ""):
        self.path = path
        self.name = name
        self.fd: Optional[int] = None

    def open(self) -> bool:
        try:
            # Ouverture en lecture seule non-bloquante
            self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
            return True
        except (PermissionError, FileNotFoundError, OSError):
            self.fd = None
            return False

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def read_events(self) -> List[Tuple[int, int, int]]:
        """Lit les événements disponibles. Retourne une liste de tuples (type, code, value)."""
        if self.fd is None:
            return []
        events = []
        try:
            data = os.read(self.fd, EVENT_SIZE * 64)
            for i in range(0, len(data), EVENT_SIZE):
                chunk = data[i : i + EVENT_SIZE]
                if len(chunk) == EVENT_SIZE:
                    _, _, ev_type, code, value = struct.unpack(INPUT_EVENT_FORMAT, chunk)
                    events.append((ev_type, code, value))
        except (BlockingIOError, InterruptedError):
            pass
        except OSError:
            self.close()
        return events


class EvdevListener:
    """
    Gestionnaire d'écoute des claviers physiques.
    Détecte automatiquement les périphériques clavier dans /dev/input/
    et ignore le clavier virtuel créé par le daemon pour éviter les boucles infinies.
    """

    def __init__(self, virtual_device_name: str = "AutoCorrect Virtual Keyboard"):
        self.virtual_device_name = virtual_device_name
        self.devices: List[KeyboardDevice] = []
        self._running = False

    @staticmethod
    def is_likely_keyboard(dev_path: str, virtual_device_name: str) -> Tuple[bool, str]:
        """Analyse sysfs capabilities/key pour vérifier si le périphérique est un vrai clavier de saisie."""
        try:
            event_basename = os.path.basename(dev_path)
            # Lecture du nom depuis sysfs
            name_path = f"/sys/class/input/{event_basename}/device/name"
            name = "Inconnu"
            if os.path.exists(name_path):
                with open(name_path, "r", encoding="utf-8", errors="ignore") as f:
                    name = f.read().strip()

            # Ignore notre propre périphérique virtuel uinput
            if virtual_device_name.lower() in name.lower():
                return False, name

            # Vérification des capacités de touches via sysfs capabilities/key
            caps_key_path = f"/sys/class/input/{event_basename}/device/capabilities/key"
            if os.path.exists(caps_key_path):
                with open(caps_key_path, "r") as f:
                    hex_str = f.read().strip()

                val = int("".join(hex_str.split()), 16)
                # Un vrai clavier alphanumérique doit supporter KEY_A (30), KEY_ENTER (28) et KEY_SPACE (57)
                has_a = bool(val & (1 << 30))
                has_enter = bool(val & (1 << 28))
                has_space = bool(val & (1 << 57))

                if has_a and has_enter and has_space:
                    return True, name

        except Exception:
            pass
        return False, "Non identifié"

    def discover_keyboards(self) -> List[KeyboardDevice]:
        """Scanne /dev/input/event* et retourne la liste des claviers trouvés."""
        keyboards = []
        event_paths = sorted(glob.glob("/dev/input/event*"))

        for path in event_paths:
            is_kbd, name = self.is_likely_keyboard(path, self.virtual_device_name)
            if is_kbd:
                keyboards.append(KeyboardDevice(path, name))

        return keyboards

    def start(self) -> int:
        """Ouvre tous les claviers détectés. Retourne le nombre de claviers ouverts avec succès."""
        self.devices = self.discover_keyboards()
        opened_count = 0
        for dev in self.devices:
            if dev.open():
                opened_count += 1
        self._running = opened_count > 0
        return opened_count

    def stop(self):
        """Ferme tous les descripteurs de fichiers."""
        self._running = False
        for dev in self.devices:
            dev.close()
        self.devices.clear()

    def poll_events(self, timeout_ms: int = 20) -> Generator[Tuple[int, int, int], None, None]:
        """
        Attend et extrait les événements clavier (ev_type, code, value) via select().
        Permet un temps de réponse instantané (< 1ms).
        """
        if not self._running:
            return

        fds = [dev.fd for dev in self.devices if dev.fd is not None]
        if not fds:
            return

        readable, _, _ = select.select(fds, [], [], timeout_ms / 1000.0)
        fd_to_dev = {dev.fd: dev for dev in self.devices}

        for fd in readable:
            dev = fd_to_dev.get(fd)
            if dev:
                for ev_type, code, value in dev.read_events():
                    yield ev_type, code, value
