"""Transcripción de audio con faster-whisper: carga el modelo una vez y transcribe muchas."""
import gc
import time

import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000  # Hz, nativo de Whisper
COMPUTE_TYPE = "int8"
DEFAULT_MODEL = "medium"
DEFAULT_LANGUAGE = "es"


class Transcriber:
    def __init__(
        self, model_name: str = DEFAULT_MODEL, language: str = DEFAULT_LANGUAGE, vad: bool = True
    ) -> None:
        """Carga el modelo (GPU, int8) y lo calienta; el idioma y el filtro VAD quedan fijos."""
        self.language = language
        self.vad = vad
        self._model = WhisperModel(model_name, device="cuda", compute_type=COMPUTE_TYPE)
        list(self._model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language=language)[0])  # calentamiento del decodificador
        if vad:  # carga Silero ahora y no en el primer dictado
            list(self._model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language=language, vad_filter=True)[0])

    def transcribe(self, audio: np.ndarray) -> tuple[str, float]:
        """Transcribe int16 mono a SAMPLE_RATE; devuelve (texto, segundos), sin contar carga ni calentamiento."""
        if len(audio) == 0:
            return "", 0.0
        samples = audio.reshape(-1).astype(np.float32) / 32768
        start = time.perf_counter()
        segments, _info = self._model.transcribe(samples, language=self.language, vad_filter=self.vad)
        text = " ".join(segment.text.strip() for segment in segments)
        return text, time.perf_counter() - start

    def close(self) -> None:
        """Suelta el modelo y fuerza la recolección para liberar la GPU; idempotente."""
        self._model = None
        gc.collect()
