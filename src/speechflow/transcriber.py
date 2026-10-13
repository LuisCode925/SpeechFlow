"""Transcripción de audio con faster-whisper: carga el modelo una vez y transcribe muchas."""
import gc
import logging
import time

import ctranslate2
import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger("speechflow")

SAMPLE_RATE = 16000  # Hz, nativo de Whisper
COMPUTE_TYPE = "int8"
DEFAULT_MODEL = "medium"  # defecto en GPU
DEFAULT_CPU_MODEL = "small"  # defecto en CPU
DEFAULT_LANGUAGE = "es"
AUTO_LANGUAGE = "auto"  # idioma especial: detecta entre AUTO_CANDIDATES en cada dictado
AUTO_CANDIDATES = ("es", "en")


class Transcriber:
    def __init__(
        self,
        model_name: str | None = None,
        language: str = DEFAULT_LANGUAGE,
        vad: bool = True,
        device: str = "auto",
        cpu_threads: int = 0,
        initial_prompt: str = "",
    ) -> None:
        """Carga el modelo (int8) y lo calienta; `language` es el idioma por defecto de transcribe().

        `device` "cpu" o "cuda" fuerza ese dispositivo (con "cuda" un fallo se propaga); "auto" usa la GPU si hay
        y funciona, y si no cae a CPU con un WARNING. `Transcriber.device` es el dispositivo realmente usado.
        `model_name` None = sin fijar: DEFAULT_MODEL en GPU y DEFAULT_CPU_MODEL en CPU (también en el reintento de
        "auto"); uno explícito se usa siempre. `Transcriber.model_name` es el modelo realmente cargado.
        """
        self.language = language
        self.vad = vad
        self.initial_prompt = initial_prompt  # contexto para Whisper en transcribe(); "" = sin prompt
        self.last_language: str | None = None  # idioma usado en la última llamada a transcribe()
        self._model = None
        if device == "auto":
            self.device = "cpu"
            if ctranslate2.get_cuda_device_count() == 0:
                logger.warning("No hay GPU CUDA visible: se usa la CPU.")
            else:
                try:
                    self._model = self._load(model_name or DEFAULT_MODEL, "cuda", cpu_threads)
                    self.model_name = model_name or DEFAULT_MODEL
                    self.device = "cuda"
                except Exception as e:
                    logger.warning("No se pudo cargar el modelo en la GPU (%s): se usa la CPU.", e)
                    self._model = None
                    gc.collect()  # libera lo que la GPU alcanzó a cargar antes de reintentar
            if self._model is None:
                self.model_name = self._resolve_cpu_model(model_name)
                self._model = self._load(self.model_name, "cpu", cpu_threads)
        else:
            self.model_name = self._resolve_cpu_model(model_name) if device == "cpu" else model_name or DEFAULT_MODEL
            self._model = self._load(self.model_name, device, cpu_threads)
            self.device = device

    @staticmethod
    def _resolve_cpu_model(model_name: str | None) -> str:
        """El modelo explícito, o DEFAULT_CPU_MODEL (con un INFO) si no está fijado."""
        if model_name is not None:
            return model_name
        logger.info("Modelo no fijado: se usa %s por defecto en CPU.", DEFAULT_CPU_MODEL)
        return DEFAULT_CPU_MODEL

    def _load(self, model_name: str, device: str, cpu_threads: int) -> WhisperModel:
        """Crea el WhisperModel en `device` y lo calienta."""
        kwargs = {"cpu_threads": cpu_threads} if device == "cpu" and cpu_threads > 0 else {}
        model = WhisperModel(model_name, device=device, compute_type=COMPUTE_TYPE, **kwargs)
        silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
        warm_language = self._fallback_language()  # "auto" no es un idioma de Whisper
        list(model.transcribe(silence, language=warm_language)[0])  # calentamiento del decodificador
        if self.vad:  # carga Silero ahora y no en el primer dictado
            list(model.transcribe(silence, language=warm_language, vad_filter=True)[0])
        model.detect_language(silence)  # calentamiento del detector, para activar auto en caliente
        return model

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
        segments, _info = self._model.transcribe(
            samples, language=language, vad_filter=self.vad, initial_prompt=self.initial_prompt or None
        )
        text = " ".join(segment.text.strip() for segment in segments)
        return text, time.perf_counter() - start

    def close(self) -> None:
        """Suelta el modelo y fuerza la recolección para liberar la GPU; idempotente."""
        self._model = None
        gc.collect()
