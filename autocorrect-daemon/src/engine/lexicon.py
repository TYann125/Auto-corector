"""
Module de lexique bilingue (Français & Anglais) ultra-rapide.

Charge en mémoire les vocabulaires français et anglais, ainsi qu'une liste
étendue de termes techniques / anglicismes courants utilisés dans un contexte francophone.
Permet des vérifications d'appartenance en O(1) et une recherche de candidats par distance
de Levenshtein bornée (< 5 ms).
"""

import os
import re
from typing import Set, Dict, List, Optional, Tuple

# Vocabulaire technique et anglicismes tolérés en français (code-switching)
COMMON_TECH_LOANWORDS: Set[str] = {
    "commit", "commits", "committer", "push", "pusher", "pull", "pulls",
    "merge", "merger", "branch", "branches", "build", "builder", "debug",
    "feature", "features", "release", "releases", "roadmap", "stack", "stacks",
    "backend", "frontend", "fullstack", "framework", "frameworks", "pipeline",
    "pipelines", "workflow", "workflows", "daemon", "daemons", "terminal",
    "terminals", "script", "scripts", "plugin", "plugins", "socket", "sockets",
    "thread", "threads", "buffer", "buffers", "cache", "caches", "benchmark",
    "benchmarks", "ticket", "tickets", "issue", "issues", "pr", "repo", "repos",
    "repository", "repositories", "deploy", "deployment", "feedback", "feedbacks",
    "meeting", "meetings", "standup", "sprint", "sprints", "backlog", "backlogs",
    "login", "logout", "token", "tokens", "cookie", "cookies", "api", "apis",
    "ui", "ux", "cli", "gui", "patch", "patches", "update", "updates", "setup",
    "config", "configs", "timeout", "runtime", "server", "servers", "client",
    "clients", "cloud", "docker", "pod", "pods", "cluster", "clusters",
}

# Mots français courants fondamentaux (formes fléchies, verbes, noms, adjectifs)
CORE_FRENCH_WORDS: Set[str] = {
    "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cet", "cette", "ces",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos",
    "votre", "vos", "leur", "leurs", "je", "tu", "il", "elle", "on", "nous", "vous",
    "ils", "elles", "me", "te", "se", "y", "en", "lui", "eux", "moi", "toi", "soi",
    "qui", "que", "quoi", "dont", "où", "quel", "quelle", "quels", "quelles",
    "et", "ou", "mais", "donc", "or", "ni", "car", "si", "comme", "quand", "lorsque",
    "puisque", "quoique", "afin", "parce", "dans", "sur", "sous", "avec", "sans",
    "pour", "par", "vers", "chez", "après", "avant", "pendant", "depuis", "contre",
    "entre", "derrière", "devant", "hors", "près", "selon", "malgré", "jusque", "vers",
    "être", "suis", "es", "est", "sommes", "êtes", "sont", "été", "étant", "serai",
    "seras", "sera", "serons", "serez", "seront", "serais", "serait", "serions",
    "seriez", "seraient", "étais", "était", "étions", "étiez", "étaient", "sois",
    "soit", "soyons", "soyez", "soient", "fus", "fut", "fûmes", "fûtes", "furent",
    "avoir", "ai", "as", "a", "avons", "avez", "ont", "eu", "ayant", "aurai", "auras",
    "aura", "aurons", "aurez", "auront", "aurais", "aurait", "aurions", "auriez",
    "auraient", "avais", "avait", "avions", "aviez", "avaient", "aie", "ait", "ayons",
    "ayez", "aient", "faire", "fais", "fait", "faisons", "faites", "font", "faisais",
    "faisait", "faisions", "faisiez", "faisaient", "ferai", "feras", "fera", "ferons",
    "ferez", "feront", "ferais", "ferait", "ferions", "feriez", "feraient",
    "aller", "vais", "vas", "va", "allons", "allez", "vont", "allais", "allait",
    "allions", "alliez", "allaient", "irai", "iras", "ira", "irons", "irez", "iront",
    "dire", "dis", "dit", "disons", "dites", "disent", "disais", "disait", "disions",
    "pouvoir", "peux", "peut", "pouvons", "pouvez", "peuvent", "pouvais", "pouvait",
    "pourrai", "pourras", "pourra", "pourrons", "pourrez", "pourront", "pourrais",
    "pourrait", "pourrions", "pourriez", "pourraient", "puisse", "puisses", "puissent",
    "vouloir", "veux", "veut", "voulons", "voulez", "veulent", "voulais", "voulait",
    "voudrai", "voudras", "voudra", "voudrons", "voudrez", "voudront", "voudrais",
    "voudrait", "voudrions", "voudriez", "voudraient", "veuille", "veuillent",
    "savoir", "sais", "sait", "savons", "savez", "savent", "savais", "savait", "saurai",
    "voir", "vois", "voit", "voyons", "voyez", "voient", "voyais", "voyait", "verrai",
    "devoir", "dois", "doit", "devons", "devez", "doivent", "devais", "devait", "devrai",
    "falloir", "faut", "fallait", "faudra", "faudrait",
    "bien", "mal", "mieux", "très", "trop", "plus", "moins", "beaucoup", "peu", "assez",
    "tant", "autant", "toujours", "jamais", "souvent", "parfois", "rarement", "encore",
    "déjà", "ici", "là", "ailleurs", "partout", "maintenant", "aujourd'hui", "demain",
    "hier", "bientôt", "tard", "tôt", "ensemble", "surtout", "seulement", "vraiment",
    "aussi", "ainsi", "alors", "oui", "non", "merci", "bonjour", "bonsoir", "salut",
    "homme", "hommes", "femme", "femmes", "enfant", "enfants", "personne", "personnes",
    "jour", "jours", "journée", "journées", "matin", "soir", "nuit", "nuits", "heure",
    "heures", "minute", "minutes", "seconde", "secondes", "temps", "moment", "moments",
    "fois", "chose", "choses", "vie", "monde", "pays", "ville", "villes", "maison",
    "maisons", "porte", "portes", "chambre", "rue", "travail", "travaux", "projet",
    "projets", "problème", "problèmes", "question", "questions", "réponse", "réponses",
    "idée", "idées", "partie", "parties", "côté", "côtés", "endroit", "place",
    "cas", "fait", "faits", "façon", "manière", "point", "points", "mot", "mots",
    "texte", "textes", "phrase", "phrases", "page", "pages", "livre", "livres",
    "lettre", "lettres", "nom", "noms", "dossier", "dossiers", "fichier", "fichiers",
    "code", "codes", "fonction", "fonctions", "système", "systèmes", "utilisateur",
    "utilisateurs", "machine", "machines", "serveur", "serveurs", "clavier", "claviers",
    "écran", "écrans", "fenêtre", "fenêtres", "erreur", "erreurs", "accès", "réseau",
    "compte", "comptes", "action", "actions", "niveau", "niveaux", "groupe", "groupes",
    "nouveau", "nouveaux", "nouvelle", "nouvelles", "grand", "grands", "grande", "grandes",
    "petit", "petits", "petite", "petites", "bon", "bons", "bonne", "bonnes", "mauvais",
    "mauvaise", "mauvaises", "beau", "beaux", "belle", "belles", "jeune", "jeunes",
    "vieux", "vieille", "vieilles", "autre", "autres", "même", "mêmes", "tout", "tous",
    "toute", "toutes", "premier", "premiers", "première", "premières", "dernier",
    "derniers", "dernière", "dernières", "seul", "seuls", "seule", "seules", "long",
    "longs", "longue", "longues", "court", "courts", "courte", "courtes", "haut",
    "hauts", "haute", "hautes", "bas", "basse", "basses", "facile", "faciles", "difficile",
    "difficiles", "simple", "simples", "rapide", "rapides", "clair", "clairs", "claire",
    "claires", "certain", "certains", "certaine", "certaines", "possible", "possibles",
    "impossible", "impossibles", "important", "importants", "importante", "importantes",
    "vrai", "vrais", "vraie", "vraies", "faux", "fausse", "fausses", "général", "générale",
    "direct", "directe", "actuel", "actuelle", "propre", "propres",
    "développement", "développeur", "développeurs", "correction", "corrections",
    "orthographe", "grammaire", "langage", "langages", "langue", "langues",
    "automatique", "automatiques", "local", "locale", "locaux", "locales",
    "service", "services", "mémoire", "vitesse", "performance", "performances",
    "configuration", "configurations", "paramètre", "paramètres", "outil", "outils",
}

# Mots anglais fondamentaux
CORE_ENGLISH_WORDS: Set[str] = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not",
    "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from",
    "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would",
    "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which",
    "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know",
    "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
    "way", "even", "new", "want", "because", "any", "these", "give", "day", "most",
    "us", "is", "are", "was", "were", "been", "has", "had", "does", "did", "doing",
    "development", "developer", "developers", "develop", "software", "hardware",
    "correction", "corrections", "spelling", "grammar", "language", "languages",
    "automatic", "automatically", "realtime", "service", "daemon", "daemonize",
    "keyboard", "keyboards", "input", "output", "device", "devices", "system",
    "systems", "file", "files", "directory", "directories", "folder", "folders",
    "user", "users", "computer", "screen", "window", "windows", "error", "errors",
    "typo", "typos", "fast", "speed", "test", "tests", "testing", "success", "failure",
    "hello", "hi", "thanks", "thank", "please", "yes", "cool", "great", "nice", "awesome",
}

# Coquilles et fautes fréquentes avec corrections directes (instantanéité absolue)
COMMON_TYPOS_MAP: Dict[str, str] = {
    # Coquilles françaises fréquentes et accents manquants
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
    "parmit": "parmi",
    "malgrès": "malgré",
    "bcp": "beaucoup",
    "toujurs": "toujours",
    "toujour": "toujours",
    "quelquechose": "quelque chose",
    "aujourhui": "aujourd'hui",
    "aujourdhui": "aujourd'hui",
    "plutot": "plutôt",
    "bientot": "bientôt",
    "interressant": "intéressant",
    "interessant": "intéressant",
    "language": "langage",  # Faute d'anglicisme fréquente en français quand contexte FR
    "evenement": "événement",
    "evenements": "événements",
    "different": "différent",
    "differente": "différente",
    "differents": "différents",
    "differentes": "différentes",
    "regle": "règle",
    "regles": "règles",
    "entrain": "en train",
    "faute": "faute",
    "fautes": "fautes",
    "orthografe": "orthographe",
    "gramaire": "grammaire",
    "clavier": "clavier",
    "ca": "ça",

    # Coquilles anglaises fréquentes
    "teh": "the",
    "recieve": "receive",
    "recieved": "received",
    "seperate": "separate",
    "seperated": "separated",
    "definately": "definitely",
    "tommorow": "tomorrow",
    "untill": "until",
    "occured": "occurred",
    "begining": "beginning",
    "goverment": "government",
    "beleive": "believe",
    "peice": "piece",
    "freind": "friend",
    "woudl": "would",
    "coudl": "could",
    "shoudl": "should",
    "wierd": "weird",
    "framwork": "framework",
    "comit": "commit",
    "pipleine": "pipeline",
    "deamon": "daemon",
}


class BilingualLexicon:
    """Gère le vocabulaire bilingue et la recherche rapide de corrections."""

    def __init__(self, load_system_words: bool = True):
        self.french_words: Set[str] = set(CORE_FRENCH_WORDS)
        self.english_words: Set[str] = set(CORE_ENGLISH_WORDS)
        self.tech_words: Set[str] = set(COMMON_TECH_LOANWORDS)
        self.direct_typos: Dict[str, str] = dict(COMMON_TYPOS_MAP)

        if load_system_words:
            self._load_system_dictionaries()

    def _load_system_dictionaries(self):
        """Enrichit le vocabulaire anglais à partir de /usr/share/dict/words si disponible."""
        words_path = "/usr/share/dict/words"
        if os.path.exists(words_path):
            try:
                count = 0
                with open(words_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        w = line.strip().lower()
                        if w.isalpha() and 2 <= len(w) <= 25:
                            self.english_words.add(w)
                            count += 1
                            if count >= 60000:  # Limite pour garder une empreinte RAM minimale (< 15 Mo)
                                break
            except Exception:
                pass

    def is_valid_french(self, word: str) -> bool:
        """Vérifie si le mot existe dans le lexique français ou technique."""
        w = word.lower()
        return w in self.french_words or w in self.tech_words

    def is_valid_english(self, word: str) -> bool:
        """Vérifie si le mot existe dans le lexique anglais ou technique."""
        w = word.lower()
        return w in self.english_words or w in self.tech_words

    def is_valid_any(self, word: str) -> bool:
        """Vérifie si le mot est valide dans l'une des deux langues (ou mot technique)."""
        w = word.lower()
        return w in self.french_words or w in self.english_words or w in self.tech_words

    def get_direct_correction(self, word: str) -> Optional[str]:
        """Retourne une correction directe de coquille connue en O(1)."""
        w_lower = word.lower()
        if w_lower in self.direct_typos:
            return self._match_casing(word, self.direct_typos[w_lower])
        return None

    def find_nearest_word(self, word: str, target_lang: str = "fr", max_distance: int = 1) -> Optional[str]:
        """
        Recherche le mot le plus proche avec une distance de Damerau-Levenshtein <= max_distance.
        Optimisé pour s'exécuter en moins de 3 millisecondes.
        """
        w_lower = word.lower()
        target_vocab = self.french_words if target_lang == "fr" else self.english_words

        # Candidats par longueur proche (longueur ± max_distance)
        word_len = len(w_lower)
        best_candidate = None
        best_dist = max_distance + 1

        for candidate in target_vocab:
            cand_len = len(candidate)
            if abs(cand_len - word_len) > max_distance:
                continue

            dist = self.damerau_levenshtein(w_lower, candidate, max_distance)
            if dist <= max_distance and dist < best_dist:
                best_dist = dist
                best_candidate = candidate
                if dist == 1:
                    break

        if best_candidate:
            return self._match_casing(word, best_candidate)
        return None

    @staticmethod
    def damerau_levenshtein(s1: str, s2: str, max_dist: int = 2) -> int:
        """Distance de Damerau-Levenshtein bornée (gère insertions, suppressions, substitutions, transpositions)."""
        len1, len2 = len(s1), len(s2)
        if abs(len1 - len2) > max_dist:
            return max_dist + 1

        d = {}
        for i in range(-1, len1 + 1):
            d[(i, -1)] = i + 1
        for j in range(-1, len2 + 1):
            d[(-1, j)] = j + 1

        for i in range(len1):
            for j in range(len2):
                cost = 0 if s1[i] == s2[j] else 1
                d[(i, j)] = min(
                    d[(i - 1, j)] + 1,       # suppression
                    d[(i, j - 1)] + 1,       # insertion
                    d[(i - 1, j - 1)] + cost # substitution
                )
                if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                    d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost) # transposition

        return d[(len1 - 1, len2 - 1)]

    @staticmethod
    def _match_casing(original: str, replacement: str) -> str:
        """Adapte la casse de la correction à celle du mot original."""
        if original.isupper():
            return replacement.upper()
        if original and original[0].isupper():
            return replacement.capitalize()
        return replacement.lower()
