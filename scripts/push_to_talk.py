"""Push-to-talk global (X11): mantén pulsada una tecla para dictar y suéltala para escribir el texto.

Graba mientras la tecla está pulsada, transcribe con faster-whisper al soltar y escribe el
resultado en la ventana con foco. Termina con Ctrl+C. `--list-devices` muestra los
dispositivos de entrada disponibles. Una segunda tecla global (`--switch-key`, f8 por defecto)
cambia en caliente al siguiente dispositivo de entrada, solo con el script en reposo. El arranque
muestra un banner ASCII con las versiones de SpeechFlow y faster-whisper antes de cargar el modelo.

Las opciones (modelo, idioma, teclas, dispositivo, límites de grabación y notificaciones) se pueden
fijar en un archivo TOML: `--config RUTA`, si no `speechflow.toml` en la raíz del repo, si no
`~/.config/speechflow/config.toml` (ver `speechflow.example.toml`). Precedencia: CLI > micrófono
guardado con `--switch-key` en `.speechflow-state.toml` (solo el dispositivo) > archivo > defectos.
Sin archivo, o con uno inválido, se avisa, se crea la plantilla `speechflow.emergency.toml` y se usan
los defectos.
"""
import argparse
import logging
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

from speechflow.audio import PREFERRED_DEVICE, Recorder, default_device, device_index, device_name, input_device_by_name, list_devices, next_input_device, parse_device, refresh_devices
from speechflow.config import CONFIG_FILENAME, REPO_ROOT, STATE_FILENAME, USER_CONFIG_PATH, Config, ConfigError, find_config, load_config, load_state_device, save_state_device, write_emergency
from speechflow.inserter import insert_text
from speechflow.log import LOGGER_NAME, log_banner, setup_logging
from speechflow.notifier import notify, set_enabled
from speechflow.transcriber import COMPUTE_TYPE, SAMPLE_RATE, Transcriber

logger = logging.getLogger(LOGGER_NAME)


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


class PushToTalk:
    """Ciclo de la tecla global: pulsar graba, soltar transcribe e inserta. Los callbacks corren en el hilo del listener."""

    def __init__(
        self,
        key: keyboard.Key | keyboard.KeyCode,
        switch_key: keyboard.Key | keyboard.KeyCode,
        device: int | str | None,
        transcriber: Transcriber,
        model_name: str,
        min_seconds: float,
        max_seconds: float,
    ) -> None:
        self.key = key
        self.switch_key = switch_key
        self.model_name = model_name
        self.min_seconds = min_seconds  # por debajo no se transcribe ni se escribe nada
        self.max_seconds = max_seconds  # la grabación se corta sola
        self.recorder = Recorder(device)
        self.transcriber = transcriber
        self.state = State.IDLE
        self._held = False  # la tecla sigue pulsada; filtra las repeticiones automáticas
        self._switch_held = False  # ídem para la tecla de cambio
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._watched_name = device_name(device)  # micrófono vigilado, por nombre (los índices cambian al refrescar)
        self._device_missing = False  # True entre la alerta de desconexión y la reconexión
        self._stop_watcher = threading.Event()

    def on_press(self, key) -> None:
        if key == self.switch_key:
            with self._lock:
                was_held, self._switch_held = self._switch_held, True
            if not was_held:
                self.switch_device()
            return
        if key != self.key:
            return
        with self._lock:
            was_held, self._held = self._held, True
            if was_held or self.state is not State.IDLE:
                return
            if self._device_missing:
                logger.warning(f"El micrófono seleccionado no está conectado ({self._watched_name}); reconéctalo o pulsa la tecla de cambio para elegir otro.")
                return
            try:
                self.recorder.start()
            except (sd.PortAudioError, ValueError) as error:
                logger.error(f"Error al abrir el micrófono: {error}")
                notify("SpeechFlow", f"Error al abrir el micrófono: {error}")
                return
            self.state = State.RECORDING
            self._timer = threading.Timer(self.max_seconds, self._stop_recording, args=(True,))
            self._timer.daemon = True
            self._timer.start()
        logger.info("Grabando...")

    def on_release(self, key) -> None:
        if key == self.switch_key:
            with self._lock:
                self._switch_held = False
            return
        if key != self.key:
            return
        with self._lock:
            self._held = False
        self._stop_recording(False)

    def switch_device(self) -> None:
        """Pasa al siguiente dispositivo de entrada; solo en IDLE, nunca con un stream abierto."""
        with self._lock:
            if self.state is not State.IDLE:
                logger.warning("No se cambia la entrada de audio mientras se graba o se transcribe.")
                return
            try:
                previous = describe_device(self.recorder.device)
            except (sd.PortAudioError, ValueError):
                previous = repr(self.recorder.device)
            try:
                refresh_devices()
                new_device = next_input_device(self.recorder.device)
            except Exception as error:
                logger.error(f"Error al releer los dispositivos de audio: {error}; se mantiene {previous}.")
                return
            if new_device is None:
                logger.error(f"No hay dispositivos de entrada disponibles; se mantiene {previous}.")
                return
            if new_device == device_index(self.recorder.device) and not self._device_missing:
                logger.info(f"Solo hay un dispositivo de entrada: {describe_device(new_device)}")
                return
            self.recorder.device = new_device
            logger.info(f"Entrada de audio cambiada: {describe_device(new_device)}")
            name = sd.query_devices(new_device)["name"]
            self._watched_name = name
            self._device_missing = False
            notify("SpeechFlow", f"Entrada de audio: {name}")
            try:
                save_state_device(name)
            except OSError as error:
                logger.warning(f"No se pudo guardar la entrada de audio en {STATE_FILENAME}: {error}")

    def start_watcher(self, interval: float) -> None:
        """Lanza el hilo que comprueba cada `interval` s que el micrófono seleccionado sigue conectado."""
        threading.Thread(target=self._watch, args=(interval,), daemon=True).start()

    def stop_watcher(self) -> None:
        self._stop_watcher.set()

    def _watch(self, interval: float) -> None:
        """Avisa de la desconexión del micrófono; solo refresca PortAudio en IDLE y bajo el lock."""
        refresh_failed = False
        while not self._stop_watcher.wait(interval):
            with self._lock:
                if self.state is not State.IDLE or self._watched_name is None:
                    continue
                try:
                    refresh_devices()
                    index = input_device_by_name(self._watched_name)
                except Exception as error:
                    if not refresh_failed:
                        logger.error(f"Error al comprobar el micrófono: {error}")
                    refresh_failed = True
                    continue
                refresh_failed = False
                name = self._watched_name
                if index is None and not self._device_missing:
                    self._device_missing = True
                    event = "disconnected"
                elif index is not None and self._device_missing:
                    self._device_missing = False
                    self.recorder.device = index  # el índice puede haber cambiado al refrescar
                    event = "reconnected"
                else:
                    continue
            if event == "disconnected":
                logger.warning(f"El micrófono seleccionado se desconectó: {name}.")
                notify("SpeechFlow", f"Micrófono desconectado: {name}")
            else:
                logger.info(f"Micrófono reconectado: {describe_device(index)}")
                notify("SpeechFlow", f"Micrófono reconectado: {name}")

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
            if seconds < self.min_seconds:
                self.state = State.IDLE
                logger.info(f"Grabación de {seconds:.2f} s descartada (mínimo {self.min_seconds} s).")
                return
            self.state = State.TRANSCRIBING
        if timed_out:
            logger.warning(f"Límite de {self.max_seconds:g} s alcanzado; suelta la tecla y vuelve a pulsarla para otro dictado.")
        logger.info(f"Grabación terminada: {seconds:.2f} s. Transcribiendo con {self.model_name}/{self.transcriber.language}...")
        threading.Thread(target=self._transcribe_and_insert, args=(audio,), daemon=True).start()

    def _transcribe_and_insert(self, audio) -> None:
        try:
            text, seconds = self.transcriber.transcribe(audio)
            label = f"{self.model_name}/{self.transcriber.language}"
            if not text:
                logger.info(f"Sin texto reconocido ({seconds:.2f} s, {label}).")
                return
            insert_text(text)
            realtime = seconds / (len(audio) / SAMPLE_RATE)
            logger.info(f"Insertado ({seconds:.2f} s, {realtime:.2f}x tiempo real, {len(text)} caracteres, {label}): {text}")
        except Exception as error:
            logger.error(f"Error: {error}")
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
    index = device_index(device)
    if index is None:
        index = "?"
    return f"[{index}] {info['name']} | {int(info['default_samplerate'])} Hz nativos a {SAMPLE_RATE} Hz mono"


def resolve_config(explicit: Path | None) -> Config:
    """Carga la configuración de usuario; si falta o es inválida, avisa, deja la plantilla de emergencia y usa los defectos."""
    if explicit is not None and not explicit.is_file():
        logger.error(f"No existe el archivo de configuración {explicit}.")
        sys.exit(1)
    path = find_config(explicit)
    if path is not None:
        try:
            config = load_config(path)
        except ConfigError as error:
            problem = f"Configuración inválida en {path}: {error}."
        else:
            logger.info(f"Configuración: {path}")
            return config
    else:
        problem = f"No se encontró {CONFIG_FILENAME} ni {USER_CONFIG_PATH}."
    try:
        emergency = f"plantilla en {write_emergency(REPO_ROOT)}"
    except OSError as error:
        emergency = f"no se pudo crear la plantilla de emergencia: {error}"
    logger.warning(f"{problem} Se usan los valores por defecto; {emergency}.")
    logger.info("Configuración: valores por defecto")
    return Config()


def main() -> None:
    defaults = Config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true", help="lista los dispositivos de entrada y termina")
    parser.add_argument("--device", type=parse_device, help=f"índice o nombre del dispositivo de entrada (defecto: el que contenga '{PREFERRED_DEVICE}', si no el del sistema)")
    parser.add_argument("--model", help=f"modelo de faster-whisper (defecto: {defaults.model})")
    parser.add_argument("--language", help=f"idioma de la transcripción (defecto: {defaults.language})")
    parser.add_argument("--key", help=f"tecla de disparo, nombre de pynput.keyboard.Key o un carácter (defecto: {defaults.key})")
    parser.add_argument("--switch-key", help=f"tecla de cambio de entrada de audio, mismo formato que --key (defecto: {defaults.switch_key})")
    parser.add_argument("--config", type=Path, help=f"archivo de configuración TOML (defecto: {CONFIG_FILENAME} en la raíz del repo, si no {USER_CONFIG_PATH})")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    setup_logging()
    log_banner()
    config = resolve_config(args.config)
    # CLI > archivo > defectos; un argumento solo cuenta si se escribió (defecto None)
    model = args.model if args.model is not None else config.model
    language = args.language if args.language is not None else config.language
    key_name = args.key if args.key is not None else config.key
    switch_key_name = args.switch_key if args.switch_key is not None else config.switch_key

    if shutil.which("xdotool") is None:
        logger.error("Falta xdotool. Instálalo con: sudo apt install xdotool")
        sys.exit(1)
    if os.environ.get("XDG_SESSION_TYPE", "x11") != "x11":
        logger.warning(f"Aviso: la sesión es {os.environ['XDG_SESSION_TYPE']!r}, no x11; la tecla global y xdotool pueden no funcionar.")
    set_enabled(config.notifications)
    if config.notifications and shutil.which("notify-send") is None:
        logger.warning("Aviso: falta notify-send (sudo apt install libnotify-bin); solo habrá mensajes por consola.")

    try:
        key = parse_key(key_name)
    except ValueError as error:
        logger.error(f"Error con --key: {error}")
        sys.exit(1)
    try:
        switch_key = parse_key(switch_key_name)
    except ValueError as error:
        logger.error(f"Error con --switch-key: {error}")
        sys.exit(1)
    if switch_key == key:
        logger.error(f"--switch-key y --key no pueden ser la misma tecla ({key_name!r}).")
        sys.exit(1)

    # --device > estado guardado > [audio] device > default_device()
    if config.device is not None:
        fallback = parse_device(config.device) if isinstance(config.device, str) else config.device
        fallback_label = f"[audio] device {fallback!r}"
    else:
        fallback, fallback_label = None, "el dispositivo por defecto"
    saved = load_state_device() if args.device is None else None
    if saved is not None:
        try:
            sd.query_devices(saved, "input")
        except (sd.PortAudioError, ValueError):
            logger.warning(f"El dispositivo guardado {saved!r} no está disponible; se usa {fallback_label}.")
            saved = None
    if args.device is not None:
        device = args.device
    elif saved is not None:
        device = saved
    else:
        device = fallback if fallback is not None else default_device()
    try:
        sd.query_devices(device, "input")
    except (sd.PortAudioError, ValueError) as error:
        logger.error(f"Error con el dispositivo de entrada {device!r}: {error}")
        sys.exit(1)

    logger.info(f"Cargando {model} ({COMPUTE_TYPE}, GPU)...")
    notify("SpeechFlow", f"Cargando {model}...")
    started = time.perf_counter()
    transcriber = Transcriber(model, language)
    load_seconds = time.perf_counter() - started
    notify("SpeechFlow", f"Modelo {model} cargado")
    logger.info(f"Modelo: {model} | idioma: {language} | compute_type: {COMPUTE_TYPE} | GPU")
    logger.info(f"Modelo cargado en {load_seconds:.2f} s (incluye calentamiento)")
    logger.info(f"Dispositivo de audio: {describe_device(device)}")
    logger.info(f"Cambio de entrada de audio: tecla {switch_key_name!r}.")
    logger.info(f"Listo. Mantén pulsada la tecla {key_name!r} para dictar. Ctrl+C para salir.")

    push_to_talk = PushToTalk(key, switch_key, device, transcriber, model, config.min_seconds, config.max_seconds)
    push_to_talk.start_watcher(config.watch_interval)
    try:
        with keyboard.Listener(on_press=push_to_talk.on_press, on_release=push_to_talk.on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        logger.info("Saliendo.")
        push_to_talk.stop_watcher()
        transcriber.close()
        logger.info(f"Modelo {model} liberado.")
        notify("SpeechFlow", "Modelo liberado")


if __name__ == "__main__":
    main()
