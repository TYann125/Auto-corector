"""
Gestionnaire de configuration pour le daemon AutoCorrect.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List


@dataclass
class DaemonConfig:
    layout: str = "azerty"
    default_language: str = "fr"
    key_delay_ms: float = 5.0
    enable_languagetool: bool = False
    languagetool_endpoint: str = "http://127.0.0.1:8081/v2/check"
    virtual_device_name: str = "AutoCorrect Virtual Keyboard"
    log_level: str = "INFO"
    custom_corrections: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str = "config.json") -> "DaemonConfig":
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
            except Exception as e:
                print(f"[Avertissement] Impossible de charger {path} : {e}, utilisation des valeurs par défaut.")
        return cls()

    def save(self, path: str = "config.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=4, ensure_ascii=False)
