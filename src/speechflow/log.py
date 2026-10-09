"""Configuración del log de consola: INFO a stdout, WARNING y ERROR a stderr."""
import logging
import os
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from logging.handlers import RotatingFileHandler

from speechflow import __version__
from speechflow.config import log_path, state_dir

LOGGER_NAME = "speechflow"
FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 1_048_576
LOG_BACKUP_COUNT = 3

BANNER_ART = r"""
________                       ______ _______________
__  ___/__________________________  /____  ____/__  /________      __
_____ \___  __ \  _ \  _ \  ___/_  __ \_  /_   __  /_  __ \_ | /| / /
____/ /__  /_/ /  __/  __/ /__ _  / / /  __/   _  / / /_/ /_ |/ |/ /
/____/ _  .___/\___/\___/\___/ /_/ /_//_/      /_/  \____/____/|__/
       /_/
"""


class _FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler que resuelve el flujo al emitir y vacía el búfer tras cada registro."""

    def __init__(self, stream_name: str) -> None:
        super().__init__(getattr(sys, stream_name))
        self._stream_name = stream_name

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = getattr(sys, self._stream_name)
        super().emit(record)
        self.flush()


class _PrivateRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler que crea cada archivo (también tras rotar) con permisos 0600."""

    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        return os.fdopen(fd, self.mode, encoding=self.encoding, errors=self.errors)


def log_banner() -> None:
    """Imprime el arte ASCII, el nombre y las versiones por stdout, sin formato de log."""
    try:
        engine = f"faster-whisper {version('faster-whisper')}"
    except PackageNotFoundError:
        engine = "faster-whisper"
    print(BANNER_ART.strip("\n"), flush=True)
    print(f"SpeechFlow {__version__}", flush=True)
    print(f"Powered by {engine}", flush=True)
    print(flush=True)


def setup_logging() -> logging.Logger:
    """Configura y devuelve el logger `speechflow`; llamarla otra vez no duplica manejadores."""
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(FORMAT, DATE_FORMAT)
    formatter.converter = time.localtime

    out = _FlushingStreamHandler("stdout")
    out.setLevel(logging.INFO)
    out.addFilter(lambda record: record.levelno < logging.WARNING)
    out.setFormatter(formatter)

    err = _FlushingStreamHandler("stderr")
    err.setLevel(logging.WARNING)
    err.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    logger.addHandler(out)
    logger.addHandler(err)
    logger.propagate = False
    _add_file_handler(logger, formatter)
    return logger


def _add_file_handler(logger: logging.Logger, formatter: logging.Formatter) -> None:
    """Añade el log rotativo en archivo; si no se puede abrir, avisa y sigue solo con consola."""
    path = None
    try:
        path = log_path()
        state_dir().mkdir(parents=True, exist_ok=True)
        handler = _PrivateRotatingFileHandler(
            path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
    except (OSError, RuntimeError) as error:
        logger.warning(
            "No se puede escribir el log en %s: %s. Solo habrá log por consola.",
            path if path is not None else "(ruta desconocida)",
            error,
        )
        return
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
