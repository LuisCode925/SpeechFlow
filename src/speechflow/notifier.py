"""Notificaciones de escritorio con notify-send."""
import subprocess


def notify(title: str, body: str = "") -> None:
    """Envía una notificación de escritorio; si notify-send no está instalado, no hace nada."""
    try:
        subprocess.run(["notify-send", title, body], check=False)
    except FileNotFoundError:
        pass
