"""Push-to-talk global (X11): mantén pulsada una tecla para dictar y suéltala para escribir el texto.

Graba mientras la tecla está pulsada, transcribe con faster-whisper al soltar y escribe el
resultado en la ventana con foco. Termina con Ctrl+C. `--list-devices` muestra los
dispositivos de entrada disponibles.
"""
import argparse
import os
import shutil
import sys
import threading
import time
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sounddevice as sd
from pynput import keyboard

from speechflow.audio import PREFERRED_DEVICE, Recorder, default_device, list_devices, parse_device
from speechflow.inserter import insert_text
from speechflow.log import setup_logging
from speechflow.notifier import notify
from speechflow.transcriber import COMPUTE_TYPE, DEFAULT_LANGUAGE, DEFAULT_MODEL, SAMPLE_RATE, Transcriber

DEFAULT_KEY = "ctrl_r"  # nombre de pynput.keyboard.Key, o un carácter suelto
MIN_SECONDS = 0.5  # por debajo no se transcribe ni se escribe nada
MAX_SECONDS = 60.0  # la grabación se corta sola


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class PushToTalk:
    """Ciclo de la tecla global: pulsar graba, soltar transcribe e inserta. Los callbacks corren en el hilo del listener."""

    def __init__(self, key: keyboard.Key | keyboard.KeyCode, device: int | str | None, transcriber: Transcriber) -> None:
        self.key = key
        self.recorder = Recorder(device)
        self.transcriber = transcriber
        self.state = State.IDLE
        self._held = False  # la tecla sigue pulsada; filtra las repeticiones automáticas
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_press(self, key) -> None:
        if key != self.key:
            return
        with self._lock:
            was_held, self._held = self._held, True
            if was_held or self.state is not State.IDLE:
                return
            try:
                self.recorder.start()
            except (sd.PortAudioError, ValueError) as error:
                print(f"Error al abrir el micrófono: {error}", file=sys.stderr)
                notify("SpeechFlow", f"Error al abrir el micrófono: {error}")
                return
            self.state = State.RECORDING
            self._timer = threading.Timer(MAX_SECONDS, self._stop_recording, args=(True,))
            self._timer.daemon = True
            self._timer.start()
        print("Grabando...")

    def on_release(self, key) -> None:
        if key != self.key:
            return
        with self._lock:
            self._held = False
        self._stop_recording(False)

    def _stop_recording(self, timed_out: bool) -> None:
        """Detiene la grabación (al soltar o por el temporizador); descarta lo corto o lanza la transcripción."""
        with self._lock:
            if self.state is not State.RECORDING:
                return
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            audio = self.recorder.stop()
            seconds = len(audio) / SAMPLE_RATE
            if seconds < MIN_SECONDS:
                self.state = State.IDLE
                print(f"Grabación de {seconds:.2f} s descartada (mínimo {MIN_SECONDS} s).")
                return
            self.state = State.TRANSCRIBING
        if timed_out:
            print(f"Límite de {MAX_SECONDS:.0f} s alcanzado; suelta la tecla y vuelve a pulsarla para otro dictado.")
        print(f"Grabación terminada: {seconds:.2f} s. Transcribiendo...")
        threading.Thread(target=self._transcribe_and_insert, args=(audio,), daemon=True).start()

    def _transcribe_and_insert(self, audio) -> None:
        try:
            text, seconds = self.transcriber.transcribe(audio)
            if not text:
                print("Sin texto reconocido.")
                return
            insert_text(text)
            print(f"Insertado ({seconds:.2f} s): {text}")
        except Exception as error:
            print(f"Error: {error}", file=sys.stderr)
            notify("SpeechFlow", f"Error: {error}")
        finally:
            with self._lock:
                self.state = State.IDLE


def parse_key(name: str) -> keyboard.Key | keyboard.KeyCode:
    """Convierte un nombre de pynput.keyboard.Key (p. ej. 'ctrl_r', 'f9') o un carácter suelto en una tecla."""
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    try:
        return keyboard.Key[name]
    except KeyError:
        raise ValueError(f"tecla desconocida {name!r}; usa un nombre de pynput.keyboard.Key (ctrl_r, f9, ...) o un carácter") from None


def describe_device(device: int | str | None) -> str:
    """Texto `[índice] nombre | tasa Hz nativos a SAMPLE_RATE Hz mono` del dispositivo de entrada."""
    info = sd.query_devices(device, "input")
    index = info.get("index")
    if index is None:
        index = device if isinstance(device, int) else next(
            (i for i, candidate in enumerate(sd.query_devices()) if candidate["name"] == info["name"]), "?"
        )
    return f"[{index}] {info['name']} | {int(info['default_samplerate'])} Hz nativos a {SAMPLE_RATE} Hz mono"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true", help="lista los dispositivos de entrada y termina")
    parser.add_argument("--device", type=parse_device, help=f"índice o nombre del dispositivo de entrada (defecto: el que contenga '{PREFERRED_DEVICE}', si no el del sistema)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="modelo de faster-whisper (defecto: %(default)s)")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="idioma de la transcripción (defecto: %(default)s)")
    parser.add_argument("--key", default=DEFAULT_KEY, help="tecla de disparo, nombre de pynput.keyboard.Key o un carácter (defecto: %(default)s)")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    logger = setup_logging()

    if shutil.which("xdotool") is None:
        logger.error("Falta xdotool. Instálalo con: sudo apt install xdotool")
        sys.exit(1)
    if os.environ.get("XDG_SESSION_TYPE", "x11") != "x11":
        logger.warning(f"Aviso: la sesión es {os.environ['XDG_SESSION_TYPE']!r}, no x11; la tecla global y xdotool pueden no funcionar.")
    if shutil.which("notify-send") is None:
        logger.warning("Aviso: falta notify-send (sudo apt install libnotify-bin); solo habrá mensajes por consola.")

    try:
        key = parse_key(args.key)
    except ValueError as error:
        logger.error(f"Error con --key: {error}")
        sys.exit(1)

    device = args.device if args.device is not None else default_device()
    try:
        sd.query_devices(device, "input")
    except (sd.PortAudioError, ValueError) as error:
        logger.error(f"Error con el dispositivo de entrada {device!r}: {error}")
        sys.exit(1)

    logger.info(f"Cargando {args.model} ({COMPUTE_TYPE}, GPU)...")
    notify("SpeechFlow", f"Cargando {args.model}...")
    started = time.perf_counter()
    transcriber = Transcriber(args.model, args.language)
    load_seconds = time.perf_counter() - started
    notify("SpeechFlow", f"Modelo {args.model} cargado")
    logger.info(f"Modelo: {args.model} | idioma: {args.language} | compute_type: {COMPUTE_TYPE} | GPU")
    logger.info(f"Modelo cargado en {load_seconds:.2f} s (incluye calentamiento)")
    logger.info(f"Dispositivo de audio: {describe_device(device)}")
    logger.info(f"Listo. Mantén pulsada la tecla {args.key!r} para dictar. Ctrl+C para salir.")

    push_to_talk = PushToTalk(key, device, transcriber)
    try:
        with keyboard.Listener(on_press=push_to_talk.on_press, on_release=push_to_talk.on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\nSaliendo.")
        transcriber.close()
        notify("SpeechFlow", "Modelo liberado")


if __name__ == "__main__":
    main()
