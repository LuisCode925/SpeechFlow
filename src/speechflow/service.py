"""Servicio systemd de usuario: genera la unidad de speechflow y la instala o desinstala."""
from pathlib import Path

from speechflow.config import config_dir

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
