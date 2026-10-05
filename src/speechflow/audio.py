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


def input_devices() -> list[int]:
    """Índices de los dispositivos con entrada, en orden."""
    return [index for index, device in enumerate(sd.query_devices()) if device["max_input_channels"] > 0]


def refresh_devices() -> None:
    """Reinicializa PortAudio para ver dispositivos conectados o desconectados. Solo sin streams abiertos."""
    sd._terminate()
    sd._initialize()


def device_index(device: int | str | None) -> int | None:
    """Índice real de un dispositivo de entrada (entero, nombre o None = defecto); None si no se resuelve."""
    try:
        info = sd.query_devices(device, "input")
    except (sd.PortAudioError, ValueError):
        return None
    index = info.get("index")
    if index is None:
        index = device if isinstance(device, int) else next(
            (i for i, candidate in enumerate(sd.query_devices()) if candidate["name"] == info["name"]), None
        )
    return index


def device_name(device: int | str | None) -> str | None:
    """Nombre de un dispositivo de entrada (entero, nombre o None = defecto); None si no se resuelve."""
    try:
        return sd.query_devices(device, "input")["name"]
    except (sd.PortAudioError, ValueError):
        return None


def input_device_by_name(name: str) -> int | None:
    """Índice del primer dispositivo de entrada cuyo nombre es exactamente `name`; None si no hay."""
    for index in input_devices():
        if sd.query_devices(index)["name"] == name:
            return index
    return None


def next_input_device(current: int | str | None) -> int | None:
    """Siguiente dispositivo de entrada tras `current`, con vuelta al principio; None si no hay ninguno."""
    devices = input_devices()
    if not devices:
        return None
    index = device_index(current)
    if index not in devices:
        return devices[0]
    return devices[(devices.index(index) + 1) % len(devices)]


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

    @property
    def active(self) -> bool:
        """True si hay un InputStream abierto y activo."""
        return self._stream is not None and self._stream.active

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
        """Cierra el stream y devuelve int16 mono a SAMPLE_RATE; tolera un stream caído."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except sd.PortAudioError:
                pass
            self._stream = None
        audio = np.concatenate(self._chunks) if self._chunks else np.zeros((0, CHANNELS), dtype=DTYPE)
        self._chunks = []
        return resample(audio, self._source_rate)
