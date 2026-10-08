"""Aislamiento común de la suite: sin HOME real, sin subprocesos reales y sin servidor X obligatorio."""
import os
import subprocess
from pathlib import Path

# Debe fijarse antes de importar speechflow.app (pynput falla sin X).
if not os.environ.get("DISPLAY"):
    os.environ.setdefault("PYNPUT_BACKEND", "dummy")

# La caché de Hugging Face es del HOME real: el test gpu la necesita aunque HOME se aísle por test.
os.environ.setdefault("HF_HOME", str(Path.home() / ".cache" / "huggingface"))

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


# --- Doble de sounddevice -------------------------------------------------------------------

import numpy as np
import sounddevice as sd


def dispositivo(nombre, entradas=1, tasa=48000):
    return {"name": nombre, "max_input_channels": entradas, "max_output_channels": 2, "default_samplerate": float(tasa)}


class InputStreamFalso:
    """Sustituye a sd.InputStream: no abre hardware; `alimentar` simula el callback de PortAudio."""

    instancias: list["InputStreamFalso"] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.callback = kwargs["callback"]
        self.active = False
        self.cerrado = False
        self.falla_al_parar = False
        InputStreamFalso.instancias.append(self)

    def start(self):
        self.active = True

    def stop(self):
        if self.falla_al_parar:
            raise sd.PortAudioError("stream caído")
        self.active = False

    def close(self):
        self.cerrado = True
        self.active = False

    def alimentar(self, datos, status=None):
        self.callback(datos, len(datos), None, status)


class SoundDeviceFalso:
    """Estado del doble de sounddevice; los tests modifican `dispositivos` y `defecto`."""

    def __init__(self):
        self.dispositivos = [dispositivo("HDA Intel: salida", entradas=0), dispositivo("Realtek ALC", 2), dispositivo("USB Mic")]
        self.defecto = 1
        self.con_index = True
        self.reinicios = 0

    def query_devices(self, device=None, kind=None):
        if device is None and kind is None:
            return [dict(d, index=i) if self.con_index else dict(d) for i, d in enumerate(self.dispositivos)]
        if device is None:
            device = self.defecto
        if isinstance(device, str):
            coincidencias = [i for i, d in enumerate(self.dispositivos) if device.lower() in d["name"].lower()]
            if not coincidencias:
                raise ValueError(f"No input device matching {device!r}")
            device = coincidencias[0]
        if not 0 <= device < len(self.dispositivos):
            raise sd.PortAudioError("Error querying device")
        info = self.dispositivos[device]
        if kind == "input" and info["max_input_channels"] <= 0:
            raise sd.PortAudioError("Invalid input device")
        return dict(info, index=device) if self.con_index else dict(info)

    def _terminate(self):
        self.reinicios += 1

    def _initialize(self):
        pass


@pytest.fixture(autouse=True)
def sounddevice_falso(monkeypatch):
    """Ningún test ve ni abre dispositivos de audio reales."""
    falso = SoundDeviceFalso()
    InputStreamFalso.instancias = []
    monkeypatch.setattr(sd, "query_devices", falso.query_devices)
    monkeypatch.setattr(sd, "_terminate", falso._terminate)
    monkeypatch.setattr(sd, "_initialize", falso._initialize)
    monkeypatch.setattr(sd, "InputStream", InputStreamFalso)
    monkeypatch.setattr(sd.default, "device", (falso.defecto, None))
    return falso
