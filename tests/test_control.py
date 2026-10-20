"""Canal de control: servidor, cliente y `ctl`, con XDG_RUNTIME_DIR en un directorio temporal corto."""
import json
import shutil
import socket
import stat
import tempfile
import threading
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


# --- speechflow ctl ---------------------------------------------------------------------------

STATUS = {
    "ok": True, "pid": 1234, "state": "idle", "paused": False,
    "model": {"name": "large-v3-turbo", "status": "loaded", "compute_device": "cuda"},
    "language": "es", "mode": "hold", "device": {"index": 7, "name": "Blue Yeti", "connected": True},
}


@pytest.fixture
def peticiones(monkeypatch):
    """Sustituye send_request por un doble: devuelve `respuesta` y registra las peticiones."""
    class Registro(list):
        estado: dict

    registro = Registro()
    estado = {"respuesta": {"ok": True}, "error": None}

    def falso(request, timeout=10.0):
        registro.append(request)
        if estado["error"]:
            raise estado["error"]
        return estado["respuesta"]

    monkeypatch.setattr(control, "send_request", falso)
    registro.estado = estado
    return registro


def test_ctl_status_legible(peticiones, capsys):
    peticiones.estado["respuesta"] = STATUS
    assert control.main(["status"]) == 0
    out = capsys.readouterr().out
    assert peticiones == [{"cmd": "status"}]
    for texto in ("idle", "large-v3-turbo", "loaded", "cuda", "es", "hold", "Blue Yeti"):
        assert texto in out
    assert len(out.splitlines()) > 1


def test_ctl_json_imprime_la_respuesta_cruda(peticiones, capsys):
    peticiones.estado["respuesta"] = STATUS
    assert control.main(["status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == STATUS


def test_ctl_pause_y_resume(peticiones, capsys):
    peticiones.estado["respuesta"] = {"ok": True, "paused": True}
    assert control.main(["pause"]) == 0
    assert "pausa" in capsys.readouterr().out
    peticiones.estado["respuesta"] = {"ok": True, "paused": False}
    assert control.main(["resume"]) == 0
    assert "reanudado" in capsys.readouterr().out
    assert peticiones == [{"cmd": "pause"}, {"cmd": "resume"}]


def test_ctl_language(peticiones, capsys):
    peticiones.estado["respuesta"] = {"ok": True, "language": "en"}
    assert control.main(["language", "en"]) == 0
    assert peticiones == [{"cmd": "language", "value": "en"}]
    assert "en" in capsys.readouterr().out


@pytest.mark.parametrize("argumento,valor", [("next", "next"), ("3", 3), ("USB", "USB")])
def test_ctl_device_envia_el_valor(peticiones, capsys, argumento, valor):
    peticiones.estado["respuesta"] = {"ok": True, "device": {"index": 3, "name": "USB Audio"}}
    assert control.main(["device", argumento]) == 0
    assert peticiones == [{"cmd": "device", "value": valor}]
    assert "USB Audio" in capsys.readouterr().out


def test_ctl_devices(peticiones, capsys):
    peticiones.estado["respuesta"] = {"ok": True, "devices": [
        {"index": 3, "name": "USB Audio", "selected": False},
        {"index": 7, "name": "Blue Yeti", "selected": True},
    ]}
    assert control.main(["devices"]) == 0
    lineas = capsys.readouterr().out.splitlines()
    assert len(lineas) == 2
    assert lineas[1].startswith("*") and "Blue Yeti" in lineas[1]


def test_ctl_error_del_servidor_sale_con_1(peticiones, capsys):
    peticiones.estado["respuesta"] = {"ok": False, "error": "ocupado: grabando"}
    assert control.main(["pause"]) == 1
    assert "ocupado: grabando" in capsys.readouterr().err


def test_ctl_error_con_json_sale_con_1(peticiones, capsys):
    peticiones.estado["respuesta"] = {"ok": False, "error": "idioma no válido: fr"}
    assert control.main(["language", "fr", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_ctl_sin_proceso_sale_con_3(runtime, peticiones, capsys):
    peticiones.estado["error"] = control.ControlUnavailable("no hay socket")
    assert control.main(["status"]) == 3
    err = capsys.readouterr().err
    assert "SpeechFlow no está en ejecución" in err
    assert str(control.socket_path()) in err


def test_ctl_uso_incorrecto_sale_con_2(peticiones, capsys):
    assert control.main([]) == 2
    assert "status" in capsys.readouterr().err
    assert control.main(["bailar"]) == 2
    assert control.main(["language"]) == 2
    assert control.main(["device"]) == 2
    assert peticiones == []


def test_ctl_help_sale_con_0(capsys):
    assert control.main(["--help"]) == 0
    assert "status" in capsys.readouterr().out


# --- subscribe (SPEC 30) ---

ESTADO = {"ok": True, "pid": 1, "state": "idle", "paused": False}


def _suscribir(path) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect(str(path))
    sock.sendall(b'{"cmd": "subscribe"}\n')
    return sock


def _linea(sock) -> dict:
    data = b""
    while not data.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return json.loads(data)


def test_subscribe_responde_con_status_y_event(servidor):
    peticiones = []
    servidor(lambda request: peticiones.append(request) or dict(ESTADO))
    with _suscribir(control.socket_path()) as sock:
        assert _linea(sock) == {**ESTADO, "event": "status"}
    assert peticiones == [{"cmd": "status"}]


def test_subscribe_no_cierra_la_conexion_ni_bloquea_otras_peticiones(servidor):
    server = servidor(lambda request: dict(ESTADO))
    with _suscribir(control.socket_path()) as sock:
        _linea(sock)
        inicio = time.monotonic()
        assert control.send_request({"cmd": "status"}) == ESTADO
        assert time.monotonic() - inicio < 1
        sock.settimeout(0.3)
        with pytest.raises(TimeoutError):
            sock.recv(1)  # sigue abierta: ni datos ni EOF
        assert len(server._subscribers) == 1


def test_subscribe_con_error_de_status_cierra_la_conexion(servidor):
    server = servidor(lambda request: {"ok": False, "error": "no disponible"})
    with _suscribir(control.socket_path()) as sock:
        assert _linea(sock) == {"ok": False, "error": "no disponible"}
        assert sock.recv(1) == b""
    assert server._subscribers == []


class EstadoMutable:
    """`handler` doble: devuelve el estado actual, que el test cambia."""

    def __init__(self):
        self.estado = dict(ESTADO)

    def __call__(self, request):
        return dict(self.estado)


def _esperar(condicion, plazo=3.0):
    limite = time.monotonic() + plazo
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.01)
    return False


def _publicador_vivo() -> bool:
    return any(hilo.name == "control-publisher" for hilo in threading.enumerate())


@pytest.fixture
def rapido(monkeypatch):
    monkeypatch.setattr(control, "PUBLISH_INTERVAL", 0.02)


def test_un_cambio_llega_a_dos_suscriptores(servidor, rapido):
    handler = EstadoMutable()
    servidor(handler)
    with _suscribir(control.socket_path()) as uno, _suscribir(control.socket_path()) as dos:
        _linea(uno), _linea(dos)
        handler.estado["paused"] = True
        assert _linea(uno) == {**handler.estado, "event": "status"}
        assert _linea(dos) == {**handler.estado, "event": "status"}


def test_sin_cambios_no_se_envia_nada(servidor, rapido):
    servidor(EstadoMutable())
    with _suscribir(control.socket_path()) as sock:
        _linea(sock)
        sock.settimeout(0.3)
        with pytest.raises(TimeoutError):
            sock.recv(1)


def test_suscriptor_cerrado_se_descarta_y_el_hilo_termina(servidor, rapido):
    server = servidor(EstadoMutable())
    sock = _suscribir(control.socket_path())
    _linea(sock)
    assert _publicador_vivo()
    sock.close()
    assert _esperar(lambda: not server._subscribers)
    assert _esperar(lambda: not _publicador_vivo())


def test_excepcion_en_status_no_mata_el_publicador(servidor, rapido):
    handler = EstadoMutable()
    fallos = []

    def fragil(request):
        if fallos:
            raise RuntimeError("boom")
        return handler(request)

    servidor(fragil)
    with _suscribir(control.socket_path()) as sock:
        _linea(sock)
        fallos.append(1)
        time.sleep(0.1)
        fallos.clear()
        handler.estado["state"] = "recording"
        assert _linea(sock)["state"] == "recording"


def test_el_noveno_suscriptor_se_rechaza(servidor, rapido):
    server = servidor(EstadoMutable())
    socks = [_suscribir(control.socket_path()) for _ in range(control.MAX_SUBSCRIBERS)]
    try:
        for sock in socks:
            assert _linea(sock)["event"] == "status"
        with _suscribir(control.socket_path()) as noveno:
            assert _linea(noveno) == {"ok": False, "error": "demasiados suscriptores"}
            assert noveno.recv(1) == b""
        assert len(server._subscribers) == control.MAX_SUBSCRIBERS
        assert control.send_request({"cmd": "status"}) == ESTADO  # el proceso sigue atendiendo
    finally:
        for sock in socks:
            sock.close()


def test_suscriptor_cerrado_libera_su_plaza(servidor, rapido):
    server = servidor(EstadoMutable())
    socks = [_suscribir(control.socket_path()) for _ in range(control.MAX_SUBSCRIBERS)]
    for sock in socks:
        _linea(sock)
    socks.pop().close()
    assert _esperar(lambda: len(server._subscribers) == control.MAX_SUBSCRIBERS - 1)
    with _suscribir(control.socket_path()) as nuevo:
        assert _linea(nuevo)["event"] == "status"
    for sock in socks:
        sock.close()


def test_close_envia_eof_a_los_suscriptores_y_borra_el_socket(servidor, rapido):
    server = servidor(EstadoMutable())
    path = control.socket_path()
    with _suscribir(path) as uno, _suscribir(path) as dos:
        _linea(uno), _linea(dos)
        server.close()
        assert uno.recv(1) == b""
        assert dos.recv(1) == b""
    assert not path.exists()
    assert not _publicador_vivo()
