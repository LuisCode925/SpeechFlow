"""Inserción de texto en la ventana con foco (X11) mediante xdotool."""
import subprocess


def insert_text(text: str) -> None:
    """Escribe `text` en la ventana con foco; con texto vacío no hace nada."""
    if not text:
        return
    subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=True)
