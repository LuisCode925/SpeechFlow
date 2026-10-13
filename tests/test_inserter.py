"""Tests de speechflow.inserter contra el doble de subprocess.run."""
import subprocess

import pytest

from speechflow import inserter
from speechflow.inserter import insert_text


def test_texto_vacio_no_ejecuta_nada(subprocess_falso):
    insert_text("")
    assert subprocess_falso == []


def test_argumentos_de_xdotool(subprocess_falso):
    insert_text("hola mundo", method="type")
    assert subprocess_falso == [((["xdotool", "type", "--clearmodifiers", "--", "hola mundo"],), {"check": True})]


def test_texto_que_parece_opcion_va_tras_doble_guion(subprocess_falso):
    insert_text("--help", method="type")
    args = subprocess_falso[0][0][0]
    assert args[-2:] == ["--", "--help"]


def test_propaga_el_error_de_xdotool(monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "xdotool")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        insert_text("x", method="type")


# --- Modo portapapeles ------------------------------------------------------------------------

READ = ["xclip", "-selection", "clipboard", "-o", "-t", "UTF8_STRING"]
WRITE = ["xclip", "-selection", "clipboard", "-i", "-t", "UTF8_STRING"]
FOCO = ["xdotool", "getwindowfocus"]
CLASE = ["xprop", "-id", "4242", "WM_CLASS"]


class Escenario:
    """Doble de subprocess.run y time.sleep que registra el orden de las llamadas."""

    def __init__(self, monkeypatch, previo="viejo", clase="firefox", instancia=None, fallos=()):
        self.eventos = []
        self.previo = previo
        self.clase = clase
        self.instancia = instancia or clase
        self.fallos = fallos  # comandos (listas) que lanzan CalledProcessError o la excepción dada
        self.kwargs = {}
        monkeypatch.setattr(subprocess, "run", self.run)
        monkeypatch.setattr(inserter.time, "sleep", lambda s: self.eventos.append(("sleep", s)))

    def run(self, cmd, **kwargs):
        self.eventos.append(("run", cmd))
        self.kwargs.setdefault(tuple(cmd), []).append(kwargs)
        for fallo in self.fallos:
            comando, error = fallo if isinstance(fallo, tuple) else (fallo, subprocess.CalledProcessError(1, fallo))
            if cmd == comando:
                raise error
        if cmd == READ:
            return subprocess.CompletedProcess(cmd, 0, stdout=(self.previo or "").encode())
        if cmd == FOCO:
            return subprocess.CompletedProcess(cmd, 0, stdout=b"4242\n")
        if cmd == CLASE:
            salida = f'WM_CLASS(STRING) = "{self.instancia}", "{self.clase}"\n'
            return subprocess.CompletedProcess(cmd, 0, stdout=salida.encode())
        return subprocess.CompletedProcess(cmd, 0)

    def comandos(self):
        return [e[1] if e[0] == "run" else e for e in self.eventos]


def test_clipboard_secuencia_completa(monkeypatch):
    e = Escenario(monkeypatch)
    insert_text("¿Cómo estás? ñandú")
    assert e.comandos() == [
        READ, WRITE, FOCO, CLASE,
        ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
        ("sleep", inserter.PASTE_DELAY),
        WRITE,
    ]
    assert e.kwargs[tuple(WRITE)][0]["input"] == "¿Cómo estás? ñandú".encode()
    assert e.kwargs[tuple(WRITE)][1]["input"] == b"viejo"


def test_clipboard_texto_vacio_no_ejecuta_nada(subprocess_falso):
    insert_text("")
    insert_text("", method="clipboard")
    assert subprocess_falso == []


def test_type_no_llama_a_xclip(subprocess_falso):
    insert_text("hola", method="type")
    assert subprocess_falso == [((["xdotool", "type", "--clearmodifiers", "--", "hola"],), {"check": True})]


def test_texto_va_por_stdin_y_no_como_argumento(monkeypatch):
    e = Escenario(monkeypatch)
    insert_text("secreto")
    assert all("secreto" not in str(c) for c in e.comandos() if isinstance(c, list))
    assert e.kwargs[tuple(WRITE)][0]["stdout"] == subprocess.DEVNULL
    assert e.kwargs[tuple(WRITE)][0]["stderr"] == subprocess.DEVNULL


def test_todas_las_llamadas_llevan_timeout(monkeypatch):
    e = Escenario(monkeypatch)
    insert_text("hola")
    assert all(k["timeout"] == inserter.COMMAND_TIMEOUT for ks in e.kwargs.values() for k in ks)


def test_no_toca_primary(monkeypatch):
    e = Escenario(monkeypatch)
    insert_text("hola")
    assert all("primary" not in c for c in e.comandos() if isinstance(c, list))


@pytest.mark.parametrize("clase", ["gnome-terminal", "GNOME-Terminal", "Konsole", "kitty", "yakuake"])
def test_terminal_pega_con_ctrl_shift_v(monkeypatch, clase):
    e = Escenario(monkeypatch, clase=clase)
    insert_text("hola")
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"] in e.comandos()


def test_coincide_por_instancia_o_por_clase(monkeypatch):
    e = Escenario(monkeypatch, instancia="kitty", clase="otra")
    insert_text("hola")
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"] in e.comandos()


def test_xprop_sin_wm_class_usa_ctrl_v(monkeypatch):
    e = Escenario(monkeypatch)
    run = e.run

    def sin_clase(cmd, **kw):
        if cmd == CLASE:
            e.eventos.append(("run", cmd))
            return subprocess.CompletedProcess(cmd, 0, stdout=b"WM_CLASS:  not found.\n")
        return run(cmd, **kw)

    monkeypatch.setattr(subprocess, "run", sin_clase)
    insert_text("hola")
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+v"] in e.comandos()


def test_extra_terminals_sin_distinguir_mayusculas(monkeypatch):
    e = Escenario(monkeypatch, clase="MyTerm")
    insert_text("hola", extra_terminals=("myterm",))
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"] in e.comandos()


def test_clase_desconocida_pega_con_ctrl_v(monkeypatch):
    e = Escenario(monkeypatch, clase="otra")
    insert_text("hola", extra_terminals=("myterm",))
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+v"] in e.comandos()


@pytest.mark.parametrize("fallo", [FOCO, CLASE])
def test_fallo_al_averiguar_la_clase_usa_ctrl_v(monkeypatch, fallo):
    e = Escenario(monkeypatch, clase="kitty", fallos=[fallo])
    insert_text("hola")
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+v"] in e.comandos()
    assert not any(c[:2] == ["xdotool", "type"] for c in e.comandos() if isinstance(c, list))


@pytest.mark.parametrize("previo", [None, ""])
def test_portapapeles_previo_vacio_no_se_restaura(monkeypatch, previo):
    e = Escenario(monkeypatch, previo=previo)
    insert_text("hola")
    assert e.comandos().count(WRITE) == 1


def test_portapapeles_previo_ilegible_no_se_restaura(monkeypatch):
    e = Escenario(monkeypatch, fallos=[READ])
    insert_text("hola")
    assert e.comandos().count(WRITE) == 1
    assert ["xdotool", "key", "--clearmodifiers", "ctrl+v"] in e.comandos()


@pytest.mark.parametrize(
    "error",
    [subprocess.CalledProcessError(1, "x"), OSError(2, "No such file"), subprocess.TimeoutExpired("x", 2)],
)
def test_fallo_de_xdotool_key_restaura_y_teclea(monkeypatch, caplog, error):
    key = ["xdotool", "key", "--clearmodifiers", "ctrl+v"]
    e = Escenario(monkeypatch, fallos=[(key, error)])
    with caplog.at_level("WARNING", logger="speechflow"):
        insert_text("--hola")
    assert e.comandos()[-2:] == [WRITE, ["xdotool", "type", "--clearmodifiers", "--", "--hola"]]
    assert e.comandos().count(WRITE) == 2
    assert "Portapapeles no disponible (" in caplog.text and "se teclea con xdotool type." in caplog.text


def test_fallo_de_xclip_al_escribir_teclea(monkeypatch, caplog):
    e = Escenario(monkeypatch, previo=None, fallos=[WRITE])
    with caplog.at_level("WARNING", logger="speechflow"):
        insert_text("hola")
    assert e.comandos()[-1] == ["xdotool", "type", "--clearmodifiers", "--", "hola"]
    assert "Portapapeles no disponible" in caplog.text


def test_fallo_de_respaldo_se_propaga(monkeypatch):
    type_cmd = ["xdotool", "type", "--clearmodifiers", "--", "hola"]
    Escenario(monkeypatch, fallos=[WRITE, type_cmd])
    with pytest.raises(subprocess.CalledProcessError):
        insert_text("hola")


def test_el_log_no_contiene_el_portapapeles_previo(monkeypatch, caplog):
    Escenario(monkeypatch, previo="contraseña", fallos=[["xdotool", "key", "--clearmodifiers", "ctrl+v"]])
    with caplog.at_level("DEBUG", logger="speechflow"):
        insert_text("hola")
    assert "contraseña" not in caplog.text


def test_fallo_al_restaurar_no_teclea_ni_propaga(monkeypatch, caplog):
    e = Escenario(monkeypatch)
    originalrun = e.run
    llamadas_write = []

    def run(cmd, **kwargs):
        if cmd == WRITE:
            llamadas_write.append(1)
            if len(llamadas_write) == 2:
                raise subprocess.CalledProcessError(1, "xclip")
        return originalrun(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", run)
    with caplog.at_level("WARNING", logger="speechflow"):
        insert_text("hola")
    assert not any(c[:2] == ["xdotool", "type"] for c in e.comandos() if isinstance(c, list))
    assert "No se pudo restaurar el portapapeles" in caplog.text
