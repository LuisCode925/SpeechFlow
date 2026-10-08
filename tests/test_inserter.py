"""Tests de speechflow.inserter contra el doble de subprocess.run."""
import subprocess

import pytest

from speechflow.inserter import insert_text


def test_texto_vacio_no_ejecuta_nada(subprocess_falso):
    insert_text("")
    assert subprocess_falso == []


def test_argumentos_de_xdotool(subprocess_falso):
    insert_text("hola mundo")
    assert subprocess_falso == [((["xdotool", "type", "--clearmodifiers", "--", "hola mundo"],), {"check": True})]


def test_texto_que_parece_opcion_va_tras_doble_guion(subprocess_falso):
    insert_text("--help")
    args = subprocess_falso[0][0][0]
    assert args[-2:] == ["--", "--help"]


def test_propaga_el_error_de_xdotool(monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "xdotool")

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        insert_text("x")
