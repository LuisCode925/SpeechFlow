"""Prueba de captura del micrófono: graba entre dos Enter y guarda un WAV mono 16 kHz.

Tras grabar, mide el audio y lo transcribe con faster-whisper (int8, GPU).
`--list-devices` muestra los dispositivos de entrada disponibles.
"""
import argparse
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import sounddevice as sd
from math import gcd
from scipy.signal import resample_poly

from speechflow.transcriber import COMPUTE_TYPE, DEFAULT_LANGUAGE, DEFAULT_MODEL, SAMPLE_RATE, Transcriber

PREFERRED_DEVICE = "Realtek"
MIN_PEAK = 0.01  # por debajo se avisa de un posible micrófono mudo o equivocado
CHANNELS = 1
DTYPE = "int16"
DEFAULT_OUTPUT = Path("benchmarks/captures/capture.wav")


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


def record(device: int | str | None) -> np.ndarray:
    """Graba a la tasa nativa del dispositivo entre dos Enter; devuelve int16 mono a SAMPLE_RATE."""
    chunks = []
    source_rate = int(sd.query_devices(device, "input")["default_samplerate"])

    def callback(indata, frames, time_info, status):
        if status:
            print(status, file=sys.stderr)
        chunks.append(indata.copy())

    with sd.InputStream(
        samplerate=source_rate, channels=CHANNELS, dtype=DTYPE, device=device, callback=callback
    ):
        input("Pulsa Enter para empezar a grabar...")
        chunks.clear()
        print("Grabando... pulsa Enter para parar.")
        input()
    audio = np.concatenate(chunks) if chunks else np.zeros((0, CHANNELS), dtype=DTYPE)
    return resample(audio, source_rate)


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true", help="lista los dispositivos de entrada y termina")
    parser.add_argument("--device", type=parse_device, help=f"índice o nombre del dispositivo de entrada (defecto: el que contenga '{PREFERRED_DEVICE}', si no el del sistema)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="modelo de faster-whisper (defecto: %(default)s)")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="idioma de la transcripción (defecto: %(default)s)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="WAV de salida (defecto: %(default)s)")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    device = args.device if args.device is not None else default_device()
    try:
        audio = record(device)
    except (sd.PortAudioError, ValueError) as error:
        sys.exit(f"Error con el dispositivo de entrada {device!r}: {error}")
    save_wav(args.output, audio)
    print(f"Guardado {args.output}")
    seconds, peak, rms = measure(audio)
    print(f"Duración: {seconds:.2f} s | Pico: {peak:.3f} | RMS: {rms:.4f}")
    if peak < MIN_PEAK:
        print(
            f"Aviso: pico {peak:.4f} < {MIN_PEAK}; posible micrófono mudo o dispositivo equivocado (usa --list-devices).",
            file=sys.stderr,
        )
    if len(audio) == 0:
        return
    print(f"Transcribiendo con {args.model} ({COMPUTE_TYPE}, GPU)...")
    transcriber = Transcriber(args.model, args.language)
    text, seconds = transcriber.transcribe(audio)
    print(f"Transcripción ({seconds:.2f} s): {text}")


if __name__ == "__main__":
    main()
