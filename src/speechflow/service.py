"""Servicio systemd de usuario: genera la unidad de speechflow y la instala o desinstala."""
import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from speechflow.config import config_dir
from speechflow.log import DATE_FORMAT, FORMAT, LOGGER_NAME, _FlushingStreamHandler, apply_log_levels

logger = logging.getLogger(LOGGER_NAME)

UNIT_NAME = "speechflow.service"

_FORBIDDEN = (" ", "\t", "\n", "\r", "%")

_UNIT_TEMPLATE = """\
[Unit]
Description=SpeechFlow, dictado por voz push-to-talk
PartOf=graphical-session.target
After=graphical-session.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
ExecStart={python} -m speechflow
Environment=LD_LIBRARY_PATH={prefix}/lib
Restart=on-failure
RestartSec=3
TimeoutStopSec=40

[Install]
WantedBy=graphical-session.target
"""


def render_unit(python: str, prefix: str) -> str:
    """Texto de la unidad. ValueError si `python` o `prefix` llevan espacios, saltos de línea o '%'."""
    for name, value in (("python", python), ("prefix", prefix)):
        if any(char in value for char in _FORBIDDEN):
            raise ValueError(f"La ruta de {name} no puede contener espacios, saltos de línea ni '%': {value!r}")
    return _UNIT_TEMPLATE.format(python=python, prefix=prefix)


def unit_path() -> Path:
    """`$XDG_CONFIG_HOME/systemd/user/speechflow.service`. RuntimeError sin HOME."""
    return config_dir().parent / "systemd" / "user" / UNIT_NAME


def _setup_console_logging() -> None:
    """Salida a consola (info a stdout, errores a stderr) sin el log rotativo: es un comando de control."""
    if logger.handlers:
        return
    formatter = logging.Formatter(FORMAT, DATE_FORMAT)
    out = _FlushingStreamHandler("stdout")
    out.addFilter(lambda record: record.levelno < logging.WARNING)
    out.setFormatter(formatter)
    err = _FlushingStreamHandler("stderr")
    err.setFormatter(formatter)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(out)
    logger.addHandler(err)
    logger.propagate = False
    apply_log_levels("info", "info")


def _systemctl(*args: str, capture: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta `systemctl --user <args>` sin shell."""
    return subprocess.run(["systemctl", "--user", *args], capture_output=capture, text=True)


def _run_checked(*args: str) -> bool:
    """Ejecuta systemctl y, si falla, registra su salida de error. True si terminó con código 0."""
    try:
        result = _systemctl(*args)
    except OSError as error:
        logger.error("No se pudo ejecutar systemctl: %s", error)
        return False
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        logger.error("systemctl --user %s falló (código %d)%s", " ".join(args), result.returncode, f": {detail}" if detail else "")
        return False
    return True


def _has_systemctl() -> bool:
    if shutil.which("systemctl") is None:
        logger.error("No se encontró systemctl: este sistema no usa systemd.")
        return False
    return True


def install() -> int:
    """Escribe la unidad con el Python actual y la habilita e inicia. Idempotente; no reinicia un servicio activo."""
    if not _has_systemctl():
        return 1
    try:
        path = unit_path()
        unit = render_unit(sys.executable, sys.prefix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(unit, encoding="utf-8")
    except (RuntimeError, ValueError, OSError) as error:
        logger.error("No se pudo escribir la unidad: %s", error)
        return 1
    logger.info("Unidad escrita en %s", path)
    if not (_run_checked("daemon-reload") and _run_checked("enable", "--now", UNIT_NAME)):
        return 1
    logger.info("Servicio instalado y activado. Si ya estaba en marcha y la unidad cambió, aplícala con: systemctl --user restart speechflow")
    return 0


def uninstall() -> int:
    """Desactiva y detiene el servicio, borra la unidad y recarga systemd."""
    try:
        path = unit_path()
    except RuntimeError as error:
        logger.error("No se pudo localizar la unidad: %s", error)
        return 1
    if not path.exists():
        logger.info("El servicio no está instalado.")
        return 0
    if not _has_systemctl() or not _run_checked("disable", "--now", UNIT_NAME):
        return 1
    try:
        path.unlink()
    except OSError as error:
        logger.error("No se pudo borrar %s: %s", path, error)
        return 1
    if not _run_checked("daemon-reload"):
        return 1
    logger.info("Servicio desinstalado.")
    return 0


def status() -> int:
    """Muestra `systemctl --user status` y devuelve su código de salida."""
    if not _has_systemctl():
        return 1
    try:
        return _systemctl("status", UNIT_NAME, "--no-pager", capture=False).returncode
    except OSError as error:
        logger.error("No se pudo ejecutar systemctl: %s", error)
        return 1


def main(argv: list[str]) -> int:
    """Analiza `install`, `uninstall` o `status` y devuelve el código de salida (2 si el uso es incorrecto)."""
    parser = argparse.ArgumentParser(prog="speechflow service", description="Gestiona speechflow como servicio de systemd --user.")
    sub = parser.add_subparsers(dest="command", metavar="{install,uninstall,status}")
    sub.add_parser("install", help="instala y activa el servicio")
    sub.add_parser("uninstall", help="desactiva y elimina el servicio")
    sub.add_parser("status", help="muestra el estado del servicio")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit:
        return exit.code if isinstance(exit.code, int) else 0
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    _setup_console_logging()
    return {"install": install, "uninstall": uninstall, "status": status}[args.command]()
