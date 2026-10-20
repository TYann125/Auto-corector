"""
Tests unitaires et benchmarks pour le moteur linguistique bilingue (Français & Anglais).
"""

import time
import unittest
from src.engine.corrector import TextCorrectionEngine


class TestBilingualEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = TextCorrectionEngine(default_lang="fr", enable_languagetool=False)

    def test_french_typo_corrections(self):
        """Vérifie la correction de coquilles et d'orthographe en français."""
        # 'developpment' -> 'développement'
        self.assertEqual(
            self.engine.process_word("developpment", ["le"]),
            "développement"
        )
        # 'acceuil' -> 'accueil'
        self.assertEqual(
            self.engine.process_word("acceuil", ["notre"]),
            "accueil"
        )
        # 'toujurs' -> 'toujours'
        self.assertEqual(
            self.engine.process_word("toujurs", ["il", "est"]),
            "toujours"
        )
        # 'apres' -> 'après'
        self.assertEqual(
            self.engine.process_word("apres", ["juste"]),
            "après"
        )
        # 'probleme' -> 'problème'
        self.assertEqual(
            self.engine.process_word("probleme", ["un"]),
            "problème"
        )

    def test_english_typo_corrections(self):
        """Vérifie la correction en anglais lorsque le contexte est anglais."""
        context = ["this", "is", "a"]
        # 'recieve' -> 'receive'
        self.assertEqual(
            self.engine.process_word("recieve", context),
            "receive"
        )
        # 'definately' -> 'definitely'
        self.assertEqual(
            self.engine.process_word("definately", context),
            "definitely"
        )
        # 'teh' -> 'the'
        self.assertEqual(
            self.engine.process_word("teh", ["look", "at"]),
            "the"
        )

    def test_code_switching_preservation(self):
        """
        Vérifie qu'un mot anglais inséré dans une phrase en français n'est PAS modifié ni traduit !
        Exemple : 'J'ai push mon commit sur github'
        """
        context = ["j'ai", "fait", "un"]

        # 'commit' est un mot anglais valide -> ne doit PAS être touché
        self.assertIsNone(self.engine.process_word("commit", context))

        # 'push' est valide -> ne doit PAS être touché
        self.assertIsNone(self.engine.process_word("push", context))

        # 'framework' est valide -> ne doit PAS être touché
        self.assertIsNone(self.engine.process_word("framework", context))

        # 'pipeline' est valide -> ne doit PAS être touché
        self.assertIsNone(self.engine.process_word("pipeline", context))

        # En revanche, une faute sur un mot anglais dans un contexte FR ('comit' -> 'commit') doit être corrigée
        self.assertEqual(self.engine.process_word("comit", context), "commit")

    def test_grammar_agreements(self):
        """Vérifie les accords stricts de pluriel et homophones."""
        # Accord pluriel : "les maison" -> "les maisons"
        self.assertEqual(
            self.engine.process_word("maison", ["les"]),
            "maisons"
        )
        # "des erreur" -> "des erreurs"
        self.assertEqual(
            self.engine.process_word("erreur", ["des"]),
            "erreurs"
        )
        # Homophone 'a' vs 'à' après 'grâce'
        self.assertEqual(
            self.engine.process_word("a", ["grâce"]),
            "à"
        )
        # Homophone 'ou' vs 'où' après 'au moment'
        self.assertEqual(
            self.engine.process_word("ou", ["au", "moment"]),
            "où"
        )
        # 'ca' -> 'ça'
        self.assertEqual(
            self.engine.process_word("ca", []),
            "ça"
        )

    def test_casing_preservation(self):
        """Vérifie la conservation de la casse originale (Majuscule, Tout en majuscules)."""
        self.assertEqual(self.engine.process_word("Developpment", ["le"]), "Développement")
        self.assertEqual(self.engine.process_word("DEVELOPPMENT", ["le"]), "DÉVELOPPEMENT")
        self.assertEqual(self.engine.process_word("Acceuil", ["notre"]), "Accueil")

    def test_latency_performance_benchmark(self):
        """
        Exigence fonctionnelle : traitement < 100 ms.
        Vérifie que le temps moyen d'analyse est nettement inférieur à 10 ms.
        """
        words_to_test = [
            ("developpment", ["le"]),
            ("commit", ["j'ai"]),
            ("maison", ["les"]),
            ("bonjour", []),
            ("recieve", ["to"]),
            ("toujurs", ["il"]),
            ("apres", ["juste"]),
            ("framework", ["mon"]),
        ]

        # Warmup
        for w, ctx in words_to_test:
            self.engine.process_word(w, ctx)

        times = []
        for _ in range(100):
            for w, ctx in words_to_test:
                t0 = time.perf_counter()
                self.engine.process_word(w, ctx)
                t1 = time.perf_counter()
                times.append((t1 - t0) * 1000.0)

        avg_latency_ms = sum(times) / len(times)
        max_latency_ms = max(times)

        print(f"\n[BENCHMARK] Latence moyenne : {avg_latency_ms:.3f} ms | Pire latence : {max_latency_ms:.3f} ms")
        self.assertLess(avg_latency_ms, 10.0, "La latence moyenne doit être inférieure à 10 ms")
        self.assertLess(max_latency_ms, 100.0, "La latence maximale doit être strictement inférieure à 100 ms")


if __name__ == "__main__":
    unittest.main()
