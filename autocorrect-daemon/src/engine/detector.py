"""
Module de détection automatique de la langue (Français / Anglais) en temps réel.

Analyse le contexte immédiat (phrase en cours de frappe) et les marqueurs linguistiques
pour déterminer la langue dominante, tout en gérant le mélange de langues (code-switching)
afin de ne jamais forcer de fausse traduction.
"""

from typing import List, Tuple
from .lexicon import BilingualLexicon

# Mots grammaticaux discriminants pour le français
FRENCH_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de", "ce", "cet", "cette", "ces",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos",
    "votre", "vos", "leur", "leurs", "je", "tu", "il", "elle", "on", "nous", "vous",
    "ils", "elles", "dans", "sur", "avec", "pour", "par", "est", "sont", "ont", "fait",
    "qui", "que", "quoi", "dont", "où", "mais", "ou", "et", "donc", "or", "ni", "car",
    "très", "bien", "aussi", "plus", "moins", "ici", "tout", "tous", "comme", "j'ai", "c'est",
}

# Mots grammaticaux discriminants pour l'anglais
ENGLISH_STOPWORDS = {
    "the", "a", "an", "this", "that", "these", "those", "my", "your", "his", "her",
    "our", "their", "its", "i", "you", "he", "she", "it", "we", "they", "me", "him",
    "her", "us", "them", "in", "on", "at", "for", "with", "from", "by", "to", "of",
    "is", "are", "was", "were", "been", "have", "has", "had", "do", "does", "did",
    "will", "would", "can", "could", "should", "not", "but", "and", "or", "so", "if",
    "as", "than", "then", "very", "also", "just", "now", "what", "which", "who",
}


class LanguageDetector:
    """Détecteur de langue bilingue FR/EN temps réel."""

    def __init__(self, lexicon: BilingualLexicon):
        self.lexicon = lexicon

    def detect_context_language(self, recent_words: List[str], default_lang: str = "fr") -> str:
        """
        Détermine la langue du contexte récent (derniers 5 à 10 mots).
        Retourne 'fr' ou 'en'.
        """
        if not recent_words:
            return default_lang

        fr_score = 0
        en_score = 0

        for word in recent_words:
            w = word.lower().strip(".,;:!?()[]{}'\"")
            if not w:
                continue

            # Mots discriminants grammaticaux (poids fort)
            if w in FRENCH_STOPWORDS:
                fr_score += 3
            elif w in ENGLISH_STOPWORDS:
                en_score += 3
            else:
                # Vérification vocabulaire général
                in_fr = self.lexicon.is_valid_french(w)
                in_en = self.lexicon.is_valid_english(w)

                if in_fr and not in_en:
                    fr_score += 1
                elif in_en and not in_fr:
                    en_score += 1

        if fr_score > en_score:
            return "fr"
        elif en_score > fr_score:
            return "en"
        return default_lang

    def classify_word(self, word: str, context_lang: str) -> Tuple[str, bool]:
        """
        Classifie un mot :
        Retourne (detected_lang, is_valid).
        Gère le code-switching : un mot valide dans l'autre langue est accepté sans être modifié.
        """
        w = word.lower()

        # 1. Anglicisme ou terme tech reconnu
        if w in self.lexicon.tech_words:
            return "en", True

        # 2. Vérification dans la langue du contexte
        if context_lang == "fr":
            if self.lexicon.is_valid_french(w):
                return "fr", True
            if self.lexicon.is_valid_english(w):
                # Mot anglais valide au sein d'une phrase en français (code-switching)
                return "en", True
        else:
            if self.lexicon.is_valid_english(w):
                return "en", True
            if self.lexicon.is_valid_french(w):
                # Mot français au sein d'une phrase anglaise
                return "fr", True

        # Mot inconnu / suspect de coquille
        return context_lang, False
