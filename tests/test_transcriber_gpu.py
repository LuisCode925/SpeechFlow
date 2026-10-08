"""Smoke test con el modelo real; requiere GPU CUDA y el modelo `medium` en la caché de Hugging Face."""
import numpy as np
import pytest

from speechflow.transcriber import SAMPLE_RATE, Transcriber

pytestmark = pytest.mark.gpu


def test_carga_transcribe_silencio_y_cierra():
    t = Transcriber()
    try:
        texto, segundos = t.transcribe(np.zeros(SAMPLE_RATE, dtype=np.int16))
        assert isinstance(texto, str) and segundos >= 0.0
    finally:
        t.close()
        t.close()
