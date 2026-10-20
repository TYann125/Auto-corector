"""
Daemon principal de correction automatique de frappe en temps réel sous Linux.

Ce service surveille les événements clavier de manière non-bloquante,
analyse les mots saisis lors des délimititeurs, et applique les corrections
instantanées via injection uinput.
"""

import os
import sys
import time
import signal
import logging
import threading
from collections import deque
from typing import Deque, List, Optional, Tuple

from .config import DaemonConfig
from .keyboard.layout import KeyboardLayout, KEY_SPACE
from .keyboard.evdev_native import EvdevListener, EV_KEY
from .keyboard.uinput_native import NativeUinputDevice
from .keyboard.injector import KeyboardInjector
from .engine.corrector import TextCorrectionEngine
from .buffer.word_tracker import WordTracker


class AutoCorrectDaemon:
    """Orchestre la capture, l'analyse bilingue et l'injection des corrections."""

    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig()
        self._setup_logging()

        self.logger.info("Initialisation du daemon AutoCorrect...")
        self.layout = KeyboardLayout(self.config.layout)
        self.logger.info(f"Disposition clavier chargée : {self.config.layout.upper()}")

        self.uinput_dev = NativeUinputDevice(device_name=self.config.virtual_device_name)
        self.injector = KeyboardInjector(
            self.uinput_dev,
            self.layout,
            key_delay_ms=self.config.key_delay_ms,
        )

        self.engine = TextCorrectionEngine(
            default_lang=self.config.default_language,
            enable_languagetool=self.config.enable_languagetool,
            languagetool_endpoint=self.config.languagetool_endpoint,
            custom_corrections=self.config.custom_corrections,
        )

        self.tracker = WordTracker(
            self.layout,
            on_word_complete=self._handle_word_completed,
        )

        self.listener = EvdevListener(virtual_device_name=self.config.virtual_device_name)
        self.is_running = False
        self.is_enabled = True
        self.keystroke_queue: Deque[Tuple[int, int, int]] = deque()
        self._queue_lock = threading.Lock()
        self._injection_active = threading.Event()
        self._injection_thread: Optional[threading.Thread] = None
        self._tray = None

    def _setup_logging(self):
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger("AutoCorrectDaemon")

    def _handle_word_completed(self, word: str, delimiter: str, recent_words: List[str]):
        """Rappel exécuté à chaque fin de mot (appui sur Espace ou ponctuation)."""
        # Ne rien faire si nous sommes déjà en train d'injecter une correction
        if self.injector.is_injecting or self._injection_active.is_set():
            return

        self.logger.debug(f"[Traqué] Mot intercepté : '{word}', délimiteur : {repr(delimiter)}")
        t_start = time.perf_counter()
        correction = self.engine.process_word(word, recent_words)
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        if correction and correction != word:
            self.logger.info(
                f"[Correction] '{word}' -> '{correction}' (calculé en {t_elapsed_ms:.2f} ms)"
            )
            # Nombre de retours arrière : longueur du mot + 1 (pour effacer le délimiteur déjà affiché)
            backspace_count = len(word) + len(delimiter)
            self._start_injection(backspace_count, correction, delimiter)

    def _start_injection(self, backspace_count: int, correction: str, delimiter: str) -> None:
        if self._injection_thread and self._injection_thread.is_alive():
            return

        def inject() -> None:
            try:
                self.injector.erase_and_type(
                    backspace_count=backspace_count,
                    replacement_text=correction,
                    trailing_char=delimiter,
                    separator=delimiter == " ",
                )
            finally:
                self._injection_active.clear()
                with self._queue_lock:
                    self.keystroke_queue.clear()

        self._injection_active.set()
        self._injection_thread = threading.Thread(
            target=inject, name="autocorrect-injection", daemon=True
        )
        self._injection_thread.start()

    def _queue_event(self, event: Tuple[int, int, int]) -> None:
        with self._queue_lock:
            self.keystroke_queue.append(event)

    def toggle_enabled(self) -> None:
        self.is_enabled = not self.is_enabled
        self.logger.info("Correction %s", "activée" if self.is_enabled else "suspendue")

    def change_language(self, language: str) -> None:
        if language not in {"fr", "en"}:
            raise ValueError(f"Langue non supportée : {language}")
        self.config.default_language = language
        self.engine.default_lang = language
        self.logger.info("Langue par défaut : %s", language.upper())

    def restart(self) -> None:
        self.logger.info("Redémarrage logique du daemon")
        self.tracker.reset_word_buffer()
        with self._queue_lock:
            self.keystroke_queue.clear()
        self.is_enabled = True

    def start(self):
        """Démarre le service et la boucle d'écoute matérielle."""
        self.logger.info("Création du périphérique virtuel uinput...")
        if not self.uinput_dev.open():
            self.logger.error(
                "Impossible d'ouvrir /dev/uinput. Vérifiez les permissions udev ou exécutez avec les droits requis."
            )
            return False

        self.logger.info("Découverte des claviers physiques...")
        opened_keyboards = self.listener.start()
        if opened_keyboards == 0:
            self.logger.error(
                "Aucun clavier physique accessible dans /dev/input/event*. Vérifiez l'appartenance au groupe 'input'."
            )
            self.uinput_dev.close()
            return False

        self.logger.info(f"{opened_keyboards} clavier(s) physique(s) ouvert(s) avec succès :")
        for dev in self.listener.devices:
            if dev.fd is not None:
                self.logger.info(f" -> Écoute active sur : {dev.name} ({dev.path})")
        self.is_running = True
        try:
            from .tray_icon import TrayIcon
            self._tray = TrayIcon(
                is_active=lambda: self.is_running and self.is_enabled,
                on_toggle=self.toggle_enabled,
                on_restart=self.restart,
                on_language=self.change_language,
                on_quit=self._handle_tray_quit,
            )
            self._tray.start()
        except (ImportError, RuntimeError) as exc:
            self.logger.warning("Icône tray indisponible : %s", exc)

        # Enregistrement des gestionnaires de signaux d'arrêt
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self.logger.info("Daemon prêt et actif. Surveillance en cours...")
        try:
            while self.is_running:
                for ev_type, code, value in self.listener.poll_events(timeout_ms=10):
                    event = (ev_type, code, value)
                    if self.injector.is_injecting or self._injection_active.is_set():
                        self._queue_event(event)
                        continue

                    if ev_type == EV_KEY:
                        if not self.is_enabled:
                            continue
                        self.tracker.process_key_event(ev_type, code, value)
        except Exception as e:
            self.logger.error(f"Erreur inattendue dans la boucle principale : {e}", exc_info=True)
        finally:
            self.stop()

        return True

    def _handle_signal(self, signum, frame):
        self.logger.info(f"Signal reçu ({signum}), arrêt du daemon...")
        self.is_running = False

    def _handle_tray_quit(self):
        self.logger.info("Arrêt demandé depuis le tray")
        self.is_running = False

    def stop(self):
        """Arrête proprement le daemon et libère les périphériques noyau."""
        self.is_running = False
        self.listener.stop()
        if self._injection_thread and self._injection_thread.is_alive():
            self._injection_thread.join(timeout=2.0)
        if self._tray is not None:
            self._tray.stop()
        self.uinput_dev.close()
        self.logger.info("Daemon arrêté avec succès.")
