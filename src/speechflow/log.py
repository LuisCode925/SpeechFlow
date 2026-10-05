"""Configuración del log de consola: INFO a stdout, WARNING y ERROR a stderr."""
import logging
import sys
import time

LOGGER_NAME = "speechflow"
FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler que resuelve el flujo al emitir y vacía el búfer tras cada registro."""

    def __init__(self, stream_name: str) -> None:
        super().__init__(getattr(sys, stream_name))
        self._stream_name = stream_name

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = getattr(sys, self._stream_name)
        super().emit(record)
        self.flush()


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
