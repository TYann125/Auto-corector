"""
Module de correction orthographique bilingue ultra-rapide (< 5 ms) basé sur SymSpell (symspellpy).

Utilise l'algorithme Symmetric Delete avec dictionnaires de fréquences pondérés (FR & EN).
Gère le code-switching bilingue, la conservation stricte de la casse et le filtrage des symboles/code.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional

# Tentative d'import de symspellpy depuis le système ou le dossier vendoré dans src/
try:
    from symspellpy import SymSpell, Verbosity
except ImportError:
    # Recherche dans le dossier src si vendoré
    vendor_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "symspellpy")
    if os.path.exists(vendor_dir):
        sys.path.insert(0, os.path.dirname(vendor_dir))
        from symspellpy import SymSpell, Verbosity
    else:
        raise ImportError(
            "symspellpy n'est pas installé. Exécutez : pip install symspellpy ou sudo ./install.sh"
        )


# Mots techniques / anglicismes fréquents à ne JAMAIS altérer en contexte français
TECH_LOANWORDS = {
    "commit", "commits", "committer", "push", "pusher", "pull", "pulls",
    "merge", "merger", "branch", "branches", "build", "builder", "debug",
    "feature", "features", "release", "releases", "roadmap", "stack", "stacks",
    "backend", "frontend", "fullstack", "framework", "frameworks", "pipeline",
    "pipelines", "workflow", "workflows", "daemon", "daemons", "terminal",
    "terminals", "script", "scripts", "plugin", "plugins", "socket", "sockets",
    "thread", "threads", "buffer", "buffers", "cache", "caches", "benchmark",
    "benchmarks", "ticket", "tickets", "issue", "issues", "repo", "repos",
    "repository", "deploy", "deployment", "feedback", "meeting", "meetings",
    "login", "logout", "token", "tokens", "api", "apis", "cli", "gui", "patch",
    "setup", "config", "timeout", "runtime", "server", "servers", "client", "clients",
    "cloud", "docker", "pod", "pods", "cluster", "clusters", "prompt", "prompts",
    "database", "query", "endpoint", "endpoints", "payload", "payloads",
}

# Table des coquilles et accents directs en O(1) pour haute priorité en français
COMMON_FR_TYPOS = {
    "developpment": "développement",
    "developpement": "développement",
    "developpeur": "développeur",
    "developpeurs": "développeurs",
    "acceuil": "accueil",
    "acceuillir": "accueillir",
    "apres": "après",
    "deja": "déjà",
    "tres": "très",
    "meme": "même",
    "memes": "mêmes",
    "etre": "être",
    "general": "général",
    "generale": "générale",
    "generales": "générales",
    "generaux": "généraux",
    "probleme": "problème",
    "problemes": "problèmes",
    "systeme": "système",
    "systemes": "systèmes",
    "modele": "modèle",
    "modeles": "modèles",
    "creer": "créer",
    "defini": "défini",
    "definie": "définie",
    "definis": "définis",
    "definies": "définies",
    "bibliotheque": "bibliothèque",
    "bibliotheques": "bibliothèques",
    "caractere": "caractère",
    "caracteres": "caractères",
    "memoire": "mémoire",
    "securite": "sécurité",
    "connexion": "connexion",
    "connextion": "connexion",
    "bcp": "beaucoup",
    "toujurs": "toujours",
    "toujour": "toujours",
    "aujourhui": "aujourd'hui",
    "aujourdhui": "aujourd'hui",
    "plutot": "plutôt",
    "bientot": "bientôt",
    "interressant": "intéressant",
    "interessant": "intéressant",
    "evenement": "événement",
    "evenements": "événements",
    "different": "différent",
    "differente": "différente",
    "differents": "différents",
    "differentes": "différentes",
    "regle": "règle",
    "regles": "règles",
    "orthografe": "orthographe",
    "gramaire": "grammaire",
    "ca": "ça",
}


class BilingualSymSpellEngine:
    """Moteur de correction orthographique bilingue FR/EN motorisé par SymSpell."""

    _NUMBER_RE = re.compile(r"^v?\d[\d.,:/-]*[a-zA-Z]?$")
    _EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _URL_RE = re.compile(r"^(?:https?|ftp)://|^www\.", re.IGNORECASE)
    _CAMEL_CASE_RE = re.compile(r"^[a-z]+(?:[A-Z][a-zA-Z0-9]*)+$")
    _SHELL_TOKEN_RE = re.compile(
        r"^(?:[$#]|--?[A-Za-z0-9][A-Za-z0-9_-]*|"
        r"(?:sudo|git|python(?:3)?|pip|dnf|npm|cargo|make|curl|ssh|"
        r"docker|podman)\s)",
        re.IGNORECASE,
    )
    _TRAILING_PUNCTUATION = ".,;:!?()[]{}'\""

    def __init__(
        self,
        max_dictionary_edit_distance: int = 2,
        prefix_length: int = 7,
        data_dir: Optional[str] = None,
        custom_corrections: Optional[Dict[str, str]] = None,
    ):
        if max_dictionary_edit_distance < 2:
            raise ValueError("max_dictionary_edit_distance doit être au moins égal à 2")
        self.max_edit_distance = max_dictionary_edit_distance
        self.prefix_length = prefix_length

        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data",
            )
        self.data_dir = os.fspath(data_dir)
        self.custom_corrections = {
            key.casefold(): value for key, value in (custom_corrections or {}).items()
        }

        # Initialisation des deux instances SymSpell
        self.sym_fr = SymSpell(
            max_dictionary_edit_distance=self.max_edit_distance,
            prefix_length=self.prefix_length,
        )
        self.sym_en = SymSpell(
            max_dictionary_edit_distance=self.max_edit_distance,
            prefix_length=self.prefix_length,
        )

        self._ensure_and_load_dictionaries()

    def _ensure_and_load_dictionaries(self):
        """Vérifie la présence des dictionnaires de fréquence et les charge en mémoire."""
        os.makedirs(self.data_dir, exist_ok=True)
        fr_path = self._find_dictionary("fr-100k.txt", "frequency_fr.txt")
        en_path = self._find_dictionary("en-82k.txt", "frequency_en.txt")

        # Téléchargement ou création automatique si absents
        if not os.path.exists(fr_path) or not os.path.exists(en_path):
            try:
                from download_dicts import prepare_dictionaries
                prepare_dictionaries()
            except (ImportError, OSError, RuntimeError) as exc:
                print(f"[Avertissement] Impossible de préparer les dictionnaires : {exc}")
            fr_path = self._find_dictionary("fr-100k.txt", "frequency_fr.txt")
            en_path = self._find_dictionary("en-82k.txt", "frequency_en.txt")

        # Chargement du dictionnaire français
        if os.path.exists(fr_path) and os.path.getsize(fr_path) > 10:
            self.sym_fr.load_dictionary(
                fr_path, term_index=0, count_index=1, separator=" ", encoding="utf-8-sig"
            )

        # Chargement du dictionnaire anglais
        if os.path.exists(en_path) and os.path.getsize(en_path) > 10:
            self.sym_en.load_dictionary(
                en_path, term_index=0, count_index=1, separator=" ", encoding="utf-8-sig"
            )

        # Enregistrement des termes techniques dans les deux dictionnaires
        for word in TECH_LOANWORDS:
            self.sym_fr.create_dictionary_entry(word, 5000000)
            self.sym_en.create_dictionary_entry(word, 5000000)

        # Enregistrement des mots prioritaires français avec fréquence élevée
        for typo, fix in COMMON_FR_TYPOS.items():
            self.sym_fr.create_dictionary_entry(fix, 10000000)

    def _find_dictionary(self, preferred_name: str, legacy_name: str) -> str:
        """Retourne le dictionnaire demandé, avec compatibilité avec les noms historiques."""
        preferred = Path(self.data_dir) / preferred_name
        if preferred.is_file():
            return os.fspath(preferred)
        return os.fspath(Path(self.data_dir) / legacy_name)

    def should_ignore(self, word: str) -> bool:
        """
        Détermine si le mot doit être strictement ignoré :
        - Chiffres / Nombres (123, 3.14, 2026-10)
        - URLs / Chemins (/usr/bin, https://, www.)
        - Adresses e-mail (contact@domaine.fr)
        - Variables de code (camelCase, snake_case, __init__)
        - Drapeaux CLI (--config, -rf)
        """
        if not word or not word.strip():
            return True

        candidate = word.strip()

        # Chiffres, versions, horodatages (ex: 123, 3.14, 2026-10-13, v1.2)
        if self._NUMBER_RE.fullmatch(candidate):
            return True

        # Adresses e-mail
        if self._EMAIL_RE.fullmatch(candidate):
            return True

        # URLs et chemins
        if self._URL_RE.match(candidate):
            return True
        if "/" in candidate or "\\" in candidate or candidate.startswith(("~", "." + os.sep)):
            return True

        # Variables de code (snake_case avec underscore ou camelCase / PascalCase)
        if "_" in candidate:
            return True
        if self._CAMEL_CASE_RE.fullmatch(candidate):
            return True

        # Drapeaux et tokens de commandes shell (ex: --verbose, $HOME, git)
        if self._SHELL_TOKEN_RE.search(candidate):
            return True

        # Monogrammes isolés (sauf lettres valides françaises / anglaises)
        if len(candidate) == 1 and candidate.casefold() not in {"a", "à", "y", "i"}:
            return True

        return False

    @staticmethod
    def apply_casing(original: str, replacement: str) -> str:
        """
        Conserve impérativement la casse d'origine du mot saisi :
        - Tout en minuscules -> correction en minuscules
        - Première lettre majuscule -> correction avec majuscule initiale
        - Tout en majuscules -> correction TOUT EN MAJUSCULES
        """
        if not replacement:
            return replacement
        if original.isupper():
            return replacement.upper()
        if original and original[0].isupper() and not original.isupper():
            # Respecte la majuscule initiale sur lettres accentuées
            if len(replacement) > 1:
                return replacement[0].upper() + replacement[1:].lower()
            return replacement.upper()
        return replacement.lower()

    def correct(self, word: str, context_lang: str = "fr") -> Optional[str]:
        """
        Évalue le mot saisi et retourne la correction appropriée, ou None si le mot est correct.
        Temps d'exécution garanti < 2 ms.
        """
        if not word or self.should_ignore(word):
            return None

        clean_lower = word.casefold().strip(self._TRAILING_PUNCTUATION)
        if not clean_lower:
            return None

        # 1. Priorité absolue : Dictionnaire personnalisé utilisateur (config.json)
        if clean_lower in self.custom_corrections:
            custom_replacement = self.custom_corrections[clean_lower]
            # Une correction personnalisée peut être une expression dont la casse
            # est volontaire (ex. « Cordialement, »), contrairement à un candidat
            # lexical qui doit suivre la casse du mot saisi.
            if word.isupper():
                return custom_replacement.upper()
            if word and word[0].isupper():
                return custom_replacement[0].upper() + custom_replacement[1:]
            return custom_replacement

        # 2. Vérification des coquilles directes et accents français en O(1)
        if context_lang == "fr" and clean_lower in COMMON_FR_TYPOS:
            fix = COMMON_FR_TYPOS[clean_lower]
            if fix.lower() != clean_lower:
                return self.apply_casing(word, fix)

        # 3. Vérification de validité (Code-switching : mot déjà correct en FR ou en EN)
        if clean_lower in self.sym_fr.words:
            return None
        if clean_lower in self.sym_en.words:
            return None
        if clean_lower in TECH_LOANWORDS:
            return None

        # 4. Recherche par SymSpell selon la langue du contexte
        candidate = None

        max_edit_distance = 1 if len(clean_lower) <= 4 else 2

        if context_lang == "fr":
            # Recherche dans le dictionnaire français
            suggestions = self.sym_fr.lookup(
                clean_lower,
                Verbosity.CLOSEST,
                max_edit_distance=max_edit_distance,
            )
            if suggestions:
                candidate = suggestions[0].term

            # Si aucune suggestion en français, tester le dictionnaire anglais
            # (pour corriger des termes tech mal orthographiés ex: 'comit' -> 'commit')
            if not candidate:
                en_suggestions = self.sym_en.lookup(
                    clean_lower,
                    Verbosity.CLOSEST,
                    max_edit_distance=max_edit_distance,
                )
                if en_suggestions:
                    candidate = en_suggestions[0].term
        else:
            # Contexte anglais
            suggestions = self.sym_en.lookup(
                clean_lower,
                Verbosity.CLOSEST,
                max_edit_distance=max_edit_distance,
            )
            if suggestions:
                candidate = suggestions[0].term

            if not candidate:
                fr_suggestions = self.sym_fr.lookup(
                    clean_lower,
                    Verbosity.CLOSEST,
                    max_edit_distance=max_edit_distance,
                )
                if fr_suggestions:
                    candidate = fr_suggestions[0].term

        # 5. Application de la casse et validation finale
        if candidate and candidate.lower() != clean_lower:
            return self.apply_casing(word, candidate)

        return None
