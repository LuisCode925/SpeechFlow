"""Transcripción de audio con faster-whisper: carga el modelo una vez y transcribe muchas."""
import gc
import time

import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000  # Hz, nativo de Whisper
COMPUTE_TYPE = "int8"
DEFAULT_MODEL = "medium"
DEFAULT_LANGUAGE = "es"
AUTO_LANGUAGE = "auto"  # idioma especial: detecta entre AUTO_CANDIDATES en cada dictado
AUTO_CANDIDATES = ("es", "en")


class Transcriber:
    def __init__(
        self, model_name: str = DEFAULT_MODEL, language: str = DEFAULT_LANGUAGE, vad: bool = True
    ) -> None:
        """Carga el modelo (GPU, int8) y lo calienta; `language` es el idioma por defecto de transcribe()."""
        self.language = language
        self.vad = vad
        self.last_language: str | None = None  # idioma usado en la última llamada a transcribe()
        self._model = WhisperModel(model_name, device="cuda", compute_type=COMPUTE_TYPE)
        silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
        warm_language = self._fallback_language()  # "auto" no es un idioma de Whisper
        list(self._model.transcribe(silence, language=warm_language)[0])  # calentamiento del decodificador
        if vad:  # carga Silero ahora y no en el primer dictado
            list(self._model.transcribe(silence, language=warm_language, vad_filter=True)[0])
        self._model.detect_language(silence)  # calentamiento del detector, para activar auto en caliente

    def _fallback_language(self) -> str:
        """Idioma fijo del Transcriber, o DEFAULT_LANGUAGE si está en auto."""
        return DEFAULT_LANGUAGE if self.language == AUTO_LANGUAGE else self.language

    def _detect(self, samples: np.ndarray) -> str:
        """Elige entre AUTO_CANDIDATES el de mayor probabilidad; si la detección falla, el idioma fijo."""
        fallback = self._fallback_language()
        if fallback not in AUTO_CANDIDATES:
            fallback = DEFAULT_LANGUAGE
        try:
            probabilities = dict(self._model.detect_language(samples)[2])
            candidates = {lang: probabilities[lang] for lang in AUTO_CANDIDATES if lang in probabilities}
        except Exception:  # audio sin voz u otro fallo del detector: sigue el camino normal
            return fallback
        return max(candidates, key=candidates.__getitem__) if candidates else fallback

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> tuple[str, float]:
        """Transcribe int16 mono a SAMPLE_RATE; devuelve (texto, segundos), sin contar carga ni calentamiento.

        `language` None usa self.language; "auto" detecta entre es y en (los segundos incluyen la detección).
        El idioma realmente usado queda en `last_language`.
        """
        language = self.language if language is None else language
        if len(audio) == 0:
            self.last_language = self._fallback_language() if language == AUTO_LANGUAGE else language
            return "", 0.0
        samples = audio.reshape(-1).astype(np.float32) / 32768
        start = time.perf_counter()
        if language == AUTO_LANGUAGE:
            language = self._detect(samples)
        self.last_language = language
        segments, _info = self._model.transcribe(samples, language=language, vad_filter=self.vad)
        text = " ".join(segment.text.strip() for segment in segments)
        return text, time.perf_counter() - start

    def close(self) -> None:
        """Suelta el modelo y fuerza la recolección para liberar la GPU; idempotente."""
        self._model = None
        gc.collect()
