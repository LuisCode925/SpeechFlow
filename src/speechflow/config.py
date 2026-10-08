"""Configuración de usuario de push_to_talk: búsqueda, lectura y validación de un archivo TOML."""
import json
import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from speechflow.transcriber import DEFAULT_LANGUAGE, DEFAULT_MODEL

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
    watch_interval: float = 3.0
    notifications: bool = True
    idle_timeout: float = 0.0  # [model] idle_timeout, en segundos; 0 = desactivado


class ConfigError(Exception):
    """Archivo ilegible o inválido; el mensaje dice qué clave y por qué."""


# sección -> clave -> (tipos admitidos, campo de Config)
_SCHEMA: dict[str, dict[str, tuple[tuple[type, ...], str]]] = {
    "model": {
        "name": ((str,), "model"),
        "language": ((str,), "language"),
        "idle_timeout": ((int, float), "idle_timeout"),
    },
    "keys": {"record": ((str,), "key"), "switch": ((str,), "switch_key")},
    "audio": {"device": ((int, str), "device"), "watch_interval": ((int, float), "watch_interval")},
    "recording": {"min_seconds": ((int, float), "min_seconds"), "max_seconds": ((int, float), "max_seconds")},
    "notifications": {"enabled": ((bool,), "notifications")},
}


def _xdg_dir(variable: str, default: str) -> Path:
    """`$variable/speechflow` si es una ruta absoluta; si no, `~/default/speechflow`. RuntimeError sin HOME."""
    value = os.environ.get(variable, "")
    if value and Path(value).is_absolute():
        return Path(value) / "speechflow"
    return Path(default).expanduser() / "speechflow"


def config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", "~/.config")


def state_dir() -> Path:
    return _xdg_dir("XDG_STATE_HOME", "~/.local/state")


def user_config_path() -> Path:
    return config_dir() / "config.toml"


def emergency_path() -> Path:
    return config_dir() / "config.emergency.toml"


def state_path() -> Path:
    return state_dir() / "state.toml"


def find_config(explicit: Path | None) -> Path | None:
    """Devuelve --config o el archivo de usuario si existen, o None si no hay ninguno."""
    if explicit is not None:
        return explicit if explicit.is_file() else None
    try:
        path = user_config_path()
    except RuntimeError:  # sin HOME
        return None
    return path if path.is_file() else None


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
            values[field] = float(value) if field in ("min_seconds", "max_seconds", "watch_interval", "idle_timeout") else value

    config = Config(**values)
    if config.min_seconds <= 0:
        raise ConfigError(f"recording.min_seconds debe ser mayor que 0, no {config.min_seconds}")
    if config.max_seconds <= config.min_seconds:
        raise ConfigError(
            f"recording.max_seconds ({config.max_seconds}) debe ser mayor que min_seconds ({config.min_seconds})"
        )
    if config.watch_interval < 1.0:
        raise ConfigError(f"audio.watch_interval debe ser al menos 1.0, no {config.watch_interval}")
    if config.idle_timeout != 0 and config.idle_timeout < 30.0:
        raise ConfigError(f"model.idle_timeout debe ser 0 o al menos 30.0, no {config.idle_timeout}")
    return config


def _emergency_template() -> str:
    d = Config()
    return (
        "# config.emergency.toml — plantilla con los valores por defecto.\n"
        "# El script no la lee: cópiala o renómbrala a config.toml para usarla.\n"
        "[model]\n"
        f"name = {json.dumps(d.model)}\n"
        f"language = {json.dumps(d.language)}\n"
        f"idle_timeout = {d.idle_timeout}  # segundos sin dictar antes de liberar el modelo; 0 desactiva; mínimo 30.0\n"
        "\n"
        "[keys]\n"
        f"record = {json.dumps(d.key)}\n"
        f"switch = {json.dumps(d.switch_key)}\n"
        "\n"
        "[audio]\n"
        '# device = "Realtek"  # índice (entero) o parte del nombre; sin definir se usa la entrada por defecto\n'
        f"watch_interval = {d.watch_interval}  # segundos entre comprobaciones del micrófono; mínimo 1.0\n"
        "\n"
        "[recording]\n"
        f"min_seconds = {d.min_seconds}\n"
        f"max_seconds = {d.max_seconds}\n"
        "\n"
        "[notifications]\n"
        f"enabled = {str(d.notifications).lower()}\n"
    )


def write_emergency() -> Path:
    """Crea la plantilla con los defectos en emergency_path() (y su carpeta); si ya existe no la toca. Devuelve la ruta."""
    path = emergency_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as f:
            f.write(_emergency_template())
    except FileExistsError:
        pass
    return path


def load_state_device() -> str | None:
    """Nombre del dispositivo guardado, o None si no hay archivo de estado o es ilegible."""
    try:
        path = state_path()
        with path.open("rb") as f:
            device = tomllib.load(f).get("device")
    except (FileNotFoundError, RuntimeError):  # sin archivo o sin HOME
        return None
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.warning("Archivo de estado ilegible en %s: %s. Se ignora.", path, e)
        return None
    if device is not None and not isinstance(device, str):
        logger.warning("Archivo de estado inválido en %s: device debe ser texto. Se ignora.", path)
        return None
    return device


def save_state_device(name: str) -> None:
    """Guarda el nombre del dispositivo en state_path(), creando la carpeta (archivo temporal + os.replace)."""
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(f"device = {json.dumps(name)}\n", encoding="utf-8")
    os.replace(tmp, path)
