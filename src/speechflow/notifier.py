"""Notificaciones de escritorio con notify-send."""
import subprocess

_enabled = True


def set_enabled(enabled: bool) -> None:
    """Activa o desactiva todas las notificaciones; con False, notify() no hace nada."""
    global _enabled
    _enabled = enabled


def notify(title: str, body: str = "") -> None:
    """Envía una notificación de escritorio; si notify-send no está instalado o están desactivadas, no hace nada."""
    if not _enabled:
        return
    try:
        subprocess.run(["notify-send", title, body], check=False)
    except FileNotFoundError:
        pass
