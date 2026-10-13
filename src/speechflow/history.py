"""Historial de transcripciones: una línea JSON por dictado en un archivo rotativo con permisos 0600."""
import json
import logging
import threading
from pathlib import Path

from speechflow.log import PrivateRotatingFileHandler

HISTORY_BACKUP_COUNT = 2


class History:
    """Añade entradas JSONL a `path`; rota por tamaño y escribe cada línea completa con un hilo a la vez."""

    def __init__(self, path: Path, max_bytes: int, backup_count: int = HISTORY_BACKUP_COUNT) -> None:
        """Abre el archivo (y crea su carpeta). Lanza OSError si no se puede abrir."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handler = PrivateRotatingFileHandler(
            path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        self._lock = threading.Lock()
        self._closed = False

    def add(self, entry: dict) -> None:
        """Escribe `entry` como una línea JSON. Propaga OSError y TypeError/ValueError si falla; no hace nada tras close()."""
        line = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            if self._closed:
                return
            handler = self._handler
            record = logging.LogRecord("history", logging.INFO, "", 0, line, None, None)
            if handler.shouldRollover(record):  # rota antes de escribir: la línea nunca queda partida
                handler.doRollover()
            stream = handler.stream
            stream.write(line + "\n")
            stream.flush()

    def close(self) -> None:
        """Cierra el archivo tras terminar cualquier escritura en curso."""
        with self._lock:
            if not self._closed:
                self._closed = True
                self._handler.close()
