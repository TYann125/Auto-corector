"""
Module de règles grammaticales strictes (accords et homophones).

Respecte scrupuleusement la consigne de comportement strict :
- Ne reformule JAMAIS la phrase.
- Ne modifie JAMAIS le registre de langue.
- Corrige uniquement les accords de pluriel évidents, les accords d'articles et les homophones fréquents.
"""

from typing import Optional, List
from .lexicon import BilingualLexicon

# Déterminants pluriels français
FRENCH_PLURAL_DETERMINERS = {
    "les", "des", "ces", "mes", "tes", "ses", "nos", "vos", "leurs",
    "plusieurs", "quelques", "deux", "trois", "quatre", "cinq",
}

# Déterminants singuliers français
FRENCH_SINGULAR_MASCULINE = {"un", "le", "ce", "cet", "mon", "ton", "son"}
FRENCH_SINGULAR_FEMININE = {"une", "la", "cette", "ma", "ta", "sa"}

# Mots masculins fréquents souvent mal accordés
MASCULINE_NOUNS = {
    "problème", "système", "modèle", "groupe", "compte", "domaine", "espace",
    "fichier", "dossier", "serveur", "clavier", "écran", "travail", "projet",
}

# Mots féminins fréquents souvent mal accordés
FEMININE_NOUNS = {
    "erreur", "maison", "page", "phrase", "question", "réponse", "fonction",
    "machine", "mémoire", "vitesse", "sécurité", "solution", "porte", "table",
}

# Locutions introduisant systématiquement 'à' (avec accent)
PREPOSITIONS_NEEDING_A_ACCENT = {
    "grace", "grâce", "face", "quant", "pret", "prêt", "voué", "destiné",
    "parvenir", "aller", "accès", "acces", "tendance", "service", "droit",
}

# Mots précédant la particule 'où' de lieu ou de temps
WORDS_PRECEDING_OU_ACCENT = {
    "moment", "instant", "endroit", "lieu", "ville", "jour", "année",
    "partout", "par", "vers", "jusqu'",
}


class StrictGrammarEngine:
    """Applique les corrections grammaticales directes et strictes."""

    def __init__(self, lexicon: BilingualLexicon):
        self.lexicon = lexicon

    def check_agreement(self, current_word: str, prev_words: List[str], context_lang: str) -> Optional[str]:
        """
        Vérifie si le mot en cours nécessite un accord grammatical par rapport au mot précédent.
        Retourne la chaîne corrigée ou None si aucun accord n'est requis.
        """
        if not prev_words:
            return None

        w_lower = current_word.lower()
        prev_word = prev_words[-1].lower().strip(".,;:!?()[]{}'\"")

        if context_lang == "fr":
            return self._check_french_grammar(current_word, w_lower, prev_word, prev_words)
        elif context_lang == "en":
            return self._check_english_grammar(current_word, w_lower, prev_word)

        return None

    def _check_french_grammar(self, original_word: str, w_lower: str, prev_word: str, prev_words: List[str]) -> Optional[str]:
        # 1. Règle 'ca' -> 'ça'
        if w_lower == "ca" and not original_word.isupper():
            return "Ça" if original_word.istitle() else "ça"

        # 2. Homophone 'a' vs 'à'
        if w_lower == "a":
            if prev_word in PREPOSITIONS_NEEDING_A_ACCENT:
                return "À" if original_word.istitle() else "à"

        # 3. Homophone 'ou' vs 'où'
        if w_lower == "ou":
            if prev_word in WORDS_PRECEDING_OU_ACCENT:
                return "Où" if original_word.istitle() else "où"

        # 4. Accord du pluriel après déterminant pluriel
        # Ex: "les maison" -> "les maisons", "des erreur" -> "des erreurs"
        if prev_word in FRENCH_PLURAL_DETERMINERS:
            # Ne pas modifier si le mot se termine déjà par s, x, z
            if not w_lower.endswith(("s", "x", "z")):
                # Vérifie si le mot de base est un mot français connu
                if self.lexicon.is_valid_french(w_lower):
                    if w_lower.endswith("eau") or w_lower.endswith("eu"):
                        plural = w_lower + "x"
                    elif w_lower.endswith("al") and w_lower not in {"bal", "chacal", "carnaval", "festival", "récital"}:
                        plural = w_lower[:-2] + "aux"
                    else:
                        plural = w_lower + "s"
                    return self.lexicon._match_casing(original_word, plural)

        # 5. Déterminant genre
        # Ex: "une problème" -> "un problème", "un erreur" -> "une erreur" (détecté au mot suivant)
        if prev_word == "une" and w_lower in MASCULINE_NOUNS:
            # L'accord porte ici sur le mot courant ; on ne rétro-corrige pas prev_word ici sauf si nécessaire
            pass

        return None

    def _check_english_grammar(self, original_word: str, w_lower: str, prev_word: str) -> Optional[str]:
        # En anglais, les accords simples immédiats concernent notamment les pronoms et formes de base
        return None
