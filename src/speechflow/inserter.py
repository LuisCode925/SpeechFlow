"""Inserción de texto en la ventana con foco (X11): pegado por portapapeles (xclip) o tecleado con xdotool."""
import logging
import re
import subprocess
import time

logger = logging.getLogger("speechflow")

# Clases de ventana (en minúsculas) que pegan con Ctrl+Shift+V
TERMINAL_CLASSES = frozenset({
    "gnome-terminal", "gnome-terminal-server", "konsole", "xterm", "uxterm", "urxvt", "alacritty", "kitty",
    "xfce4-terminal", "terminator", "tilix", "st", "st-256color", "wezterm", "foot", "lxterminal",
    "mate-terminal", "qterminal", "terminology", "guake", "yakuake",
})
PASTE_DELAY = 0.3  # segundos entre el pegado y la restauración del portapapeles
COMMAND_TIMEOUT = 2.0  # segundos máximos por llamada a xclip / xdotool

_XCLIP_READ = ["xclip", "-selection", "clipboard", "-o", "-t", "UTF8_STRING"]
_XCLIP_WRITE = ["xclip", "-selection", "clipboard", "-i", "-t", "UTF8_STRING"]


def insert_text(text: str, method: str = "clipboard", extra_terminals: tuple[str, ...] = ()) -> None:
    """Inserta `text` en la ventana con foco; con texto vacío no hace nada.

    `method="clipboard"` copia y pega (restaurando el portapapeles previo) y, si algo falla, teclea con xdotool.
    """
    if not text:
        return
    if method == "clipboard":
        try:
            _paste(text, extra_terminals)
            return
        except _ClipboardError as e:
            logger.warning("Portapapeles no disponible (%s); se teclea con xdotool type.", e)
    _type(text)


class _ClipboardError(Exception):
    """Falló xclip o xdotool en el modo portapapeles; el texto aún no se ha pegado."""


def _type(text: str) -> None:
    subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=True)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, check=True, timeout=COMMAND_TIMEOUT, **kwargs)
    except subprocess.CalledProcessError as e:
        raise _ClipboardError(f"{cmd[0]} terminó con código {e.returncode}") from e
    except subprocess.TimeoutExpired as e:
        raise _ClipboardError(f"{cmd[0]} no respondió en {COMMAND_TIMEOUT} s") from e
    except OSError as e:
        raise _ClipboardError(f"{cmd[0]}: {e.strerror or e}") from e


def _write_clipboard(text: str) -> None:
    # xclip deja un proceso en segundo plano que mantiene la selección: sin DEVNULL run() esperaría a sus flujos
    _run(_XCLIP_WRITE, input=text.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _read_clipboard() -> str | None:
    """Texto actual de CLIPBOARD, o None si está vacío, no es texto o no se puede leer."""
    try:
        out = _run(_XCLIP_READ, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    except _ClipboardError:
        return None
    return out.decode("utf-8", errors="replace") or None if isinstance(out, bytes) else None


def _focused_classes() -> set[str]:
    """Instancia y clase (WM_CLASS) de la ventana con foco en minúsculas; vacío si no se pueden averiguar."""
    try:
        window = _run(["xdotool", "getwindowfocus"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
        out = _run(["xprop", "-id", window.decode().strip(), "WM_CLASS"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    except (_ClipboardError, AttributeError, UnicodeDecodeError):
        return set()
    return {name.lower() for name in re.findall(r'"([^"]+)"', out.decode("utf-8", errors="replace"))} if isinstance(out, bytes) else set()


def _paste(text: str, extra_terminals: tuple[str, ...]) -> None:
    previous = _read_clipboard()
    try:
        _write_clipboard(text)
        terminals = TERMINAL_CLASSES | {c.lower() for c in extra_terminals}
        shortcut = "ctrl+shift+v" if _focused_classes() & terminals else "ctrl+v"
        _run(["xdotool", "key", "--clearmodifiers", shortcut])
    except _ClipboardError:
        _restore(previous)
        raise
    time.sleep(PASTE_DELAY)
    _restore(previous)


def _restore(previous: str | None) -> None:
    """Devuelve a CLIPBOARD el texto previo; un fallo aquí no debe perder ni duplicar el dictado."""
    if previous is None:
        return
    try:
        _write_clipboard(previous)
    except _ClipboardError as e:
        logger.warning("No se pudo restaurar el portapapeles (%s).", e)
