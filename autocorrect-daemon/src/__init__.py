"""AutoCorrect Daemon - Correcteur d'orthographe et de frappe en temps réel pour Linux."""
from .config import DaemonConfig
from .daemon import AutoCorrectDaemon

__all__ = ["DaemonConfig", "AutoCorrectDaemon"]
