#!/usr/bin/env python3
"""
Point d'entrée du daemon AutoCorrect.

Usage :
  python3 run_daemon.py                      # Démarre le daemon
  python3 run_daemon.py --check-permissions  # Vérifie l'accès à /dev/input et /dev/uinput
  python3 run_daemon.py --dry-run            # Intercepte et affiche sans réinjecter
  python3 run_daemon.py --layout qwerty      # Force la disposition QWERTY
"""

import os
import sys
import argparse

# Ajout du dossier courant au sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import DaemonConfig
from src.daemon import AutoCorrectDaemon
from src.keyboard.evdev_native import EvdevListener


def check_permissions():
    """Vérifie l'état des permissions Linux pour l'interception et l'injection."""
    print("=" * 60)
    print("VÉRIFICATION DES PERMISSIONS LINUX (/dev/input et /dev/uinput)")
    print("=" * 60)

    # 1. Test /dev/uinput
    uinput_ok = False
    if os.path.exists("/dev/uinput"):
        can_write = os.access("/dev/uinput", os.W_OK)
        if can_write:
            print("[\033[92mOK\033[0m] /dev/uinput : Accès en écriture autorisé.")
            uinput_ok = True
        else:
            print("[\033[91mÉCHEC\033[0m] /dev/uinput : Permission refusée.")
    else:
        print("[\033[91mÉCHEC\033[0m] /dev/uinput : Périphérique introuvable.")

    # 2. Test /dev/input/event*
    listener = EvdevListener()
    keyboards = listener.discover_keyboards()
    accessible_kbds = []

    for kbd in keyboards:
        if os.access(kbd.path, os.R_OK):
            accessible_kbds.append(kbd)

    if accessible_kbds:
        print(f"[\033[92mOK\033[0m] Claviers physiques accessibles ({len(accessible_kbds)}/{len(keyboards)}) :")
        for kbd in accessible_kbds:
            print(f"     - {kbd.name} ({kbd.path})")
    else:
        print("[\033[91mÉCHEC\033[0m] Aucun clavier physique accessible en lecture.")
        if keyboards:
            print(f"     Claviers détectés mais inaccessibles :")
            for kbd in keyboards:
                print(f"     - {kbd.name} ({kbd.path})")

    print("\n" + "-" * 60)
    if uinput_ok and accessible_kbds:
        print("\033[92mToutes les permissions sont prêtes ! Le daemon peut être lancé.\033[0m")
        return True
    else:
        print("\033[93mACTIONS RECOMMANDÉES POUR DÉBLOQUER LES PERMISSIONS :\033[0m")
        print("1. Installer la règle udev fournie :")
        print("   sudo cp systemd/99-autocorrect-uinput.rules /etc/udev/rules.d/")
        print("   sudo udevadm control --reload-rules && sudo udevadm trigger")
        print("2. Ajouter votre utilisateur au groupe 'input' (et 'uinput' si présent) :")
        print("   sudo usermod -aG input $USER")
        print("   newgrp input")
        print("3. Ou exécuter directement avec sudo :")
        print("   sudo python3 run_daemon.py")
        print("=" * 60)
        return False


def main():
    parser = argparse.ArgumentParser(description="Daemon de correction automatique en temps réel sous Linux (Wayland & X11)")
    parser.add_argument("--config", default="config.json", help="Chemin du fichier de configuration JSON")
    parser.add_argument("--layout", choices=["azerty", "qwerty"], help="Forcer la disposition clavier")
    parser.add_argument("--lang", choices=["fr", "en"], help="Forcer la langue par défaut")
    parser.add_argument("--check-permissions", action="store_true", help="Vérifier les accès /dev/input et /dev/uinput")
    parser.add_argument("--languagetool", action="store_true", help="Activer le connecteur LanguageTool local")
    parser.add_argument("--debug", action="store_true", help="Activer les logs détaillés de frappe (DEBUG)")
    args = parser.parse_args()

    if args.check_permissions:
        check_permissions()
        return

    # Chargement de la configuration
    config_path = args.config if os.path.exists(args.config) else "config.example.json"
    config = DaemonConfig.load(config_path)

    if args.layout:
        config.layout = args.layout
    if args.lang:
        config.default_language = args.lang
    if args.languagetool:
        config.enable_languagetool = True
    if args.debug:
        config.log_level = "DEBUG"

    # Vérification préliminaire des permissions
    if not os.access("/dev/uinput", os.W_OK):
        print("\033[91m[ERREUR] Accès en écriture à /dev/uinput refusé.\033[0m")
        print("Veuillez exécuter avec les droits nécessaires :")
        print("    \033[92msudo python3 run_daemon.py\033[0m")
        print("Ou lancez d'abord le script d'installation des permissions udev :")
        print("    \033[92msudo ./install.sh && newgrp input\033[0m")
        sys.exit(1)

    daemon = AutoCorrectDaemon(config)
    success = daemon.start()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
