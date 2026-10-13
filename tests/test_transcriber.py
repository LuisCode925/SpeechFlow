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


class CTranslate2Falso:
    """Sustituye al módulo ctranslate2: cuenta GPUs y registra las consultas."""

    def __init__(self, gpus=1):
        self.gpus = gpus
        self.consultas = 0

    def get_cuda_device_count(self):
        self.consultas += 1
        return self.gpus


@pytest.fixture
def ct2(monkeypatch):
    falso = CTranslate2Falso()
    monkeypatch.setattr(transcriber, "ctranslate2", falso)
    return falso


@pytest.fixture
def modelo(monkeypatch, ct2):
    WhisperModelFalso.instancias = []
    monkeypatch.setattr(transcriber, "WhisperModel", WhisperModelFalso)
    return WhisperModelFalso


def test_carga_el_modelo_en_gpu_y_lo_calienta(modelo):
    t = Transcriber("small", "en")
    assert t.device == "cuda"
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
    assert modelo.instancias[0].nombre == "medium" and t.model_name == "medium" and t.language == "es"


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


def fallar_en(monkeypatch, dispositivo):
    """WhisperModel lanza RuntimeError al crearse en `dispositivo`."""
    original = WhisperModelFalso.__init__

    def init(self, nombre, **kwargs):
        if kwargs.get("device") == dispositivo:
            raise RuntimeError("CUDA driver roto")
        original(self, nombre, **kwargs)

    monkeypatch.setattr(WhisperModelFalso, "__init__", init)


class TestDispositivo:
    def test_cpu_no_consulta_cuda_y_pasa_hilos(self, modelo, ct2):
        t = Transcriber("small", "es", device="cpu", cpu_threads=4)
        (falso,) = modelo.instancias
        assert falso.kwargs == {"device": "cpu", "compute_type": "int8", "cpu_threads": 4}
        assert t.device == "cpu" and ct2.consultas == 0

    def test_cpu_con_cero_hilos_no_pasa_cpu_threads(self, modelo):
        Transcriber("small", "es", device="cpu")
        assert modelo.instancias[0].kwargs == {"device": "cpu", "compute_type": "int8"}

    def test_cuda_no_pasa_cpu_threads(self, modelo):
        Transcriber("small", "es", device="cuda", cpu_threads=4)
        assert modelo.instancias[0].kwargs == {"device": "cuda", "compute_type": "int8"}

    def test_cuda_con_fallo_propaga_y_no_reintenta(self, modelo, monkeypatch):
        fallar_en(monkeypatch, "cuda")
        with pytest.raises(RuntimeError, match="driver roto"):
            Transcriber("small", "es", device="cuda")
        assert modelo.instancias == []

    def test_auto_sin_gpu_usa_cpu(self, modelo, ct2, caplog):
        ct2.gpus = 0
        with caplog.at_level("WARNING", logger="speechflow"):
            t = Transcriber("small", "es", cpu_threads=2)
        assert t.device == "cpu"
        assert modelo.instancias[0].kwargs == {"device": "cpu", "compute_type": "int8", "cpu_threads": 2}
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_auto_con_gpu_usa_cuda(self, modelo):
        t = Transcriber("small", "es")
        assert t.device == "cuda" and modelo.instancias[0].kwargs["device"] == "cuda"

    def test_auto_con_fallo_de_carga_reintenta_en_cpu(self, modelo, monkeypatch, caplog):
        fallar_en(monkeypatch, "cuda")
        with caplog.at_level("WARNING", logger="speechflow"):
            t = Transcriber("small", "es", cpu_threads=3)
        assert t.device == "cpu"
        assert modelo.instancias[0].kwargs == {"device": "cpu", "compute_type": "int8", "cpu_threads": 3}
        assert any("driver roto" in r.getMessage() and r.levelname == "WARNING" for r in caplog.records)

    def test_auto_con_fallo_de_calentamiento_reintenta_en_cpu(self, modelo, monkeypatch):
        original = WhisperModelFalso.transcribe

        def transcribe(self, audio, **kwargs):
            if self.kwargs["device"] == "cuda":
                raise RuntimeError("cuBLAS no disponible")
            return original(self, audio, **kwargs)

        monkeypatch.setattr(WhisperModelFalso, "transcribe", transcribe)
        t = Transcriber("small", "es")
        assert t.device == "cpu" and modelo.instancias[-1].kwargs["device"] == "cpu"

    def test_cpu_sin_modelo_carga_small_con_info(self, modelo, caplog):
        with caplog.at_level("INFO", logger="speechflow"):
            t = Transcriber(device="cpu")
        assert modelo.instancias[0].nombre == "small" and t.model_name == "small"
        assert any("Modelo no fijado: se usa small por defecto en CPU." in r.getMessage() for r in caplog.records)

    def test_cuda_sin_modelo_carga_medium(self, modelo):
        t = Transcriber(device="cuda")
        assert modelo.instancias[0].nombre == "medium" and t.model_name == "medium"

    def test_auto_sin_gpu_y_sin_modelo_carga_small(self, modelo, ct2):
        ct2.gpus = 0
        t = Transcriber()
        assert modelo.instancias[0].nombre == "small" and t.model_name == "small"

    def test_auto_con_gpu_y_sin_modelo_carga_medium(self, modelo):
        t = Transcriber()
        assert t.device == "cuda" and t.model_name == "medium" and modelo.instancias[0].nombre == "medium"

    def test_auto_con_fallo_de_gpu_y_sin_modelo_reintenta_con_small(self, modelo, monkeypatch):
        fallar_en(monkeypatch, "cuda")
        t = Transcriber()
        assert t.device == "cpu" and t.model_name == "small" and modelo.instancias[-1].nombre == "small"

    def test_modelo_explicito_se_respeta_en_cpu_sin_info(self, modelo, caplog):
        with caplog.at_level("INFO", logger="speechflow"):
            t = Transcriber("medium", device="cpu")
        assert modelo.instancias[0].nombre == "medium" and t.model_name == "medium"
        assert not any("Modelo no fijado" in r.getMessage() for r in caplog.records)

    def test_modelo_explicito_se_respeta_en_el_reintento_de_auto(self, modelo, monkeypatch):
        fallar_en(monkeypatch, "cuda")
        t = Transcriber("medium")
        assert t.device == "cpu" and t.model_name == "medium" and modelo.instancias[-1].nombre == "medium"

    @pytest.mark.parametrize("device", ["auto", "cpu", "cuda"])
    def test_model_name_nunca_es_none(self, modelo, device):
        assert isinstance(Transcriber(device=device).model_name, str)

    @pytest.mark.parametrize("device", ["auto", "cpu", "cuda"])
    def test_device_nunca_es_auto(self, modelo, device):
        assert Transcriber("small", "es", device=device).device in ("cpu", "cuda")
