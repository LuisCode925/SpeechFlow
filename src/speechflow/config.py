"""Configuración de usuario de push_to_talk: búsqueda, lectura y validación de un archivo TOML."""
import json
import logging
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from speechflow.transcriber import DEFAULT_LANGUAGE

logger = logging.getLogger("speechflow")


@dataclass(frozen=True)
class Config:
    model: str | None = None  # [model] name; None = sin fijar (medium en GPU, small en CPU)
    language: str = DEFAULT_LANGUAGE
    key: str = "ctrl_r"
    switch_key: str = "f8"
    device: int | str | None = None
    min_seconds: float = 0.5
    max_seconds: float = 60.0
    watch_interval: float = 3.0
    notifications: bool = True
    idle_timeout: float = 0.0  # [model] idle_timeout, en segundos; 0 = desactivado
    vad: bool = True  # [model] vad; filtra silencios con Silero antes de transcribir
    language_key: str = "f7"  # [keys] language; alterna es <-> en
    auto_key: str = "f6"  # [keys] auto; activa o desactiva la detección automática de idioma
    mode: str = "hold"  # [recording] mode; "hold" (mantener) o "toggle" (pulsar y pulsar)
    punctuation_commands: bool = True  # [text] punctuation_commands; sustituye "punto", "coma"... por su signo
    device_compute: str = "auto"  # [model] device; "auto", "cpu" o "cuda"
    cpu_threads: int = 0  # [model] cpu_threads; 0 = defecto de faster-whisper


RECORDING_MODES = ("hold", "toggle")
COMPUTE_DEVICES = ("auto", "cpu", "cuda")


class ConfigError(Exception):
    """Archivo ilegible o inválido; el mensaje dice qué clave y por qué."""


# sección -> clave -> (tipos admitidos, campo de Config)
_SCHEMA: dict[str, dict[str, tuple[tuple[type, ...], str]]] = {
    "model": {
        "name": ((str,), "model"),
        "language": ((str,), "language"),
        "idle_timeout": ((int, float), "idle_timeout"),
        "vad": ((bool,), "vad"),
        "device": ((str,), "device_compute"),
        "cpu_threads": ((int,), "cpu_threads"),
    },
    "keys": {
        "record": ((str,), "key"),
        "switch": ((str,), "switch_key"),
        "language": ((str,), "language_key"),
        "auto": ((str,), "auto_key"),
    },
    "audio": {"device": ((int, str), "device"), "watch_interval": ((int, float), "watch_interval")},
    "recording": {
        "min_seconds": ((int, float), "min_seconds"),
        "max_seconds": ((int, float), "max_seconds"),
        "mode": ((str,), "mode"),
    },
    "notifications": {"enabled": ((bool,), "notifications")},
    "text": {"punctuation_commands": ((bool,), "punctuation_commands")},
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


def log_path() -> Path:
    return state_dir() / "speechflow.log"


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
    if config.model is not None and not config.model.strip():
        raise ConfigError("model.name no puede estar vacío")
    if config.min_seconds <= 0:
        raise ConfigError(f"recording.min_seconds debe ser mayor que 0, no {config.min_seconds}")
    if config.max_seconds <= config.min_seconds:
        raise ConfigError(
            f"recording.max_seconds ({config.max_seconds}) debe ser mayor que min_seconds ({config.min_seconds})"
        )
    if config.mode not in RECORDING_MODES:
        raise ConfigError(f'recording.mode debe ser "hold" o "toggle", no {config.mode!r}')
    if config.device_compute not in COMPUTE_DEVICES:
        raise ConfigError(f'model.device debe ser "auto", "cpu" o "cuda", no {config.device_compute!r}')
    if config.cpu_threads < 0:
        raise ConfigError(f"model.cpu_threads debe ser 0 o mayor, no {config.cpu_threads}")
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
        '# name = "medium"  # sin fijar: medium en GPU, small en CPU\n'
        f"language = {json.dumps(d.language)}\n"
        f"idle_timeout = {d.idle_timeout}  # segundos sin dictar antes de liberar el modelo; 0 desactiva; mínimo 30.0\n"
        f"vad = {str(d.vad).lower()}  # filtra silencios y ruido sin voz antes de transcribir; false desactiva\n"
        f"device = {json.dumps(d.device_compute)}  # \"auto\": GPU si hay y funciona, si no CPU; \"cpu\": solo CPU; \"cuda\": solo GPU (falla si no hay)\n"
        f"cpu_threads = {d.cpu_threads}  # hilos de CPU para Whisper; 0 usa el defecto de faster-whisper\n"
        "\n"
        "[keys]\n"
        f"record = {json.dumps(d.key)}\n"
        f"switch = {json.dumps(d.switch_key)}\n"
        f"language = {json.dumps(d.language_key)}  # alterna es <-> en en caliente\n"
        f"auto = {json.dumps(d.auto_key)}  # activa o desactiva la detección automática de idioma\n"
        "\n"
        "[audio]\n"
        '# device = "Realtek"  # índice (entero) o parte del nombre; sin definir se usa la entrada por defecto\n'
        f"watch_interval = {d.watch_interval}  # segundos entre comprobaciones del micrófono; mínimo 1.0\n"
        "\n"
        "[recording]\n"
        f"min_seconds = {d.min_seconds}\n"
        f"max_seconds = {d.max_seconds}\n"
        f"mode = {json.dumps(d.mode)}  # \"hold\": graba mientras mantienes la tecla; \"toggle\": una pulsación empieza y otra para\n"
        "\n"
        "[notifications]\n"
        f"enabled = {str(d.notifications).lower()}\n"
        "\n"
        "[text]\n"
        f'punctuation_commands = {str(d.punctuation_commands).lower()}  # sustituye "punto", "coma", "nueva línea"... por su signo; false inserta lo que transcribe Whisper\n'
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


def _load_state_text(key: str, allow_empty: bool) -> str | None:
    """Valor de texto de `key` en state.toml, o None si falta, es inválido o el archivo es ilegible."""
    try:
        path = state_path()
        with path.open("rb") as f:
            value = tomllib.load(f).get(key)
    except (FileNotFoundError, RuntimeError):  # sin archivo o sin HOME
        return None
    except (OSError, tomllib.TOMLDecodeError) as e:
        logger.warning("Archivo de estado ilegible en %s: %s. Se ignora.", path, e)
        return None
    if value is not None and (not isinstance(value, str) or (not allow_empty and not value)):
        logger.warning("Archivo de estado inválido en %s: %s debe ser texto%s. Se ignora.", path, key, "" if allow_empty else " no vacío")
        return None
    return value


def load_state_device() -> str | None:
    """Nombre del dispositivo guardado, o None si no hay archivo de estado o es ilegible."""
    return _load_state_text("device", allow_empty=True)


def load_state_language() -> str | None:
    """Idioma guardado ("es", "en", "auto", ...), o None si falta o es inválido."""
    return _load_state_text("language", allow_empty=False)


def _save_state_key(key: str, value: str) -> None:
    """Cambia `key` en state_path() conservando las demás claves de texto (archivo temporal + os.replace)."""
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current: dict[str, str] = {}
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
        current = {k: v for k in ("device", "language") if isinstance(v := data.get(k), str)}
    except (OSError, tomllib.TOMLDecodeError):  # ausente o ilegible: se escribe solo la clave nueva
        pass
    current[key] = value
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text("".join(f"{k} = {json.dumps(v)}\n" for k, v in current.items()), encoding="utf-8")
    os.replace(tmp, path)


def save_state_device(name: str) -> None:
    """Guarda el nombre del dispositivo en state_path(), conservando `language`."""
    _save_state_key("device", name)


def save_state_language(language: str) -> None:
    """Guarda el idioma en state_path(), conservando `device`."""
    _save_state_key("language", language)
