"""Benchmark de faster-whisper en GPU: carga de modelo, latencia y VRAM.

Sin argumentos recorre `small` y `medium` en int8 sobre los primeros WAV de
benchmarks/samples/ (de hasta 30 s) y escribe benchmarks/results.md.
"""
import argparse
import gc
import statistics
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

SAMPLE_RATE = 16000
SAMPLES_DIR = Path("benchmarks/samples")
RESULTS_PATH = Path("benchmarks/results.md")
MAX_SAMPLE_SECONDS = 30
TARGET_SECONDS_PER_10S = 2.0
VRAM_LIMIT_MB = 6144


def vram_used_mb() -> int:
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], text=True
    )
    return int(out.splitlines()[0])


class VramPeak:
    """Mide el pico de VRAM usada (nvidia-smi) mientras el bloque `with` está activo."""

    def __enter__(self):
        self.peak = vram_used_mb()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return self

    def _poll(self):
        while not self._stop.is_set():
            self.peak = max(self.peak, vram_used_mb())
            time.sleep(0.1)

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self.peak = max(self.peak, vram_used_mb())


def load_samples(paths, limit):
    if not paths:
        paths = sorted(SAMPLES_DIR.glob("*.wav"))
    samples = []
    for path in paths:
        if not path.is_file():
            continue
        audio = decode_audio(str(path), sampling_rate=SAMPLE_RATE)
        if len(audio) / SAMPLE_RATE <= MAX_SAMPLE_SECONDS:
            samples.append((path.name, audio))
        if len(samples) == limit:
            break
    return samples


def run_model(model_name, compute_type, samples, language):
    baseline_mb = vram_used_mb()
    rows = []
    with VramPeak() as vram:
        t0 = time.perf_counter()
        model = WhisperModel(model_name, device="cuda", compute_type=compute_type)
        load_seconds = time.perf_counter() - t0

        # Calentamiento: la primera inferencia en CUDA es más lenta y no se mide.
        list(model.transcribe(samples[0][1], language=language)[0])

        for name, audio in samples:
            t0 = time.perf_counter()
            segments, _info = model.transcribe(audio, language=language)
            text = " ".join(s.text.strip() for s in segments)
            rows.append({
                "model": model_name,
                "compute_type": compute_type,
                "sample": name,
                "audio_seconds": len(audio) / SAMPLE_RATE,
                "load_seconds": load_seconds,
                "transcribe_seconds": time.perf_counter() - t0,
                "text": text,
            })
    for row in rows:
        row["vram_mb"] = vram.peak - baseline_mb
    del model
    gc.collect()
    return rows


def pick_default(rows, models):
    """Prefiere el modelo más grande que cumpla latencia (por 10 s de audio) y VRAM."""
    for model_name in reversed(models):
        mine = [r for r in rows if r["model"] == model_name]
        per_10s = statistics.median(r["transcribe_seconds"] / r["audio_seconds"] * 10 for r in mine)
        if per_10s < TARGET_SECONDS_PER_10S and max(r["vram_mb"] for r in mine) < VRAM_LIMIT_MB:
            return model_name
    return None


def write_results(rows, models, default, language):
    gpu = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"], text=True
    ).strip()
    lines = [
        "# Resultados del benchmark de STT",
        "",
        f"- Fecha: {date.today().isoformat()}",
        f"- GPU: {gpu}",
        f"- Idioma fijado: `{language}` (sin muestras en inglés todavía)",
        f"- Objetivo: < {TARGET_SECONDS_PER_10S:g} s por cada 10 s de audio, VRAM < {VRAM_LIMIT_MB} MB",
        "- `load_seconds` puede incluir la descarga del modelo en la primera ejecución.",
        "",
        "| Modelo | Compute | Muestra | Audio (s) | Carga (s) | Transcripción (s) | VRAM pico (MB) |",
        "| ------ | ------- | ------- | --------- | --------- | ----------------- | -------------- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['model']} | {r['compute_type']} | {r['sample']} | {r['audio_seconds']:.1f} "
            f"| {r['load_seconds']:.2f} | {r['transcribe_seconds']:.2f} | {r['vram_mb']} |"
        )
    lines += ["", "## Mediana por modelo (transcripción normalizada a 10 s de audio)", ""]
    for model_name in models:
        mine = [r for r in rows if r["model"] == model_name]
        per_10s = statistics.median(r["transcribe_seconds"] / r["audio_seconds"] * 10 for r in mine)
        lines.append(f"- `{model_name}`: {per_10s:.2f} s, VRAM pico {max(r['vram_mb'] for r in mine)} MB")
    lines += ["", "## Modelo por defecto para la siguiente spec", ""]
    if default:
        lines.append(f"**`{default}` int8**: el modelo más grande que cumple latencia y VRAM.")
    else:
        lines.append("**Ninguno** cumple el objetivo de latencia en esta GPU.")
    lines += ["", "## Transcripciones", ""]
    for r in rows:
        lines.append(f"- `{r['model']}` / `{r['sample']}`: {r['text']}")
    RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", nargs="*", type=Path, help="audios (por defecto benchmarks/samples/*.wav)")
    parser.add_argument("--models", nargs="+", default=["small", "medium"])
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--language", default="es", help="es | en")
    parser.add_argument("--max-samples", type=int, default=5)
    args = parser.parse_args()

    samples = load_samples(args.wav, args.max_samples)
    if not samples:
        print(
            f"No hay audios válidos en {SAMPLES_DIR}/. Coloca WAV de hasta {MAX_SAMPLE_SECONDS} s "
            "(idealmente mono 16 kHz).",
            file=sys.stderr,
        )
        return 1

    rows = []
    for model_name in args.models:
        print(f"Probando {model_name} {args.compute_type} con {len(samples)} muestras...")
        rows += run_model(model_name, args.compute_type, samples, args.language)

    default = pick_default(rows, args.models)
    write_results(rows, args.models, default, args.language)
    print(f"Resultados en {RESULTS_PATH} (modelo por defecto: {default or 'ninguno'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
