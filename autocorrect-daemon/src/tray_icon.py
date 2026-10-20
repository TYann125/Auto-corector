"""Icône de contrôle du daemon dans la zone de notification."""

from __future__ import annotations

import threading
from pathlib import Path
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
        self._backend = ""
        self._gtk = None
        self._indicator = None
        self._menu = None
        self._gtk_main_started = threading.Event()
        self._icon_dir = Path.home() / ".cache" / "autocorrect"

    @property
    def available(self) -> bool:
        return self._available

    def start(self) -> bool:
        """Démarre l'icône avec pystray ou AppIndicator GTK."""
        try:
            import pystray
            from PIL import Image, ImageDraw
            self._icon = pystray.Icon(
                "autocorrect",
                self._make_image(Image, ImageDraw),
                "AutoCorrect",
                self._build_menu(pystray),
            )
            self._backend = "pystray"
            self._thread = threading.Thread(
                target=self._icon.run, name="autocorrect-tray", daemon=True
            )
            self._thread.start()
            return True
        except ImportError:
            return self._start_appindicator()
        except RuntimeError:
            return self._start_appindicator()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
        if (
            self._gtk is not None
            and self._gtk_main_started.is_set()
            and self._gtk.main_level() > 0
        ):
            self._gtk.main_quit()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def refresh(self) -> None:
        """Actualise l'image et le titre après un changement d'état."""
        if self._icon is None:
            if self._indicator is not None:
                self._update_appindicator()
            return
        try:
            from PIL import Image, ImageDraw
            self._icon.icon = self._make_image(Image, ImageDraw)
            self._icon.title = "AutoCorrect actif" if self._is_active() else "AutoCorrect suspendu"
        except ImportError:
            self._available = False

    def _start_appindicator(self) -> bool:
        """Backend natif Fedora via libappindicator, utilisable avec GNOME/KDE."""
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3, Gtk
        except (ImportError, ValueError, RuntimeError):
            self._available = False
            return False

        self._gtk = Gtk
        self._icon_dir.mkdir(parents=True, exist_ok=True)
        self._write_appindicator_icon(active=self._is_active())
        self._indicator = AppIndicator3.Indicator.new(
            "autocorrect",
            str(self._icon_dir / "autocorrect-active"),
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self._menu = self._build_gtk_menu(Gtk)
        self._indicator.set_menu(self._menu)
        self._backend = "appindicator"
        def run_gtk() -> None:
            self._gtk_main_started.set()
            Gtk.main()

        self._thread = threading.Thread(target=run_gtk, name="autocorrect-tray", daemon=True)
        self._thread.start()
        return True

    def _update_appindicator(self) -> None:
        self._write_appindicator_icon(active=self._is_active())
        self._indicator.set_icon_full(
            str(self._icon_dir / ("autocorrect-active" if self._is_active() else "autocorrect-paused")),
            "AutoCorrect",
        )

    def _build_gtk_menu(self, Gtk):
        menu = Gtk.Menu()
        toggle = Gtk.MenuItem.new_with_label(
            "Suspendre" if self._is_active() else "Activer"
        )
        toggle.connect("activate", lambda item: (self._on_toggle(), self.refresh()))
        menu.append(toggle)

        restart = Gtk.MenuItem.new_with_label("Redémarrer le daemon")
        restart.connect("activate", lambda item: self._on_restart())
        menu.append(restart)

        language = Gtk.MenuItem.new_with_label("Changer de langue")
        submenu = Gtk.Menu()
        for label, lang in (("Français (FR)", "fr"), ("English (EN)", "en")):
            item = Gtk.MenuItem.new_with_label(label)
            item.connect("activate", lambda widget, value=lang: self._on_language(value))
            submenu.append(item)
        language.set_submenu(submenu)
        menu.append(language)

        quit_item = Gtk.MenuItem.new_with_label("Quitter")
        quit_item.connect("activate", lambda item: self._on_quit())
        menu.append(quit_item)
        menu.show_all()
        return menu

    def _write_appindicator_icon(self, active: bool) -> None:
        from PIL import Image, ImageDraw

        image = self._make_image(Image, ImageDraw)
        suffix = "active" if active else "paused"
        image.save(self._icon_dir / f"autocorrect-{suffix}.png", format="PNG")
        # AppIndicator prend un nom sans extension et recherche le fichier PNG.
        image.save(self._icon_dir / f"autocorrect-{suffix}", format="PNG")

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
