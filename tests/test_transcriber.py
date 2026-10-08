"""Tests de speechflow.transcriber con WhisperModel falseado."""
from types import SimpleNamespace

import numpy as np
import pytest

from speechflow import transcriber
from speechflow.transcriber import SAMPLE_RATE, Transcriber


class WhisperModelFalso:
    instancias: list["WhisperModelFalso"] = []

    def __init__(self, nombre, **kwargs):
        self.nombre = nombre
        self.kwargs = kwargs
        self.llamadas = []
        self.textos = [" hola ", "mundo "]
        WhisperModelFalso.instancias.append(self)

    def transcribe(self, audio, **kwargs):
        self.llamadas.append((audio, kwargs))
        return iter([SimpleNamespace(text=t) for t in self.textos]), None


@pytest.fixture
def modelo(monkeypatch):
    WhisperModelFalso.instancias = []
    monkeypatch.setattr(transcriber, "WhisperModel", WhisperModelFalso)
    return WhisperModelFalso


def test_carga_el_modelo_en_gpu_y_lo_calienta(modelo):
    Transcriber("small", "en")
    (falso,) = modelo.instancias
    assert falso.nombre == "small"
    assert falso.kwargs == {"device": "cuda", "compute_type": "int8"}
    audio, kwargs = falso.llamadas[0]
    assert len(audio) == SAMPLE_RATE and kwargs == {"language": "en"}


def test_valores_por_defecto(modelo):
    t = Transcriber()
    assert modelo.instancias[0].nombre == "medium" and t.language == "es"


def test_audio_vacio_no_llama_al_modelo(modelo):
    t = Transcriber()
    assert t.transcribe(np.zeros((0, 1), dtype=np.int16)) == ("", 0.0)
    assert len(modelo.instancias[0].llamadas) == 1  # solo el calentamiento


def test_convierte_a_float32_normalizado_y_1d(modelo):
    t = Transcriber()
    t.transcribe(np.full((100, 1), 16384, dtype=np.int16))
    muestras, kwargs = modelo.instancias[0].llamadas[-1]
    assert muestras.dtype == np.float32 and muestras.shape == (100,)
    assert muestras[0] == pytest.approx(0.5) and kwargs == {"language": "es"}


def test_une_segmentos_y_mide_tiempo(modelo):
    t = Transcriber()
    texto, segundos = t.transcribe(np.ones(10, dtype=np.int16))
    assert texto == "hola mundo" and segundos >= 0.0


def test_close_suelta_el_modelo(modelo):
    t = Transcriber()
    t.close()
    assert t._model is None


def test_close_es_idempotente(modelo):
    t = Transcriber()
    t.close()
    t.close()
