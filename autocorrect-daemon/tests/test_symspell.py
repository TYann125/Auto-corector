"""
Tests unitaires et benchmarks pour le moteur de correction SymSpell bilingue (BilingualSymSpellEngine).
Mesure la latence exacte par mot (< 5 ms).
"""

import os
import sys
import time
import unittest

# Assure l'accès aux modules src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from engine.spelling_engine import BilingualSymSpellEngine


class TestBilingualSymSpellEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = BilingualSymSpellEngine(
            max_dictionary_edit_distance=2,
            prefix_length=7,
            custom_corrections={
                "cdl": "Cordialement,",
                "bjr": "Bonjour,",
                "asap": "dès que possible",
            },
        )

    def test_configuration_parameters(self):
        """Vérifie la configuration requise : edit_distance=2 et prefix_length=7."""
        self.assertEqual(self.engine.max_edit_distance, 2)
        self.assertEqual(self.engine.prefix_length, 7)
        self.assertEqual(self.engine.sym_fr._max_dictionary_edit_distance, 2)
        self.assertEqual(self.engine.sym_fr._prefix_length, 7)
        self.assertEqual(self.engine.sym_en._max_dictionary_edit_distance, 2)
        self.assertEqual(self.engine.sym_en._prefix_length, 7)

    def test_french_frequency_corrections(self):
        """Vérifie la correction de coquilles françaises courantes basée sur la fréquence."""
        self.assertEqual(self.engine.correct("acceuil", context_lang="fr"), "accueil")
        self.assertEqual(self.engine.correct("developpment", context_lang="fr"), "développement")
        self.assertEqual(self.engine.correct("toujurs", context_lang="fr"), "toujours")
        self.assertEqual(self.engine.correct("apres", context_lang="fr"), "après")
        self.assertEqual(self.engine.correct("probleme", context_lang="fr"), "problème")

    def test_english_frequency_corrections(self):
        """Vérifie la correction de coquilles anglaises basées sur la fréquence."""
        self.assertEqual(self.engine.correct("recieve", context_lang="en"), "receive")
        self.assertEqual(self.engine.correct("definately", context_lang="en"), "definitely")
        self.assertEqual(self.engine.correct("seperate", context_lang="en"), "separate")

    def test_code_switching_preservation(self):
        """
        Vérifie qu'un mot anglais inséré au milieu d'une phrase française est préservé,
        et qu'une faute sur un mot anglais est corrigée selon son orthographe d'origine.
        """
        # Mots anglais valides insérés dans un contexte FR -> AUCUNE modification
        self.assertIsNone(self.engine.correct("commit", context_lang="fr"))
        self.assertIsNone(self.engine.correct("push", context_lang="fr"))
        self.assertIsNone(self.engine.correct("framework", context_lang="fr"))
        self.assertIsNone(self.engine.correct("pipeline", context_lang="fr"))

        # Coquille sur un terme technique en contexte FR -> corrigé vers le bon mot anglais
        self.assertEqual(self.engine.correct("comit", context_lang="fr"), "commit")
        self.assertEqual(self.engine.correct("framwork", context_lang="fr"), "framework")

    def test_casing_preservation(self):
        """
        Conserve impérativement la casse d'origine :
        - tout en minuscules -> minuscule
        - première lettre majuscule -> majuscule initiale
        - tout en majuscules -> tout en majuscules
        """
        # Minuscules
        self.assertEqual(self.engine.correct("acceuil", context_lang="fr"), "accueil")
        # Majuscule initiale
        self.assertEqual(self.engine.correct("Acceuil", context_lang="fr"), "Accueil")
        self.assertEqual(self.engine.correct("Developpment", context_lang="fr"), "Développement")
        # Tout en majuscules
        self.assertEqual(self.engine.correct("ACCEUIL", context_lang="fr"), "ACCUEIL")
        self.assertEqual(self.engine.correct("DEVELOPPMENT", context_lang="fr"), "DÉVELOPPEMENT")

    def test_french_elisions(self):
        """Les élisions saisies sans apostrophe sont restaurées."""
        self.assertEqual(self.engine.correct("quil", context_lang="fr"), "qu'il")
        self.assertEqual(self.engine.correct("Quil", context_lang="fr"), "Qu'il")
        self.assertEqual(self.engine.correct("QUIL", context_lang="fr"), "QU'IL")
        self.assertEqual(self.engine.correct("cest", context_lang="fr"), "c'est")
        self.assertEqual(self.engine.correct("jai", context_lang="fr"), "j'ai")
        self.assertEqual(self.engine.correct("daccord", context_lang="fr"), "d'accord")

    def test_strict_filtering(self):
        """
        Ignorer impérativement :
        - chiffres, versions, dates
        - adresses e-mail
        - URLs et chemins
        - variables de code (camelCase, snake_case)
        - drapeaux CLI
        """
        # Chiffres et dates
        self.assertIsNone(self.engine.correct("123", context_lang="fr"))
        self.assertIsNone(self.engine.correct("3.14", context_lang="fr"))
        self.assertIsNone(self.engine.correct("2026-10-13", context_lang="fr"))
        self.assertIsNone(self.engine.correct("v1.2", context_lang="fr"))

        # E-mails
        self.assertIsNone(self.engine.correct("contact@domaine.fr", context_lang="fr"))

        # URLs et chemins
        self.assertIsNone(self.engine.correct("https://google.com", context_lang="fr"))
        self.assertIsNone(self.engine.correct("www.site.fr", context_lang="fr"))
        self.assertIsNone(self.engine.correct("/usr/local/bin", context_lang="fr"))

        # Variables de code
        self.assertIsNone(self.engine.correct("myVariable", context_lang="fr"))
        self.assertIsNone(self.engine.correct("get_user_id", context_lang="fr"))
        self.assertIsNone(self.engine.correct("__init__", context_lang="fr"))

        # Drapeaux CLI
        self.assertIsNone(self.engine.correct("--config", context_lang="fr"))
        self.assertIsNone(self.engine.correct("-rf", context_lang="fr"))

    def test_custom_user_corrections(self):
        """Vérifie la prise en compte du dictionnaire personnalisé (custom_corrections)."""
        self.assertEqual(self.engine.correct("cdl", context_lang="fr"), "Cordialement,")
        self.assertEqual(self.engine.correct("bjr", context_lang="fr"), "Bonjour,")
        self.assertEqual(self.engine.correct("asap", context_lang="fr"), "dès que possible")

    def test_latency_performance_benchmark(self):
        """
        Exigence absolue : latence < 5 ms par mot.
        Exécute 1000 requêtes réelles et mesure les temps moyen, p95 et maximal.
        """
        benchmark_words = [
            ("acceuil", "fr"),
            ("developpment", "fr"),
            ("toujurs", "fr"),
            ("commit", "fr"),
            ("comit", "fr"),
            ("recieve", "en"),
            ("definately", "en"),
            ("framework", "fr"),
            ("bonjour", "fr"),
            ("today", "en"),
        ]

        # Warmup
        for w, lang in benchmark_words:
            self.engine.correct(w, context_lang=lang)

        times_ms = []
        for _ in range(100):
            for w, lang in benchmark_words:
                t0 = time.perf_counter()
                self.engine.correct(w, context_lang=lang)
                t1 = time.perf_counter()
                times_ms.append((t1 - t0) * 1000.0)

        times_ms.sort()
        avg_latency = sum(times_ms) / len(times_ms)
        p95_latency = times_ms[int(len(times_ms) * 0.95)]
        max_latency = max(times_ms)

        print("\n" + "=" * 60)
        print("  RÉSULTATS DU BENCHMARK SYMSPELL (< 5 ms par mot)")
        print("=" * 60)
        print(f"  Nombre total de requêtes mesurées : {len(times_ms)}")
        print(f"  Latence MOYENNE                   : {avg_latency:.4f} ms")
        print(f"  Latence 95e percentile (P95)      : {p95_latency:.4f} ms")
        print(f"  Pire latence mesurée (MAX)        : {max_latency:.4f} ms")
        print("=" * 60)

        self.assertLess(avg_latency, 1.0, "La latence moyenne doit être inférieure à 1 ms")
        self.assertLess(max_latency, 5.0, "La pire latence doit être strictement inférieure à 5 ms")


if __name__ == "__main__":
    unittest.main()
