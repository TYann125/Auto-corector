from typing import Dict, Optional, Set

class ReversionHandler:
    def __init__(self):
        # Stocke le dernier remplacement effectué : { original: replacement }
        self.last_correction: Optional[Dict[str, str]] = None
        # Cache temporaire des mots que l'utilisateur a refusé de corriger (annulation par backspace)
        self.ignored_words: Set[str] = set()

    def record_correction(self, original: str, replacement: str):
        """Enregistre la dernière correction pour permettre une annulation."""
        self.last_correction = {
            "original": original,
            "replacement": replacement
        }

    def handle_backspace(self) -> Optional[str]:
        """
        Appelé lorsqu'un Backspace est détecté. 
        Si c'est juste après une correction, retourne le mot original pour restauration.
        """
        if self.last_correction:
            original = self.last_correction["original"]
            replacement = self.last_correction["replacement"]
            
            # On ajoute le mot original à la blacklist de session pour éviter de le recorriger immédiatement
            self.ignored_words.add(original.lower())
            
            # Reset de la dernière correction pour éviter des boucles d'annulation
            self.last_correction = None
            
            return original
        return None

    def is_ignored(self, word: str) -> bool:
        """Vérifie si un mot est dans la blacklist temporaire de session."""
        return word.lower() in self.ignored_words

    def clear_last_correction(self):
        """Efface l'historique de correction (ex: si l'utilisateur continue de taper d'autres caractères)."""
        self.last_correction = None

    def clear_session_cache(self):
        """Nettoie la blacklist (peut être appelé périodiquement ou au changement de contexte)."""
        self.ignored_words.clear()
