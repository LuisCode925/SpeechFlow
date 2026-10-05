"""Configuración de usuario de push_to_talk: búsqueda, lectura y validación de un archivo TOML."""
import json
import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from speechflow.transcriber import DEFAULT_LANGUAGE, DEFAULT_MODEL

CONFIG_FILENAME = "speechflow.toml"
USER_CONFIG_PATH = Path("~/.config/speechflow/config.toml")  # se expande con expanduser()
EMERGENCY_FILENAME = "speechflow.emergency.toml"
STATE_FILENAME = ".speechflow-state.toml"

REPO_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger("speechflow")


@dataclass(frozen=True)
class Config:
    model: str = DEFAULT_MODEL
    language: str = DEFAULT_LANGUAGE
    key: str = "ctrl_r"
    switch_key: str = "f8"
    device: int | str | None = None
    min_seconds: float = 0.5
    max_seconds: float = 60.0
    notifications: bool = True


class ConfigError(Exception):
    """Archivo ilegible o inválido; el mensaje dice qué clave y por qué."""


# sección -> clave -> (tipos admitidos, campo de Config)
_SCHEMA: dict[str, dict[str, tuple[tuple[type, ...], str]]] = {
    "model": {"name": ((str,), "model"), "language": ((str,), "language")},
    "keys": {"record": ((str,), "key"), "switch": ((str,), "switch_key")},
    "audio": {"device": ((int, str), "device")},
    "recording": {"min_seconds": ((int, float), "min_seconds"), "max_seconds": ((int, float), "max_seconds")},
    "notifications": {"enabled": ((bool,), "notifications")},
}


def find_config(explicit: Path | None) -> Path | None:
    """Devuelve el primer archivo que exista (--config, raíz del repo, XDG), o None si no hay ninguno."""
    if explicit is not None:
        return explicit if explicit.is_file() else None
    candidates = [REPO_ROOT / CONFIG_FILENAME]
    try:
        candidates.append(USER_CONFIG_PATH.expanduser())
    except RuntimeError:  # sin HOME
        pass
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path) -> Config:
    """Lee y valida el TOML de `path`; lo omitido toma el defecto. Lanza ConfigError."""
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except OSError as e:
        raise ConfigError(f"no se puede leer: {e.strerror or e}") from e
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"TOML mal formado: {e}") from e

    values: dict[str, object] = {}
    for section, content in data.items():
        if section not in _SCHEMA:
            raise ConfigError(f"sección desconocida [{section}]")
        if not isinstance(content, dict):
            raise ConfigError(f"[{section}] debe ser una tabla")
        for key, value in content.items():
            if key not in _SCHEMA[section]:
                raise ConfigError(f"clave desconocida {section}.{key}")
            types, field = _SCHEMA[section][key]
            # bool es subclase de int: solo se admite donde se pide bool
            if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
                names = " o ".join(t.__name__ for t in types)
                raise ConfigError(f"{section}.{key} debe ser {names}, no {type(value).__name__}")
            values[field] = float(value) if field in ("min_seconds", "max_seconds") else value

    config = Config(**values)
    if config.min_seconds <= 0:
        raise ConfigError(f"recording.min_seconds debe ser mayor que 0, no {config.min_seconds}")
    if config.max_seconds <= config.min_seconds:
        raise ConfigError(
            f"recording.max_seconds ({config.max_seconds}) debe ser mayor que min_seconds ({config.min_seconds})"
        )
    return config


def _emergency_template() -> str:
    d = Config()
    return (
        "# speechflow.emergency.toml — plantilla con los valores por defecto.\n"
        "# El script no la lee: cópiala o renómbrala a speechflow.toml para usarla.\n"
        "[model]\n"
        f"name = {json.dumps(d.model)}\n"
        f"language = {json.dumps(d.language)}\n"
        "\n"
        "[keys]\n"
        f"record = {json.dumps(d.key)}\n"
        f"switch = {json.dumps(d.switch_key)}\n"
        "\n"
        "[audio]\n"
        '# device = "Realtek"  # índice (entero) o parte del nombre; sin definir se usa la entrada por defecto\n'
        "\n"
        "[recording]\n"
        f"min_seconds = {d.min_seconds}\n"
        f"max_seconds = {d.max_seconds}\n"
        "\n"
        "[notifications]\n"
        f"enabled = {str(d.notifications).lower()}\n"
    )


def write_emergency(directory: Path) -> Path:
    """Crea EMERGENCY_FILENAME con los defectos en `directory`; si ya existe no lo toca. Devuelve la ruta."""
    path = directory / EMERGENCY_FILENAME
    try:
        with path.open("x", encoding="utf-8") as f:
            f.write(_emergency_template())
    except FileExistsError:
        pass
    return path


def load_state_device() -> str | None:
    """Nombre del dispositivo guardado, o None si no hay archivo de estado o es ilegible."""
    path = REPO_ROOT / STATE_FILENAME
    try:
        with path.open("rb") as f:
            device = tomllib.load(f).get("device")
    except FileNotFoundError:
        return None
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.warning("Archivo de estado ilegible en %s: %s. Se ignora.", path, e)
        return None
    if device is not None and not isinstance(device, str):
        logger.warning("Archivo de estado inválido en %s: device debe ser texto. Se ignora.", path)
        return None
    return device


def save_state_device(name: str) -> None:
    """Guarda el nombre del dispositivo en STATE_FILENAME (archivo temporal + os.replace)."""
    path = REPO_ROOT / STATE_FILENAME
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(f"device = {json.dumps(name)}\n", encoding="utf-8")
    os.replace(tmp, path)
