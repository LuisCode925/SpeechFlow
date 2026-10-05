"""Configuración de usuario de push_to_talk: búsqueda, lectura y validación de un archivo TOML."""
import tomllib
from dataclasses import dataclass
from pathlib import Path

from speechflow.transcriber import DEFAULT_LANGUAGE, DEFAULT_MODEL

CONFIG_FILENAME = "speechflow.toml"
USER_CONFIG_PATH = Path("~/.config/speechflow/config.toml")  # se expande con expanduser()
EMERGENCY_FILENAME = "speechflow.emergency.toml"
STATE_FILENAME = ".speechflow-state.toml"

REPO_ROOT = Path(__file__).resolve().parents[2]


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
