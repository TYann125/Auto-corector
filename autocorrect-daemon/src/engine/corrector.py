"""
Moteur central de correction orthographique et grammaticale en temps réel.

Coordonne le lexique bilingue, le détecteur de langue, le moteur de règles grammaticales
et l'éventuel serveur LanguageTool local pour délivrer une correction en moins de 10 millisecondes.
"""

import time
import re
from typing import Optional, List, Tuple
from .lexicon import BilingualLexicon
from .detector import LanguageDetector
from .grammar_rules import StrictGrammarEngine
from .spelling_engine import BilingualSymSpellEngine
from .languagetool_client import LanguageToolClient


class TextCorrectionEngine:
    """Moteur bilingue ultra-rapide (< 5 ms) et strict pour Linux."""

    def __init__(
        self,
        default_lang: str = "fr",
        enable_languagetool: bool = False,
        languagetool_endpoint: str = "http://127.0.0.1:8081/v2/check",
        custom_corrections: Optional[dict] = None,
    ):
        self.default_lang = default_lang
        self.lexicon = BilingualLexicon(load_system_words=False)
        self.detector = LanguageDetector(self.lexicon)
        self.grammar = StrictGrammarEngine(self.lexicon)
        self.spelling = BilingualSymSpellEngine(custom_corrections=custom_corrections)
        self.lt_client = LanguageToolClient(endpoint=languagetool_endpoint, enabled=enable_languagetool)

        # Pré-vérification de disponibilité de LanguageTool
        if enable_languagetool:
            self.lt_client.check_availability()

    def process_word(self, current_word: str, recent_words: List[str]) -> Optional[str]:
        """
        Analyse le mot qui vient d'être saisi et retourne sa correction, ou None s'il est correct.
        Durée d'exécution garantie < 5 ms.
        """
        if not current_word or len(current_word) == 0:
            return None

        # 1. Filtre les identifiants techniques, nombres, URLs, commandes, emails
        if self.spelling.should_ignore(current_word):
            return None

        clean_word = current_word.strip()

        # 2. Détection de la langue du contexte de la phrase
        context_lang = self.detector.detect_context_language(recent_words, default_lang=self.default_lang)

        # 3. Vérification des accords grammaticaux stricts prioritaires
        grammar_correction = self.grammar.check_agreement(clean_word, recent_words, context_lang)
        if grammar_correction and grammar_correction != clean_word:
            return grammar_correction

        # 4. Correction orthographique ultra-rapide par SymSpell (fréquences pondérées FR & EN)
        sym_correction = self.spelling.correct(clean_word, context_lang=context_lang)
        if sym_correction:
            return sym_correction

        return None
