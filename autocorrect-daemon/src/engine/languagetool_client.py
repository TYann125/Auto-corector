"""
Module d'intégration optionnel avec un serveur local LanguageTool.

Permet de déléguer des vérifications grammaticales complexes à une instance locale
LanguageTool (généralement sur http://localhost:8081/v2/check).
Comporte un coupe-circuit (circuit breaker) et un timeout strict (< 80 ms) pour respecter
l'exigence temps réel sans bloquer la frappe.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any


class LanguageToolClient:
    """Client HTTP ultra-léger et rapide pour serveur LanguageTool local."""

    def __init__(self, endpoint: str = "http://127.0.0.1:8081/v2/check", enabled: bool = True, timeout_s: float = 0.08):
        self.endpoint = endpoint
        self.enabled = enabled
        self.timeout_s = timeout_s
        self._is_server_available: Optional[bool] = None

    def check_availability(self) -> bool:
        """Vérifie si le serveur LanguageTool local est actif."""
        if not self.enabled:
            return False
        try:
            req = urllib.request.Request(
                self.endpoint.replace("/check", "/languages"),
                headers={"User-Agent": "AutoCorrect-Daemon/1.0"},
            )
            with urllib.request.urlopen(req, timeout=0.2) as resp:
                self._is_server_available = resp.status == 200
                return self._is_server_available
        except Exception:
            self._is_server_available = False
            return False

    def check_text(self, text: str, lang: str = "auto") -> List[Dict[str, Any]]:
        """Interroge le serveur LanguageTool local avec timeout strict."""
        if self._is_server_available is False:
            return []

        lt_lang = "fr" if lang == "fr" else ("en-US" if lang == "en" else "auto")
        data = urllib.parse.urlencode({
            "text": text,
            "language": lt_lang,
            "enabledOnly": "false",
        }).encode("utf-8")

        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("matches", [])
        except Exception:
            # En cas de timeout ou serveur absent, on ignore sans bloquer
            return []
