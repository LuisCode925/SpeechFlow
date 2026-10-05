"""Configuración del log de consola: INFO a stdout, WARNING y ERROR a stderr."""
import logging
import sys
import time
from importlib.metadata import PackageNotFoundError, version

from speechflow import __version__

LOGGER_NAME = "speechflow"
FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

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
    return logger
