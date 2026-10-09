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


# --- Dobles de PushToTalk -------------------------------------------------------------------

import threading
import time
from types import SimpleNamespace

from speechflow.transcriber import SAMPLE_RATE


def esperar(condicion, timeout=2.0):
    """Espera a que `condicion()` sea verdadera (sondeo de 2 ms); falla si pasan `timeout` s."""
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return
        time.sleep(0.002)
    raise AssertionError("la condición no se cumplió a tiempo")


def audio_de(segundos):
    return np.zeros((int(segundos * SAMPLE_RATE), 1), dtype=np.int16)


class RecorderFalso:
    """Sustituye a Recorder: no abre ningún stream; `segundos` es la duración que devuelve stop()."""

    def __init__(self, device=None):
        self.device = device
        self.segundos = 1.0
        self.error_al_iniciar = None
        self.inicios = 0
        self.paradas = 0
        self._activo = False

    @property
    def active(self):
        return self._activo

    def start(self):
        if self.error_al_iniciar is not None:
            raise self.error_al_iniciar
        self.inicios += 1
        self._activo = True

    def stop(self):
        self.paradas += 1
        self._activo = False
        return audio_de(self.segundos)

    def caer(self):
        """Simula que el stream se cae (micrófono desconectado durante la grabación)."""
        self._activo = False


class TranscriberFalso:
    """Sustituye a Transcriber. Con `bloquear=True`, transcribe() espera a `liberar` y avisa en `entro`."""

    instancias: list["TranscriberFalso"] = []

    def __init__(self, texto="hola mundo", bloquear=False, detectado="es"):
        self.texto = texto
        self.detectado = detectado  # idioma que "detecta" en modo auto
        self.idiomas = []  # `language` recibido en cada transcribe()
        self.last_language = None
        self.error = None
        self.bloquear = bloquear
        self.entro = threading.Event()
        self.liberar = threading.Event()
        self.llamadas = 0
        self.cierres = 0
        TranscriberFalso.instancias.append(self)

    def transcribe(self, audio, language=None):
        self.llamadas += 1
        self.idiomas.append(language)
        self.last_language = self.detectado if language == "auto" else language
        self.entro.set()
        if self.bloquear:
            self.liberar.wait(5)
        if self.error is not None:
            raise self.error
        return self.texto, 0.1

    def close(self):
        self.cierres += 1


@pytest.fixture
def dobles(monkeypatch):
    """Sustituye Recorder, notify e insert_text de speechflow.app y registra sus llamadas."""
    from speechflow import app

    registro = SimpleNamespace(
        notificaciones=[],
        textos=[],
        insertado=threading.Event(),
        error_insercion=None,
    )

    def insert_text(texto):
        if registro.error_insercion is not None:
            raise registro.error_insercion
        registro.textos.append(texto)
        registro.insertado.set()

    TranscriberFalso.instancias = []
    monkeypatch.setattr(app, "Recorder", RecorderFalso)
    monkeypatch.setattr(app, "notify", lambda titulo, cuerpo="": registro.notificaciones.append((titulo, cuerpo)))
    monkeypatch.setattr(app, "insert_text", insert_text)
    return registro


@pytest.fixture
def crear_ptt(dobles, caplog):
    """Fábrica de PushToTalk con teclas centinela y tiempos cortos; al terminar para hilos y temporizadores."""
    from pynput import keyboard

    from speechflow import app

    creados = []
    caplog.set_level("INFO", logger="speechflow")

    def fabrica(transcriber="auto", device=None, min_seconds=0.1, max_seconds=5.0, idle_timeout=0.0, vad=True, language="es"):
        if transcriber == "auto":
            transcriber = TranscriberFalso()
        ptt = app.PushToTalk(
            keyboard.KeyCode.from_char("r"),
            keyboard.KeyCode.from_char("f"),
            device,
            transcriber,
            "medium",
            language,
            min_seconds,
            max_seconds,
            idle_timeout,
            vad,
        )
        creados.append(ptt)
        return ptt

    yield fabrica

    for ptt in creados:
        ptt.stop_watcher()
        with ptt._lock:
            ptt._cancel_idle_timer()
            if ptt._timer is not None:
                ptt._timer.cancel()
        for t in TranscriberFalso.instancias:
            t.liberar.set()
        for hilo in (ptt._worker, ptt._loader):
            if hilo is not None:
                hilo.join(2)
