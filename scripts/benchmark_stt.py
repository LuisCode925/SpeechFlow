"""Benchmark de faster-whisper en GPU: carga de modelo y latencia de transcripción."""
import argparse
import sys
import time
from pathlib import Path

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

SAMPLE_RATE = 16000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path, help="archivo de audio a transcribir")
    parser.add_argument("--model", default="small", help="small | medium")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--language", default=None, help="es | en (por defecto, autodetección)")
    args = parser.parse_args()

    if not args.wav.is_file():
        print(f"No existe {args.wav}. Coloca WAV de prueba en benchmarks/samples/.", file=sys.stderr)
        return 1

    audio = decode_audio(str(args.wav), sampling_rate=SAMPLE_RATE)
    audio_seconds = len(audio) / SAMPLE_RATE

    t0 = time.perf_counter()
    model = WhisperModel(args.model, device="cuda", compute_type=args.compute_type)
    load_seconds = time.perf_counter() - t0

    t0 = time.perf_counter()
    segments, _info = model.transcribe(audio, language=args.language)
    text = " ".join(s.text.strip() for s in segments)
    transcribe_seconds = time.perf_counter() - t0

    print(f"model={args.model} compute_type={args.compute_type} sample={args.wav.name}")
    print(f"audio_seconds={audio_seconds:.1f} load_seconds={load_seconds:.2f} transcribe_seconds={transcribe_seconds:.2f}")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
