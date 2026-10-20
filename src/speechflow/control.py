"""Canal de control por socket Unix: servidor de una línea JSON por conexión y cliente para `speechflow ctl`."""
import argparse
import json
import logging
import os
import socket
import sys
import threading
from collections.abc import Callable
from pathlib import Path

# Mismo nombre que log.LOGGER_NAME; no se importa `speechflow.log` porque arrastra faster_whisper (`ctl` debe arrancar al instante).
logger = logging.getLogger("speechflow")

MAX_REQUEST_BYTES = 4096
READ_TIMEOUT = 2.0
SEND_TIMEOUT = 1.0         # s máximos para escribir a un suscriptor
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
        self._subscribers: list[socket.socket] = []
        self._subscribers_lock = threading.Lock()

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
            keep = False
            try:
                keep = self._handle_connection(conn)
            except Exception:
                logger.debug("Error atendiendo una conexión de control", exc_info=True)
            finally:
                if not keep:
                    conn.close()

    def _handle_connection(self, conn: socket.socket) -> bool:
        """Atiende una petición. True si la conexión pasa a ser un suscriptor y no debe cerrarse."""
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
            if request.get("cmd") == "subscribe":
                return self._subscribe(conn)
            try:
                response = self._handler(request)
            except Exception:
                logger.exception("Error en el manejador de control")
                response = {"ok": False, "error": "error interno"}
        try:
            conn.sendall(_encode(response))
        except OSError:
            logger.debug("El cliente de control cerró antes de la respuesta")
        return False

    def _subscribe(self, conn: socket.socket) -> bool:
        """Responde con la foto de `status` más `event` y guarda la conexión como suscriptor. False si se rechaza."""
        try:
            response = self._handler({"cmd": "status"})
        except Exception:
            logger.exception("Error en el manejador de control")
            response = {"ok": False, "error": "error interno"}
        subscribed = bool(response.get("ok"))
        if subscribed:
            response = {**response, "event": "status"}
        try:
            conn.settimeout(SEND_TIMEOUT)
            conn.sendall(_encode(response))
        except OSError:
            logger.debug("El suscriptor cerró antes de la primera línea")
            return False
        if subscribed:
            with self._subscribers_lock:
                self._subscribers.append(conn)
            logger.debug("Suscriptor de control añadido")
        return subscribed


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


def _format_status(response: dict) -> str:
    model = response.get("model", {})
    device = response.get("device", {})
    connected = "" if device.get("connected", True) else " (desconectado)"
    return "\n".join([
        f"Estado:   {response.get('state')}" + (" (en pausa)" if response.get("paused") else ""),
        f"Pausa:    {'sí' if response.get('paused') else 'no'}",
        f"Modelo:   {model.get('name')} [{model.get('status')}, {model.get('compute_device')}]",
        f"Idioma:   {response.get('language')}",
        f"Modo:     {response.get('mode')}",
        f"Micrófono: [{device.get('index')}] {device.get('name')}{connected}",
        f"PID:      {response.get('pid')}",
    ])


def _format_devices(response: dict) -> str:
    return "\n".join(
        f"{'*' if item.get('selected') else ' '} [{item.get('index')}] {item.get('name')}" for item in response.get("devices", [])
    )


def _summary(cmd: str, response: dict) -> str:
    """Resumen legible de una respuesta correcta."""
    if cmd == "status":
        return _format_status(response)
    if cmd == "devices":
        return _format_devices(response)
    if cmd in ("pause", "resume"):
        return "Dictado en pausa." if response.get("paused") else "Dictado reanudado."
    if cmd == "language":
        return f"Idioma: {response.get('language')}"
    device = response.get("device", {})
    return f"Micrófono: [{device.get('index')}] {device.get('name')}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="speechflow ctl", description="Controla un proceso speechflow en ejecución por su socket Unix.")
    sub = parser.add_subparsers(dest="command", metavar="{status,pause,resume,language,device,devices}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="imprime la respuesta cruda del servidor")
    sub.add_parser("status", parents=[common], help="estado del proceso")
    sub.add_parser("pause", parents=[common], help="pausa el dictado y libera el modelo")
    sub.add_parser("resume", parents=[common], help="reanuda el dictado y recarga el modelo")
    language = sub.add_parser("language", parents=[common], help="fija el idioma")
    language.add_argument("value", help="es, en o auto")
    device = sub.add_parser("device", parents=[common], help="cambia el micrófono")
    device.add_argument("value", help="next, un índice o un nombre/subcadena")
    sub.add_parser("devices", parents=[common], help="lista los dispositivos de entrada")
    return parser


def main(argv: list[str]) -> int:
    """Cuerpo de `speechflow ctl`. Salida: 0 ok, 1 `ok: false`, 2 uso incorrecto, 3 sin proceso escuchando."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit:
        return exit.code if isinstance(exit.code, int) else 0
    if args.command is None:
        parser.print_help(sys.stderr)
        return 2
    request: dict = {"cmd": args.command}
    if "value" in args:
        value = args.value
        request["value"] = int(value) if args.command == "device" and value.isdecimal() else value
    try:
        response = send_request(request)
    except ControlUnavailable:
        try:
            where = socket_path()
        except RuntimeError:
            where = "(XDG_RUNTIME_DIR no está definida)"
        print(f"SpeechFlow no está en ejecución: no hay socket en {where}.", file=sys.stderr)
        return 3
    except (OSError, ValueError) as error:
        print(f"Error de comunicación con SpeechFlow: {error}", file=sys.stderr)
        return 1
    ok = bool(response.get("ok"))
    if args.json:
        print(json.dumps(response, ensure_ascii=False))
    elif ok:
        print(_summary(args.command, response))
    else:
        print(f"Error: {response.get('error', 'error desconocido')}", file=sys.stderr)
    return 0 if ok else 1
