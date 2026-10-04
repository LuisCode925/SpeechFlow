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
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sounddevice as sd
from pynput import keyboard

from speechflow.audio import PREFERRED_DEVICE, Recorder, default_device, list_devices, parse_device
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
    """Ciclo de la tecla global: pulsar graba, soltar para. Los callbacks corren en el hilo del listener."""

    def __init__(self, key: keyboard.Key | keyboard.KeyCode, device: int | str | None) -> None:
        self.key = key
        self.recorder = Recorder(device)
        self.state = State.IDLE
        self._held = False  # la tecla sigue pulsada; filtra las repeticiones automáticas
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
        print("Grabando...")
        notify("SpeechFlow", "Grabando...")

    def on_release(self, key) -> None:
        if key != self.key:
            return
        with self._lock:
            self._held = False
            if self.state is not State.RECORDING:
                return
            audio = self.recorder.stop()
            self.state = State.IDLE
        print(f"Grabación terminada: {len(audio) / SAMPLE_RATE:.2f} s")


def parse_key(name: str) -> keyboard.Key | keyboard.KeyCode:
    """Convierte un nombre de pynput.keyboard.Key (p. ej. 'ctrl_r', 'f9') o un carácter suelto en una tecla."""
    if len(name) == 1:
        return keyboard.KeyCode.from_char(name)
    try:
        return keyboard.Key[name]
    except KeyError:
        raise ValueError(f"tecla desconocida {name!r}; usa un nombre de pynput.keyboard.Key (ctrl_r, f9, ...) o un carácter") from None


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

    if shutil.which("xdotool") is None:
        sys.exit("Falta xdotool. Instálalo con: sudo apt install xdotool")
    if os.environ.get("XDG_SESSION_TYPE", "x11") != "x11":
        print(f"Aviso: la sesión es {os.environ['XDG_SESSION_TYPE']!r}, no x11; la tecla global y xdotool pueden no funcionar.", file=sys.stderr)
    if shutil.which("notify-send") is None:
        print("Aviso: falta notify-send (sudo apt install libnotify-bin); solo habrá mensajes por consola.", file=sys.stderr)

    try:
        key = parse_key(args.key)
    except ValueError as error:
        sys.exit(f"Error con --key: {error}")

    device = args.device if args.device is not None else default_device()
    try:
        sd.query_devices(device, "input")
    except (sd.PortAudioError, ValueError) as error:
        sys.exit(f"Error con el dispositivo de entrada {device!r}: {error}")

    print(f"Cargando {args.model} ({COMPUTE_TYPE}, GPU)...")
    transcriber = Transcriber(args.model, args.language)
    print(f"Listo. Mantén pulsada la tecla {args.key!r} para dictar. Ctrl+C para salir.")

    push_to_talk = PushToTalk(key, device)
    try:
        with keyboard.Listener(on_press=push_to_talk.on_press, on_release=push_to_talk.on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\nSaliendo.")


if __name__ == "__main__":
    main()
