"""Prueba de captura del micrófono: graba entre dos Enter y guarda un WAV mono 16 kHz.

Tras grabar, mide el audio y lo transcribe con faster-whisper (int8, GPU).
`--list-devices` muestra los dispositivos de entrada disponibles.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sounddevice as sd

from speechflow.audio import PREFERRED_DEVICE, Recorder, default_device, list_devices, measure, parse_device, save_wav
from speechflow.transcriber import COMPUTE_TYPE, DEFAULT_LANGUAGE, DEFAULT_MODEL, Transcriber

MIN_PEAK = 0.01  # por debajo se avisa de un posible micrófono mudo o equivocado
DEFAULT_OUTPUT = Path("benchmarks/captures/capture.wav")


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
        recorder = Recorder(device)
        input("Pulsa Enter para empezar a grabar...")
        recorder.start()
        print("Grabando... pulsa Enter para parar.")
        input()
        audio = recorder.stop()
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
