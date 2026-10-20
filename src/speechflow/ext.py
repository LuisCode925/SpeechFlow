"""Extensión de GNOME Shell: instala, desinstala y consulta la copia de `shell_extension/` en el directorio del usuario."""
import argparse
import logging
import os
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

# Autónomo a propósito: config, log y service arrastran faster_whisper al importarse.
logger = logging.getLogger("speechflow")

UUID = "speechflow@local"
FILES = ("metadata.json", "extension.js", "stylesheet.css")


def extension_dir() -> Path:
    """`$XDG_DATA_HOME/gnome-shell/extensions/speechflow@local`. RuntimeError sin HOME."""
    value = os.environ.get("XDG_DATA_HOME", "")
    base = Path(value) if value and Path(value).is_absolute() else Path("~/.local/share").expanduser()
    return base / "gnome-shell" / "extensions" / UUID


def _setup_console_logging() -> None:
    """Mensajes informativos a stdout y errores a stderr, sin el log rotativo."""
    if logger.handlers:
        return
    out = logging.StreamHandler(sys.stdout)
    out.addFilter(lambda record: record.levelno < logging.WARNING)
    err = logging.StreamHandler(sys.stderr)
    err.setLevel(logging.WARNING)
    logger.setLevel(logging.INFO)
    logger.addHandler(out)
    logger.addHandler(err)
    logger.propagate = False


def _package_files() -> dict[str, bytes]:
    source = resources.files("speechflow") / "shell_extension"
    return {name: (source / name).read_bytes() for name in FILES}


def _has_gnome_extensions() -> bool:
    return shutil.which("gnome-extensions") is not None


def install() -> int:
    """Copia los archivos de la extensión sustituyendo la versión anterior. No la activa."""
    try:
        target = extension_dir()
        files = _package_files()
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for name, data in files.items():
            (target / name).write_bytes(data)
    except (RuntimeError, OSError) as error:
        logger.error("No se pudo instalar la extensión: %s", error)
        return 1
    logger.info("Extensión instalada en %s", target)
    logger.info("Siguientes pasos:")
    logger.info("  1. Reinicia GNOME Shell (en X11: Alt+F2, escribe r y pulsa Enter; en Wayland, cierra la sesión y vuelve a entrar).")
    logger.info("  2. Actívala con: gnome-extensions enable %s", UUID)
    return 0


def uninstall() -> int:
    """Desactiva la extensión si existe `gnome-extensions` y borra el directorio instalado."""
    try:
        target = extension_dir()
    except RuntimeError as error:
        logger.error("No se pudo localizar la extensión: %s", error)
        return 1
    if _has_gnome_extensions():
        try:
            subprocess.run(["gnome-extensions", "disable", UUID], capture_output=True, text=True)
        except OSError as error:
            logger.warning("No se pudo ejecutar gnome-extensions disable: %s", error)
    if not target.exists():
        logger.info("La extensión no está instalada.")
        return 0
    try:
        shutil.rmtree(target)
    except OSError as error:
        logger.error("No se pudo borrar %s: %s", target, error)
        return 1
    logger.info("Extensión desinstalada.")
    return 0


def status() -> int:
    """Indica si está instalada, si coincide con la del paquete y el resultado de `gnome-extensions info`."""
    try:
        target = extension_dir()
        files = _package_files()
    except (RuntimeError, OSError) as error:
        logger.error("No se pudo consultar la extensión: %s", error)
        return 1
    if not target.is_dir():
        logger.info("No instalada (se instalaría en %s).", target)
    else:
        same = all((target / name).is_file() and (target / name).read_bytes() == data for name, data in files.items())
        logger.info("Instalada en %s", target)
        logger.info("Coincide con la del paquete." if same else "Difiere de la del paquete; actualízala con: speechflow ext install")
    if _has_gnome_extensions():
        try:
            result = subprocess.run(["gnome-extensions", "info", UUID], capture_output=True, text=True)
        except OSError as error:
            logger.warning("No se pudo ejecutar gnome-extensions info: %s", error)
        else:
            output = (result.stdout or result.stderr or "").strip()
            if output:
                logger.info("%s", output)
    return 0


def main(argv: list[str]) -> int:
    """Analiza `install`, `uninstall` o `status` y devuelve el código de salida (2 si el uso es incorrecto)."""
    parser = argparse.ArgumentParser(prog="speechflow ext", description="Gestiona la extensión de GNOME Shell de speechflow.")
    sub = parser.add_subparsers(dest="command", metavar="{install,uninstall,status}")
    sub.add_parser("install", help="copia la extensión al directorio del usuario")
    sub.add_parser("uninstall", help="desactiva y borra la extensión")
    sub.add_parser("status", help="muestra si está instalada y si coincide con la del paquete")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit:
        return exit.code if isinstance(exit.code, int) else 0
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    _setup_console_logging()
    return {"install": install, "uninstall": uninstall, "status": status}[args.command]()
