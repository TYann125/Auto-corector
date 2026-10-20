"""Icône de contrôle du daemon dans la zone de notification."""

from __future__ import annotations

import threading
from typing import Callable, Optional


class TrayIcon:
    """Contrôle optionnel via pystray, avec repli propre si le tray n'est pas disponible."""

    def __init__(
        self,
        is_active: Callable[[], bool],
        on_toggle: Callable[[], None],
        on_restart: Callable[[], None],
        on_language: Callable[[str], None],
        on_quit: Callable[[], None],
    ):
        self._is_active = is_active
        self._on_toggle = on_toggle
        self._on_restart = on_restart
        self._on_language = on_language
        self._on_quit = on_quit
        self._icon = None
        self._thread: Optional[threading.Thread] = None
        self._available = True

    @property
    def available(self) -> bool:
        return self._available

    def start(self) -> bool:
        """Démarre l'icône dans un thread; retourne False si pystray/Pillow manque."""
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            self._available = False
            return False

        self._icon = pystray.Icon(
            "autocorrect",
            self._make_image(Image, ImageDraw),
            "AutoCorrect",
            self._build_menu(pystray),
        )
        self._thread = threading.Thread(target=self._icon.run, name="autocorrect-tray", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def refresh(self) -> None:
        """Actualise l'image et le titre après un changement d'état."""
        if self._icon is None:
            return
        try:
            from PIL import Image, ImageDraw
            self._icon.icon = self._make_image(Image, ImageDraw)
            self._icon.title = "AutoCorrect actif" if self._is_active() else "AutoCorrect suspendu"
        except ImportError:
            self._available = False

    def _build_menu(self, pystray):
        return pystray.Menu(
            pystray.MenuItem(
                lambda: "Suspendre" if self._is_active() else "Activer",
                lambda icon, item: self._toggle(),
            ),
            pystray.MenuItem("Redémarrer le daemon", lambda icon, item: self._on_restart()),
            pystray.MenuItem(
                "Changer de langue",
                pystray.Menu(
                    pystray.MenuItem("Français (FR)", lambda icon, item: self._on_language("fr")),
                    pystray.MenuItem("English (EN)", lambda icon, item: self._on_language("en")),
                ),
            ),
            pystray.MenuItem("Quitter", lambda icon, item: self._on_quit()),
        )

    def _toggle(self) -> None:
        self._on_toggle()
        self.refresh()

    def _make_image(self, image_module, draw_module):
        active = self._is_active()
        image = image_module.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = draw_module.Draw(image)
        color = (40, 170, 75, 255) if active else (125, 125, 125, 255)
        draw.ellipse((4, 4, 60, 60), fill=color)
        draw.text((19, 14), "A", fill=(255, 255, 255, 255))
        if not active:
            draw.line((12, 52, 52, 12), fill=(220, 60, 60, 255), width=5)
        return image
