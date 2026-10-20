@workspace Role: Senior Python / Linux Kernel Engineer.
Task: Générer l'intégralité d'un projet d'autocorrection bilingue (FR/EN) temps réel pour Linux (Fedora/Wayland) via `evdev` et `/dev/uinput`.

# DIRECTIVE DE STRUCTURE ET DOSSIER
- Créer un répertoire de projet dédié et propre (ex: `~/autocorrect-daemon/`), NE PAS placer les fichiers directement en vrac sur le Bureau.

# MATRICE DES CONTRAINTES STRICTES & PERFORMANCE
1. ZERO INOTIFY : Interdiction absolue de `watchdog` ou `pyinotify`. Chargement unique des dictionnaires en RAM au démarrage. Sauvegarde asynchrone de `user_learning.json` à l'arrêt ou via timer de 15 minutes.
2. ANTI-COLLISION : File d'attente FIFO (`keystroke_queue`) pour verrouiller la saisie physique pendant l'injection `uinput`. Ajouter un espace unique post-correction, puis dépiler les touches en attente.
3. REVERSION SMARTPHONE : Appui sur `KEY_BACKSPACE` post-correction = effacement du mot corrigé, réinjection du mot original et ajout en liste noire temporaire (30 min).
4. DISTANCE D'ÉDITION ADAPTATIVE : `max_edit_distance = 1` si `len(mot) <= 4`, sinon `2`.
5. APOSTROPHES & ÉLISIONS : Correction automatique des contractions manquantes (`quil` -> `qu'il`, `cest` -> `c'est`, `jai` -> `j'ai`, `daccord` -> `d'accord`, `quon` -> `qu'on`).
6. PRÉSERVATION DE LA CASSE : Respect strict des minuscules, Majuscules initiales et TOUT EN MAJUSCULES.
7. REGEX D'EXCLUSION : Ignorer URLs, e-mails, chemins UNIX, variables (`snake_case`, `camelCase`) et commandes CLI.
8. GRAMMAIRE DE PHRASE : Timer d'inactivité (1.2s) envoyant le tampon de phrase au serveur local LanguageTool (`http://127.0.0.1:8081/v2/check`) pour corriger accords et conjugaisons. Interruption immédiate si une touche est pressée.
9. TRAY ICON : Icône `pystray` dans la barre des tâches ("A" vert = actif, "A" gris = suspendu) avec menu contextuel (Toggle, FR/EN, Quitter).

# LIVRABLES À GÉNÉRER DANS LE DOSSIER DE PROJET

1. `spelling_engine.py` : Moteur `symspellpy` (FR/EN), élisions, casse, règles de distance et exclusions Regex.
2. `idle_checker.py` : Timer debounce 1.2s, buffer de phrase, intégration LanguageTool HTTP local.
3. `reversion_handler.py` : Interception de `KEY_BACKSPACE`, restauration du mot brut et cache 30m.
4. `daemon.py` : Boucle principale `evdev`/`uinput`, gestion FIFO anti-collision, réécriture propre.
5. `tray_icon.py` : Gestionnaire `pystray` avec icône dynamique et bascule FR/EN.
6. `download_dicts.py` : Script de téléchargement automatique des dicos de fréquence (`fr-100k.txt`, `en-82k.txt`).
7. `test_autocorrect.py` : Suite de tests automatisés `unittest` couvrant toutes les fonctionnalités.
8. `setup.sh` : Script Bash d'installation des paquets Fedora, règles `udev` (`uinput`), et groupes utilisateur.
9. `requirements.txt` : Liste des dépendances Python (`symspellpy`, `evdev`, `pystray`, `Pillow`, `requests`).
10. `README.md` : Documentation complète du projet (installation, lancement, configuration).

Génère l'intégralité du code fichier par fichier de manière modulaire et directement utilisable.
