"""Aislamiento común de la suite: sin HOME real, sin subprocesos reales y sin servidor X obligatorio."""
import os
import subprocess

# Debe fijarse antes de importar speechflow.app (pynput falla sin X).
if not os.environ.get("DISPLAY"):
    os.environ.setdefault("PYNPUT_BACKEND", "dummy")

import pytest

from speechflow import notifier


@pytest.fixture(autouse=True)
def aislar_entorno(tmp_path, monkeypatch):
    """HOME y XDG_* apuntan a tmp_path para no tocar la configuración real."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))


@pytest.fixture(autouse=True)
def subprocess_falso(monkeypatch):
    """Sustituye subprocess.run por un doble que registra (args, kwargs)."""
    llamadas = []

    def run(*args, **kwargs):
        llamadas.append((args, kwargs))
        return subprocess.CompletedProcess(args[0] if args else [], 0)

    monkeypatch.setattr(subprocess, "run", run)
    return llamadas


@pytest.fixture(autouse=True)
def restaurar_notifier():
    """notifier vuelve a su estado inicial (activado) tras cada test."""
    yield
    notifier.set_enabled(True)
