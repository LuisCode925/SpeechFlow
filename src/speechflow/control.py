"""Canal de control por socket Unix: servidor de una línea JSON por conexión y cliente para `speechflow ctl`."""
import json
import logging
import os
import socket
import threading
from collections.abc import Callable
from pathlib import Path

from speechflow.log import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

MAX_REQUEST_BYTES = 4096
READ_TIMEOUT = 2.0
_ACCEPT_POLL = 0.2


class ControlUnavailable(Exception):
    """No hay proceso escuchando: el socket no existe o rechaza la conexión."""


def socket_path() -> Path:
    """`$XDG_RUNTIME_DIR/speechflow/control.sock`. RuntimeError sin XDG_RUNTIME_DIR (sin alternativa en /tmp)."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise RuntimeError("XDG_RUNTIME_DIR no está definida; el canal de control necesita un directorio privado")
    return Path(runtime) / "speechflow" / "control.sock"


def _encode(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n"


def _read_line(conn: socket.socket, limit: int) -> bytes:
    """Lee hasta el primer salto de línea. ValueError si supera `limit` bytes o la conexión se cierra sin línea."""
    data = b""
    while b"\n" not in data:
        if len(data) > limit:
            raise ValueError(f"más de {limit} bytes")
        chunk = conn.recv(limit + 1 - len(data))
        if not chunk:
            if not data:
                raise ValueError("línea vacía")
            break
        data += chunk
    line = data.split(b"\n", 1)[0]
    if len(line) > limit:
        raise ValueError(f"más de {limit} bytes")
    return line


class ControlServer:
    """Atiende una conexión cada vez en un hilo daemon: lee una línea JSON, llama a `handler` y responde."""

    def __init__(self, handler: Callable[[dict], dict], path: Path) -> None:
        self._handler = handler
        self._path = path
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        """Crea el directorio (0700) y el socket (0600) y empieza a atender. OSError si no puede crearse."""
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self._path.parent, 0o700)
        if self._path.exists() or self._path.is_symlink():
            if _is_alive(self._path):
                raise OSError(f"ya hay otra instancia escuchando en {self._path}")
            self._path.unlink()
            logger.debug("Socket huérfano eliminado: %s", self._path)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(str(self._path))
            os.chmod(self._path, 0o600)
            sock.listen(8)
            sock.settimeout(_ACCEPT_POLL)
        except OSError:
            sock.close()
            raise
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(target=self._serve, name="control-server", daemon=True)
        self._thread.start()

    def close(self) -> None:
        """Deja de atender, cierra el socket y borra el archivo. Idempotente."""
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=READ_TIMEOUT + 1)
        sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()
            try:
                self._path.unlink()
            except FileNotFoundError:
                pass

    def _serve(self) -> None:
        sock = self._sock
        while not self._stop.is_set():
            try:
                conn, _ = sock.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with conn:
                try:
                    self._handle_connection(conn)
                except Exception:
                    logger.debug("Error atendiendo una conexión de control", exc_info=True)

    def _handle_connection(self, conn: socket.socket) -> None:
        conn.settimeout(READ_TIMEOUT)
        try:
            line = _read_line(conn, MAX_REQUEST_BYTES)
            request = json.loads(line.decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("debe ser un objeto JSON")
        except (ValueError, TimeoutError) as error:
            reason = "tiempo de espera agotado" if isinstance(error, TimeoutError) else str(error)
            response = {"ok": False, "error": f"petición inválida: {reason}"}
        else:
            logger.debug("Petición de control: %r", request)
            try:
                response = self._handler(request)
            except Exception:
                logger.exception("Error en el manejador de control")
                response = {"ok": False, "error": "error interno"}
        try:
            conn.sendall(_encode(response))
        except OSError:
            logger.debug("El cliente de control cerró antes de la respuesta")


def _is_alive(path: Path) -> bool:
    """True si alguien acepta conexiones en el socket."""
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    probe.settimeout(1.0)
    try:
        probe.connect(str(path))
    except (ConnectionRefusedError, FileNotFoundError):
        return False
    except OSError:
        return True
    finally:
        probe.close()
    return True


def send_request(request: dict, timeout: float = 10.0) -> dict:
    """Envía una petición y devuelve la respuesta. ControlUnavailable si no hay socket o rechaza la conexión."""
    try:
        path = socket_path()
    except RuntimeError as error:
        raise ControlUnavailable(str(error)) from error
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        try:
            sock.connect(str(path))
        except (FileNotFoundError, ConnectionRefusedError) as error:
            raise ControlUnavailable(f"no hay socket en {path}") from error
        sock.sendall(_encode(request))
        line = _read_line(sock, 1 << 20)
        return json.loads(line.decode("utf-8"))
    finally:
        sock.close()
