"""Captura de micrófono: dispositivos, remuestreo, medición, WAV y un Recorder start/stop."""
import sys
import wave
from math import gcd
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

from speechflow.transcriber import SAMPLE_RATE

PREFERRED_DEVICE = "Realtek"
CHANNELS = 1
DTYPE = "int16"


def list_devices() -> None:
    default_input = sd.default.device[0]
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            mark = ">" if index == default_input else " "
            print(f"{mark} {index:2d} {device['name']} ({device['max_input_channels']} canales de entrada)")


def parse_device(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def default_device() -> int | None:
    """Primer dispositivo de entrada cuyo nombre contiene PREFERRED_DEVICE; None = defecto del sistema."""
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0 and PREFERRED_DEVICE.lower() in device["name"].lower():
            return index
    return None


def resample(audio: np.ndarray, source_rate: int) -> np.ndarray:
    """Remuestrea int16 mono de `source_rate` a SAMPLE_RATE."""
    if source_rate == SAMPLE_RATE:
        return audio
    divisor = gcd(SAMPLE_RATE, source_rate)
    resampled = resample_poly(audio.astype(np.float32), SAMPLE_RATE // divisor, source_rate // divisor, axis=0)
    return np.clip(np.rint(resampled), -32768, 32767).astype(DTYPE)


def measure(audio: np.ndarray) -> tuple[float, float, float]:
    """Duración (s), pico y RMS (0.0–1.0) del audio int16."""
    if len(audio) == 0:
        return 0.0, 0.0, 0.0
    samples = audio.astype(np.float32) / 32768
    return len(audio) / SAMPLE_RATE, float(np.abs(samples).max()), float(np.sqrt(np.mean(samples**2)))


def save_wav(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(audio.tobytes())


class Recorder:
    def __init__(self, device: int | str | None = None) -> None:
        self.device = device
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._source_rate = SAMPLE_RATE

    def start(self) -> None:
        """Abre el InputStream a la tasa nativa del dispositivo y empieza a acumular."""
        self._chunks = []
        self._source_rate = int(sd.query_devices(self.device, "input")["default_samplerate"])

        def callback(indata, frames, time_info, status):
            if status:
                print(status, file=sys.stderr)
            self._chunks.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self._source_rate, channels=CHANNELS, dtype=DTYPE, device=self.device, callback=callback
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Cierra el stream y devuelve int16 mono a SAMPLE_RATE."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        audio = np.concatenate(self._chunks) if self._chunks else np.zeros((0, CHANNELS), dtype=DTYPE)
        self._chunks = []
        return resample(audio, self._source_rate)
