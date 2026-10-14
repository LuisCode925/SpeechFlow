"""Canal de control: servidor, cliente y `ctl`, con XDG_RUNTIME_DIR en un directorio temporal corto."""
import json
import shutil
import socket
import stat
import tempfile
import time
from pathlib import Path

import pytest

from speechflow import control


@pytest.fixture
def runtime(monkeypatch):
    # Los sockets Unix limitan la ruta a 108 bytes: tmp_path puede ser demasiado largo.
    directory = Path(tempfile.mkdtemp(prefix="sf"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(directory))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def servidor(runtime):
    creados = []

    def crear(handler=None):
        server = control.ControlServer(handler or (lambda request: {"ok": True, "eco": request}), control.socket_path())
        server.start()
        creados.append(server)
        return server

    yield crear
    for server in creados:
        server.close()


def _raw(path, payload: bytes, *, shutdown=True) -> bytes:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(5)
        sock.connect(str(path))
        sock.sendall(payload)
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        return data


def test_socket_path(runtime):
    assert control.socket_path() == runtime / "speechflow" / "control.sock"


def test_socket_path_sin_xdg_runtime_dir(monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    with pytest.raises(RuntimeError):
        control.socket_path()


def test_ida_y_vuelta(servidor):
    servidor()
    respuesta = control.send_request({"cmd": "status", "value": "ñ"})
    assert respuesta == {"ok": True, "eco": {"cmd": "status", "value": "ñ"}}


def test_permisos(servidor):
    servidor()
    path = control.socket_path()
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_close_borra_el_archivo_y_es_idempotente(servidor):
    server = servidor()
    path = control.socket_path()
    assert path.exists()
    server.close()
    assert not path.exists()
    server.close()


def test_json_invalido(servidor):
    servidor()
    respuesta = json.loads(_raw(control.socket_path(), b"esto no es json\n"))
    assert respuesta["ok"] is False
    assert respuesta["error"].startswith("petición inválida")
    assert control.send_request({"cmd": "x"})["ok"] is True


def test_peticion_que_no_es_objeto(servidor):
    servidor()
    respuesta = json.loads(_raw(control.socket_path(), b"[1, 2]\n"))
    assert respuesta["ok"] is False


def test_linea_de_mas_de_4096_bytes(servidor):
    servidor()
    respuesta = json.loads(_raw(control.socket_path(), b'{"cmd": "' + b"a" * 5000 + b'"}\n'))
    assert respuesta["ok"] is False
    assert "4096" in respuesta["error"]
    assert control.send_request({"cmd": "x"})["ok"] is True


def test_error_del_manejador_no_tumba_el_servidor(servidor):
    def handler(request):
        raise RuntimeError("fallo")

    servidor(handler)
    assert control.send_request({"cmd": "x"}) == {"ok": False, "error": "error interno"}
    assert control.send_request({"cmd": "x"})["ok"] is False


def test_cliente_que_no_envia_nada_no_bloquea_al_siguiente(servidor, monkeypatch):
    monkeypatch.setattr(control, "READ_TIMEOUT", 0.5)
    servidor()
    lento = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    lento.connect(str(control.socket_path()))
    try:
        inicio = time.monotonic()
        assert control.send_request({"cmd": "x"})["ok"] is True
        assert time.monotonic() - inicio < 3
    finally:
        lento.close()


def test_socket_huerfano_se_reemplaza(runtime):
    path = control.socket_path()
    path.parent.mkdir(mode=0o700)
    huerfano = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    huerfano.bind(str(path))
    huerfano.close()  # el archivo queda sin nadie que acepte
    assert path.exists()
    server = control.ControlServer(lambda request: {"ok": True}, path)
    server.start()
    try:
        assert control.send_request({"cmd": "x"}) == {"ok": True}
    finally:
        server.close()


def test_socket_de_instancia_viva_no_se_borra(servidor):
    servidor()
    path = control.socket_path()
    segundo = control.ControlServer(lambda request: {"ok": False}, path)
    with pytest.raises(OSError):
        segundo.start()
    assert path.exists()
    assert control.send_request({"cmd": "x"})["ok"] is True


def test_ruta_demasiado_larga_falla_con_oserror(runtime):
    path = runtime / ("d" * 120) / "control.sock"
    with pytest.raises(OSError):
        control.ControlServer(lambda request: {"ok": True}, path).start()


def test_send_request_sin_socket(runtime):
    with pytest.raises(control.ControlUnavailable):
        control.send_request({"cmd": "status"})


def test_send_request_sin_xdg_runtime_dir(monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    with pytest.raises(control.ControlUnavailable):
        control.send_request({"cmd": "status"})


def test_send_request_con_socket_huerfano(runtime):
    path = control.socket_path()
    path.parent.mkdir(mode=0o700)
    huerfano = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    huerfano.bind(str(path))
    huerfano.close()
    with pytest.raises(control.ControlUnavailable):
        control.send_request({"cmd": "status"})


def test_importar_no_crea_archivos(runtime):
    import importlib

    importlib.reload(control)
    assert list(runtime.iterdir()) == []
