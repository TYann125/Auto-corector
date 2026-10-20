# AutoCorrect Daemon (Linux / Fedora)

Daemon local sous Linux (Fedora, Wayland & X11) qui corrige vos fautes d'orthographe, de frappe et de grammaire **automatiquement et en temps réel, au fur et à mesure que vous tapez**.

---

## 1. Faisabilité Technique & Architecture (Wayland / X11)

### Pourquoi les méthodes traditionnelles échouent sous Wayland
Sous **X11**, les outils historiques comme `xdotool`, `xte` ou `xbindkeys` utilisaient les API globales du serveur X (`XRecord`, `XGrabKeyboard`, `XSendEvent`).  
Sous **Wayland** (compositeurs KDE Plasma / KWin, GNOME / Mutter, Hyprland, Sway), les fenêtres sont **strictement isolées** pour des raisons de sécurité : une application standard ne peut ni espionner les frappes des autres fenêtres, ni injecter d'événements arbitraires.

### La solution universelle : le sous-système noyau Linux (`evdev` & `uinput`)
Ce daemon opère **sous le compositeur d'affichage**, directement au niveau du noyau Linux :
1. **Écoute bas niveau (`/dev/input/event*`) :**  
   Le daemon écoute les paquets binaires bruts `struct input_event` (EV_KEY) émis par les claviers physiques.
   - **Mode passif (monitoring) :** Le daemon ne capture pas le clavier de manière exclusive (`grab`). Vos frappes continuent donc d'arriver instantanément à l'application active avec **zéro latence matérielle**.
2. **Détection de fin de mot :**  
   Une machine à états interne reconstitue les mots tapés en tenant compte de la disposition (AZERTY / QWERTY), des modificateurs (Shift, AltGr, CapsLock) et des touches de navigation.
   Dès qu'un délimiteur est pressé (Espace, Entrée, ponctuation), le mot est évalué.
3. **Suppression et injection chirurgicale (`/dev/uinput`) :**  
   Si une faute est détectée :
   - Le daemon émet via un clavier virtuel noyau (`/dev/uinput`) le nombre exact de retours arrière (`KEY_BACKSPACE`) nécessaires pour effacer le mot erroné et le délimiteur affiché ($N = \text{len}(\text{mot}) + \text{len}(\text{délimiteur})$).
   - Il tape instantanément le mot corrigé et le délimiteur.
   - **Protection anti-boucle infinie :** Le daemon filtre son propre périphérique virtuel et arme un verrou atomique `is_injecting` pendant l'émission des frappes.

---

## 2. Moteur Bilingue Ultra-Rapide (< 100 ms) & Comportement Strict

Le moteur linguistique est conçu pour respecter deux impératifs absolus :
1. **Latence d'évaluation mesurée à ~0.002 ms (2 microsecondes)**, bien en deçà du budget maximal de 100 ms.
2. **Comportement strict :** Aucune reformulation, aucun changement de registre. Uniquement des corrections de coquilles, d'accents et d'accords évidents.

### Fonctionnalités linguistiques :
- **Détection automatique de la langue en temps réel :** Analyse les marqueurs grammaticaux de la phrase en cours (Français / Anglais).
- **Code-switching bilingue préservé :** Les termes techniques ou anglicismes saisis dans une phrase en français (ex: *« J'ai fait un commit et push sur le repo »*) sont reconnus comme valides et ne sont **jamais traduits de force**.
- **Accords stricts :**
  - Accord en nombre après déterminant pluriel (*« les maison »* $\to$ *« les maisons »*, *« des erreur »* $\to$ *« des erreurs »*).
  - Homophones grammaticaux et accents contextuels (*« grace a »* $\to$ *« grâce à »*, *« au moment ou »* $\to$ *« au moment où »*, *« ca »* $\to$ *« ça »*).
- **Option LanguageTool local :** Un connecteur HTTP optionnel vers un serveur LanguageTool local (`http://localhost:8081/v2/check`) avec coupe-circuit strict (timeout de 80 ms).

---

## 3. Gestion des Permissions sous Linux

L'accès à `/dev/input/event*` (écoute) et `/dev/uinput` (injection) est restreint par défaut sous Fedora pour protéger l'utilisateur contre les enregistreurs de frappe malveillants.

Deux méthodes d'exécution sont disponibles :

### Méthode A : Configuration udev (Recommandée - Sans mot de passe root)
Permet au daemon de tourner sous votre compte utilisateur sans `sudo`.

1. Installez la règle udev fournie dans `systemd/99-autocorrect-uinput.rules` :
   ```bash
   sudo cp systemd/99-autocorrect-uinput.rules /etc/udev/rules.d/
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
2. Ajoutez votre compte au groupe `input` :
   ```bash
   sudo usermod -aG input $USER
   ```
3. Chargez le module noyau `uinput` :
   ```bash
   sudo modprobe uinput
   echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
   ```
4. Appliquez le groupe à votre session courante (ou reconnectez-vous) :
   ```bash
   newgrp input
   ```

### Méthode B : Exécution via `sudo`
Si vous préférez tester immédiatement sans modifier vos groupes :
```bash
sudo python3 run_daemon.py
```

---

## 4. Installation & Démarrage Rapide

### Étape 1 : Installation automatique des dépendances
Exécutez le script d'installation :
```bash
sudo ./install.sh
```
Ce script installe les paquets recommandés (`hunspell-fr`, `libevdev`), charge le module noyau `uinput`, configure la règle `udev` et ajoute votre utilisateur au groupe `input`.

### Étape 2 : Vérification des permissions
Avant de lancer le daemon, vérifiez que tout est débloqué :
```bash
python3 run_daemon.py --check-permissions
```

### Étape 3 : Lancer la suite de tests unitaires et benchmarks
```bash
python3 -m unittest discover -s tests -v
```
Tous les tests valident le mapping scancodes AZERTY/QWERTY, la conservation de la casse, le code-switching, les accords grammaticaux et le pipeline virtuel uinput.

### Étape 4 : Lancer le daemon manuellement
```bash
python3 run_daemon.py
```
Options disponibles :
- `--layout azerty` ou `--layout qwerty` : Sélection de la disposition matérielle.
- `--lang fr` ou `--lang en` : Langue dominante par défaut.
- `--debug` : Affiche en temps réel chaque mot capturé et chaque frappe dans la console.
- `--languagetool` : Active le pont vers un serveur local LanguageTool.
- `--config chemin/vers/config.json` : Fichier de configuration spécifique.

---

## 5. Configuration (`config.json`)

Le fichier `config.json` (créé à partir de `config.example.json`) permet d'ajuster les paramètres :

```json
{
    "layout": "azerty",
    "default_language": "fr",
    "key_delay_ms": 5.0,
    "enable_languagetool": false,
    "languagetool_endpoint": "http://127.0.0.1:8081/v2/check",
    "virtual_device_name": "AutoCorrect Virtual Keyboard",
    "log_level": "INFO",
    "custom_corrections": {
        "cdl": "Cordialement,",
        "bjr": "Bonjour,",
        "asap": "dès que possible"
    }
}
```

---

## 6. Déploiement en tant que Service Système (`systemd`)

Pour que le daemon démarre automatiquement en arrière-plan à l'allumage de votre machine Fedora :

1. Copiez le projet dans `/opt/autocorrect-daemon` (ou adaptez le chemin dans le service) :
   ```bash
   sudo cp -r . /opt/autocorrect-daemon
   ```
2. Installez le service systemd :
   ```bash
   sudo cp systemd/autocorrect.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```
3. Activez et démarrez le service :
   ```bash
   sudo systemctl enable --now autocorrect.service
   ```
4. Consultez les logs en temps réel :
   ```bash
   journalctl -u autocorrect.service -f
   ```
