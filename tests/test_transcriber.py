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
        self.detecciones = []
        self.probabilidades = [("es", 0.6), ("en", 0.3)]
        WhisperModelFalso.instancias.append(self)

    def transcribe(self, audio, **kwargs):
        self.llamadas.append((audio, kwargs))
        return iter([SimpleNamespace(text=t) for t in self.textos]), None

    def detect_language(self, audio, **kwargs):
        self.detecciones.append(audio)
        if isinstance(self.probabilidades, Exception):
            raise self.probabilidades
        return self.probabilidades[0][0], self.probabilidades[0][1], self.probabilidades


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


def test_calentamiento_con_vad_hace_dos_llamadas(modelo):
    Transcriber("small", "en", vad=True)
    llamadas = modelo.instancias[0].llamadas
    assert [k for _, k in llamadas] == [{"language": "en"}, {"language": "en", "vad_filter": True}]
    assert all(len(a) == SAMPLE_RATE for a, _ in llamadas)


def test_calentamiento_sin_vad_hace_una_llamada(modelo):
    Transcriber("small", "en", vad=False)
    assert [k for _, k in modelo.instancias[0].llamadas] == [{"language": "en"}]


def test_vad_activo_por_defecto(modelo):
    assert Transcriber().vad is True


def test_transcribe_pasa_vad_filter(modelo):
    Transcriber().transcribe(np.ones(10, dtype=np.int16))
    assert modelo.instancias[0].llamadas[-1][1] == {"language": "es", "vad_filter": True}


def test_transcribe_sin_vad_pasa_false(modelo):
    Transcriber(vad=False).transcribe(np.ones(10, dtype=np.int16))
    assert modelo.instancias[0].llamadas[-1][1] == {"language": "es", "vad_filter": False}


def test_valores_por_defecto(modelo):
    t = Transcriber()
    assert modelo.instancias[0].nombre == "medium" and t.language == "es"


def test_audio_vacio_no_llama_al_modelo(modelo):
    t = Transcriber()
    assert t.transcribe(np.zeros((0, 1), dtype=np.int16)) == ("", 0.0)
    assert len(modelo.instancias[0].llamadas) == 2  # solo los dos calentamientos


def test_convierte_a_float32_normalizado_y_1d(modelo):
    t = Transcriber()
    t.transcribe(np.full((100, 1), 16384, dtype=np.int16))
    muestras, kwargs = modelo.instancias[0].llamadas[-1]
    assert muestras.dtype == np.float32 and muestras.shape == (100,)
    assert muestras[0] == pytest.approx(0.5) and kwargs == {"language": "es", "vad_filter": True}


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


def test_calentamiento_detecta_idioma_sobre_silencio(modelo):
    Transcriber("small", "en")
    (silencio,) = modelo.instancias[0].detecciones
    assert len(silencio) == SAMPLE_RATE and not silencio.any()


def test_calentamiento_en_auto_usa_idioma_fijo_por_defecto(modelo):
    Transcriber("small", "auto")
    assert [k["language"] for _, k in modelo.instancias[0].llamadas] == ["es", "es"]


def test_idioma_explicito_gana_sobre_el_del_objeto(modelo):
    t = Transcriber(language="es")
    t.transcribe(np.ones(10, dtype=np.int16), language="en")
    assert modelo.instancias[0].llamadas[-1][1] == {"language": "en", "vad_filter": True}
    assert t.last_language == "en" and t.language == "es"


def test_idioma_por_defecto_es_el_del_objeto(modelo):
    t = Transcriber(language="en")
    t.transcribe(np.ones(10, dtype=np.int16))
    assert modelo.instancias[0].llamadas[-1][1]["language"] == "en" and t.last_language == "en"


def test_last_language_inicial_es_none(modelo):
    assert Transcriber().last_language is None


@pytest.mark.parametrize("probabilidades, esperado", [
    ([("es", 0.7), ("en", 0.2)], "es"),
    ([("en", 0.7), ("es", 0.2)], "en"),
    ([("fr", 0.8), ("en", 0.12), ("es", 0.05)], "en"),  # otro idioma con la mayor probabilidad
    ([("de", 0.8), ("es", 0.12), ("en", 0.05)], "es"),
])
def test_auto_elige_entre_es_y_en(modelo, probabilidades, esperado):
    t = Transcriber(language="auto")
    modelo.instancias[0].probabilidades = probabilidades
    t.transcribe(np.ones(10, dtype=np.int16))
    assert t.last_language == esperado
    assert modelo.instancias[0].llamadas[-1][1] == {"language": esperado, "vad_filter": True}


def test_auto_pasado_por_parametro(modelo):
    t = Transcriber(language="es")
    modelo.instancias[0].probabilidades = [("en", 0.9), ("es", 0.05)]
    t.transcribe(np.ones(10, dtype=np.int16), language="auto")
    assert t.last_language == "en" and t.language == "es"


def test_auto_detecta_sobre_el_audio_normalizado(modelo):
    t = Transcriber(language="auto")
    t.transcribe(np.full((100, 1), 16384, dtype=np.int16))
    muestras = modelo.instancias[0].detecciones[-1]
    assert muestras.shape == (100,) and muestras[0] == pytest.approx(0.5)


@pytest.mark.parametrize("fallo", [ValueError("sin voz"), []])
def test_auto_con_fallo_de_deteccion_usa_idioma_fijo(modelo, fallo):
    t = Transcriber(language="auto")
    modelo.instancias[0].probabilidades = fallo
    texto, _ = t.transcribe(np.zeros(16000, dtype=np.int16))
    assert t.last_language == "es" and texto == "hola mundo"


def test_auto_con_fallo_usa_el_idioma_fijo_si_es_candidato(modelo):
    t = Transcriber(language="en")
    modelo.instancias[0].probabilidades = ValueError("sin voz")
    t.transcribe(np.zeros(16000, dtype=np.int16), language="auto")
    assert t.last_language == "en"


def test_auto_con_idioma_fijo_ajeno_cae_a_es(modelo):
    t = Transcriber(language="fr")
    modelo.instancias[0].probabilidades = ValueError("sin voz")
    t.transcribe(np.zeros(16000, dtype=np.int16), language="auto")
    assert t.last_language == "es"


def test_auto_sin_voz_sigue_el_camino_normal(modelo):
    t = Transcriber(language="auto")
    modelo.instancias[0].textos = []
    assert t.transcribe(np.zeros(16000, dtype=np.int16))[0] == ""


def test_audio_vacio_actualiza_last_language_sin_detectar(modelo):
    t = Transcriber(language="auto")
    assert t.transcribe(np.zeros((0, 1), dtype=np.int16)) == ("", 0.0)
    assert t.last_language == "es" and len(modelo.instancias[0].detecciones) == 1  # solo el calentamiento
