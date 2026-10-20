#!/usr/bin/env bash
# Script d'installation et de configuration des permissions pour AutoCorrect Daemon sous Fedora / Linux

set -e

echo "=========================================================="
echo "  INSTALLATION DU DAEMON AUTOCORRECT SOUS LINUX (FEDORA)  "
echo "=========================================================="

# 1. Vérification des droits sudo
if [ "$EUID" -ne 0 ]; then
    echo "[!] Ce script doit être exécuté avec les privilèges sudo/root :"
    echo "    sudo ./install.sh"
    exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[*] Installation des paquets recommandés..."
if command -v dnf &>/dev/null; then
    echo "    -> Détection de Fedora (dnf)..."
    dnf install -y hunspell-fr libevdev python3 python3-evdev \
        python3-gobject libappindicator-gtk3 || true
elif command -v apt-get &>/dev/null; then
    echo "    -> Détection de Debian/Ubuntu (apt)..."
    apt-get update && apt-get install -y hunspell-fr libevdev2 python3 python3-evdev \
        python3-gi gir1.2-appindicator3-0.1 || true
elif command -v pacman &>/dev/null; then
    echo "    -> Détection d'Arch Linux (pacman)..."
    pacman -Sy --noconfirm hunspell-fr libevdev python python-evdev || true
fi

echo "[*] Chargement automatique du module noyau uinput..."
modprobe uinput || true
echo "uinput" > /etc/modules-load.d/uinput.conf

echo "[*] Configuration des règles udev (/dev/uinput et /dev/input)..."
cp "$(dirname "$0")/systemd/99-autocorrect-uinput.rules" /etc/udev/rules.d/99-autocorrect-uinput.rules
udevadm control --reload-rules
udevadm trigger

echo "[*] Ajout de l'utilisateur '$REAL_USER' au groupe 'input'..."
usermod -aG input "$REAL_USER"

echo "[*] Installation des dépendances Python (symspellpy)..."
python3 -m pip install -r "$PROJECT_DIR/requirements.txt" || true

echo "[*] Préparation des bases de fréquences bilingues (FR & EN)..."
python3 "$PROJECT_DIR/download_dicts.py" || true

echo "[*] Création du fichier de configuration par défaut si absent..."
if [ ! -f "$PROJECT_DIR/config.json" ]; then
    cp "$PROJECT_DIR/config.example.json" "$PROJECT_DIR/config.json"
    chown "$REAL_USER:$REAL_USER" "$PROJECT_DIR/config.json"
fi

echo ""
echo "=========================================================="
echo "  INSTALLATION TERMINÉE AVEC SUCCÈS !"
echo "=========================================================="
echo "Pour appliquer l'ajout au groupe sans redémarrer votre session :"
echo "    newgrp input"
echo ""
echo "Pour tester immédiatement le daemon :"
echo "    python3 run_daemon.py"
echo ""
echo "Pour installer en tant que service systemd :"
echo "    sudo cp systemd/autocorrect.service /etc/systemd/system/"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable --now autocorrect.service"
echo "=========================================================="
