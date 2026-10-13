# SpeechFlow
SpeechFlow es una herramienta para el dictado por voz, en la cual mediante un micrófono convierte nuestras voz en palabras,
su meta es poder ser utilizada en cualquier parte del sistema sin importar la herramienta. Solo actualmente disponible en 
Linux Debian 13. 

## FP16 en cuda 12.4 en GTX 1060 6GB
La arquitectura Pascal (Compute Capability 6.1) de la Nvidia GTX 1060 6GB soporta FP16 (precisión de 16 bits), pero carece de núcleos Tensor, por lo que su rendimiento en FP16 es lento (emulado o de baja velocidad en comparación con FP32). Además, CUDA 12.4 es compatible con la GTX 1060 a nivel de driver y ejecución, pero no acelerará de forma nativa ni eficiente el cálculo en FP16 como lo haría en tarjetas con arquitecturas más modernas (Volta, Turing, Ampere o posteriores).

## Comando para fragmentar los samples.
```bash
ffmpeg -i audio_original.wav -f segment -segment_time 10 -c copy segmento_%03d.wav
```
## WAV Estéreo 44.1 kHz v.s Mono 16 kHz.
Sí, existen diferencias técnicas importantes entre ambos archivos, pero OpenAI Whisper procesa y convierte internamente cualquier audio a mono de 16 kHz antes de realizar el reconocimiento de voz.
Diferencias técnicas de los archivos
• Estéreo a 44.1 kHz: Contiene dos canales de audio (izquierdo y derecho) y toma 44,100 muestras por segundo. Ocupa mucho más espacio de almacenamiento y ancho de banda porque almacena el doble de canales y una frecuencia mayor a la necesaria para la voz humana.
• Mono a 16 kHz: Contiene un solo canal de audio mezclado para ambos lados y toma 16,000 muestras por segundo. Es el estándar óptimo y nativo para la Whisper Audio Requirements.
¿Afecta al resultado final en Whisper?
• Precisión: No hay una mejora en la transcripción si usas 44.1 kHz estéreo, ya que Whisper descarta la información estéreo y reduce la frecuencia a 16 kHz de todos modos.
• Rendimiento y velocidad: Enviar el archivo original en estéreo de 44.1 kHz obliga a Whisper (o a tu sistema) a gastar recursos extra y tiempo haciendo la conversión interna. Convertir el archivo previamente a mono de 16 kHz acelera la carga y ahorra memoria o espacio de procesamiento

## Requisitos

- Debian 13 con X11.
- GPU NVIDIA con driver compatible con CUDA 12 (probado con GTX 1060 6 GB y driver 550.163.01). Es opcional: sin GPU, o con un driver roto, funciona solo en CPU (ver [Modo solo CPU](#modo-solo-cpu)).
- [Conda](https://docs.conda.io/) (miniconda o similar).
- Para el push-to-talk, paquetes de sistema: `sudo apt install xdotool xclip x11-utils libnotify-bin` (`xdotool` es obligatorio; `xclip` es obligatorio salvo con `[text] insert_method = "type"`; `x11-utils` aporta `xprop`, que detecta las terminales para pegar con `Ctrl+Shift+V` (sin él se pega siempre con `Ctrl+V`); `libnotify-bin` aporta `notify-send` y es opcional).

## Instalación

```bash
conda env create -f environment.yml
conda activate speechflow
```

El entorno incluye Python 3.12, `sounddevice` (con `portaudio`), `scipy`, y cuBLAS y cuDNN (CUDA 12) desde conda-forge; el resto de dependencias (`faster-whisper`, `av<17`, `pynput`) y el propio paquete se instalan con `pip install -e .[dev]` (declarado en `environment.yml` y `pyproject.toml`; el extra `dev` añade `pytest`). Eso deja el comando `speechflow` en el `PATH` del entorno, que debe estar activado. En un entorno existente: `pip install -e .[dev]` (o `pip install -e .` sin las herramientas de desarrollo).

Para comprobar que la GPU es visible:

```bash
python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"  # debe imprimir 1
```

## Benchmark de STT

1. Coloca fragmentos WAV de hasta 30 s (idealmente mono, 16 kHz) en `benchmarks/samples/`, nombrados `<prefijo>_NNN.wav`. Esa carpeta no se versiona. El idioma de cada muestra se deduce del prefijo mediante `LANGUAGE_BY_PREFIX` en `scripts/benchmark_stt.py`:

   | Prefijo | Idioma |
   | ------- | ------ |
   | `mercado-libre` | `es` |
   | `bug-lower` | `en` |

   Una familia de audios nueva exige añadir su prefijo al mapa. Los WAV de más de 30 s o sin un prefijo conocido se omiten (estos últimos con una advertencia en stderr).
2. Ejecuta:

   ```bash
   python scripts/benchmark_stt.py
   ```

   Compara `small` y `medium` en `int8` sobre GPU, usando todos los fragmentos válidos de `benchmarks/samples/` (sin límite de muestras), cada uno en su idioma. La corrida completa tarda varios minutos. Opciones: `--models`, `--compute-type`, `--max-samples N` (máximo de muestras **por idioma**, útil para una prueba corta) o rutas de WAV concretas.

3. El resultado se guarda en `benchmarks/results.md`, con la mediana por modelo e idioma (normalizada a 10 s de audio), el modelo recomendado por defecto, y la tabla con idioma, carga, latencia y VRAM pico de cada muestra.

La primera ejecución descarga los modelos desde Hugging Face (`medium` pesa ~1.5 GB), así que el tiempo de carga inicial no es representativo.

## Módulo de transcripción

`src/speechflow/transcriber.py` define `Transcriber`, que carga `faster-whisper` una sola vez (`int8`; GPU o CPU según `device`, ver [Modo solo CPU](#modo-solo-cpu)), hace un calentamiento y transcribe cuantas veces se quiera sin recargar el modelo.

```python
import wave

import numpy as np

from speechflow.transcriber import Transcriber

transcriber = Transcriber("medium", "es")  # carga y calienta el modelo una vez

with wave.open("benchmarks/captures/capture.wav", "rb") as wav:
    audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)

text, seconds = transcriber.transcribe(audio)
print(f"{seconds:.2f} s: {text}")
```

- **Entrada:** `numpy.ndarray` `int16`, mono, a 16 kHz. El módulo no valida la tasa: un audio a otra tasa da transcripciones erróneas sin aviso.
- **Salida:** `(texto, segundos)`. Los segundos no incluyen la carga del modelo ni el calentamiento. Un array vacío devuelve `("", 0.0)` sin invocar al modelo.
- **Parámetros:** modelo (sin fijar: `medium` en GPU y `small` en CPU; uno explícito se usa siempre y queda en `Transcriber.model_name`), idioma por defecto (defecto `es`; `"auto"` detecta entre `es` y `en`) y `vad` (defecto `True`). `transcribe(audio, language=None)` acepta un idioma para esa llamada (`None` usa el del objeto; `"auto"` activa la detección) y deja el idioma realmente usado en `last_language`.
- **Detección automática:** con `"auto"`, `WhisperModel.detect_language()` elige el de mayor probabilidad entre `es` y `en` (aunque otro idioma tenga la mayor) y transcribe con ese. Los segundos devueltos incluyen la detección. Si la detección falla (por ejemplo, audio sin voz), se usa el idioma fijo del objeto, o `es` si no es `es` ni `en`. El calentamiento llama también a `detect_language()` sobre un segundo de silencio.
- **VAD:** con `vad=True`, cada transcripción usa `vad_filter` de `faster-whisper` (Silero, parámetros por defecto: se descartan silencios de 2 s o más, con 400 ms de margen), para que el silencio y el ruido sin voz no produzcan texto inventado. Una grabación sin voz devuelve texto vacío. El calentamiento hace una llamada extra con el filtro para cargar Silero al arrancar. `vad=False` lo desactiva.
- **Liberación:** `close()` suelta la referencia al modelo y fuerza la recolección de basura para liberar la GPU. Es idempotente; no se debe llamar a `transcribe()` después.
- `scripts/capture_mic.py` usa este módulo.

## Módulos de captura, inserción, notificación y log

- `src/speechflow/audio.py`: dispositivos de entrada, remuestreo, medición, guardado de WAV y `Recorder` (`start()` / `stop()`), que graba a la tasa nativa del dispositivo y devuelve `int16` mono a 16 kHz. Para el cambio de entrada en caliente expone `input_devices()` (índices con entrada), `refresh_devices()` (reinicializa PortAudio para ver micrófonos conectados o desconectados; solo sin streams abiertos), `device_index()` (índice real de un dispositivo, o `None`) y `next_input_device()` (el siguiente, con vuelta al principio). Para vigilar el micrófono seleccionado expone `device_name()` (nombre de un dispositivo, o `None`), `input_device_by_name()` (índice del primer dispositivo de entrada con ese nombre exacto, o `None`) y `Recorder.active` (hay un stream abierto y activo); `Recorder.stop()` tolera un stream caído. Lo usan `capture_mic.py` y `app.py`.
- `src/speechflow/punctuation.py`: `apply_voice_punctuation(text, language)`, función pura que sustituye los comandos de voz de puntuación (ver [Comandos de voz de puntuación](#comandos-de-voz-de-puntuación)); `app.py` la aplica entre la transcripción y `insert_text()`.
- `src/speechflow/replacements.py`: `compile_rules(pairs)` compila pares `(patrón, reemplazo)` con `re.IGNORECASE` (`ValueError` si no son válidos) y `apply_replacements(text, rules)` los aplica en orden. Ver [Diccionario de reemplazos e `initial_prompt`](#diccionario-de-reemplazos-e-initial_prompt).
- `src/speechflow/inserter.py`: `insert_text(text, method, extra_terminals)` inserta el texto en la ventana con foco. Con `method="clipboard"` (el defecto) lo copia al portapapeles con `xclip`, lo pega con `xdotool key` (`Ctrl+V`, o `Ctrl+Shift+V` si la ventana es una terminal) y restaura el texto previo del portapapeles; si `xclip` o `xdotool` fallan, registra un `WARNING` y teclea con `xdotool type --clearmodifiers`, que es también el comportamiento de `method="type"`.
- `src/speechflow/notifier.py`: `notify(title, body)` envía una notificación de escritorio con `notify-send`; si no está instalado o están desactivadas con `set_enabled(False)`, no hace nada.
- `src/speechflow/config.py`: configuración de usuario de la app de push-to-talk (`Config`, `find_config()`, `load_config()`, `write_emergency()` y el estado del micrófono con `load_state_device()` / `save_state_device()`). Ver [Configuración](#configuración).
- `src/speechflow/history.py`: `History(path, max_bytes, backup_count)` escribe una línea JSON por dictado con `add(entry)` (rotación por tamaño, permisos `0600`, un hilo a la vez) y se cierra con `close()`. Ver [Historial de transcripciones](#historial-de-transcripciones).
- `src/speechflow/log.py`: `setup_logging(console_level)` configura el logger `speechflow` (en `DEBUG`; filtran los manejadores) con el formato `AAAA-MM-DD HH:MM:SS.mmm NIVEL mensaje` (hora local). Las líneas por debajo de `WARNING` salen por stdout y las `WARNING` y `ERROR` por stderr. Es idempotente. `apply_log_levels(consola, archivo)` reajusta los niveles de los manejadores una vez leída la configuración (ver [Niveles de log](#niveles-de-log)). Añade un tercer manejador, un `RotatingFileHandler` en `speechflow.log` (ver [Configuración](#configuración)): mismas líneas `INFO`, `WARNING` y `ERROR` y mismo formato que la consola, 1 MB por archivo y 3 copias (`speechflow.log.1` a `.3`, unos 4 MB como máximo), con permisos `0600` también tras rotar. Si el archivo no se puede abrir, registra `No se puede escribir el log en ...` y sigue solo con consola. `log_banner()` imprime por stdout, sin prefijo, el arte ASCII de SpeechFlow con su versión y la de `faster-whisper`; `app.py` lo muestra tras leer la configuración y antes de `Cargando ...`, salvo que el nivel de consola sea `warning` o `error`. Por ahora solo lo usa `app.py`.

## Push-to-talk

El comando `speechflow` permite dictar en cualquier aplicación de X11: mantén pulsada una tecla global (`Right Ctrl` por defecto), habla, y al soltarla el texto se escribe en la ventana con foco. Se ejecuta en primer plano y termina con `Ctrl+C` (`SIGINT`), `SIGTERM` o `SIGHUP`. `python -m speechflow` es equivalente.

La lógica vive en `src/speechflow/app.py` (`State`, `PushToTalk`, `parse_key`, `describe_device`, `load_transcriber`, `resolve_config` y `main()`), importable desde otros módulos; `speechflow.app:main` es el punto de entrada del comando y `src/speechflow/__main__.py` el de `python -m speechflow`.

```bash
speechflow --list-devices   # lista los dispositivos de entrada
speechflow                  # Right Ctrl, modelo medium en GPU (small en CPU), español
speechflow --key f9         # otra tecla de disparo
speechflow --switch-key f7  # otra tecla de cambio de entrada
speechflow --device 6 --model small --language en
speechflow --config mi-config.toml
python -m speechflow        # equivalente a `speechflow`
```

Salida de ejemplo:

```
2026-10-05 14:32:02.580 INFO    Configuración: /home/usuario/.config/speechflow/config.toml
________                       ______ _______________
__  ___/__________________________  /____  ____/__  /________      __
_____ \___  __ \  _ \  _ \  ___/_  __ \_  /_   __  /_  __ \_ | /| / /
____/ /__  /_/ /  __/  __/ /__ _  / / /  __/   _  / / /_/ /_ |/ |/ /
/____/ _  .___/\___/\___/\___/ /_/ /_//_/      /_/  \____/____/|__/
       /_/
SpeechFlow 0.1.0
Powered by faster-whisper 1.2.1

2026-10-05 14:32:02.590 INFO    Cargando medium (int8, GPU)...
2026-10-05 14:32:07.412 INFO    Modelo: medium | idioma: es | compute_type: int8 | GPU
2026-10-05 14:32:07.412 INFO    Modelo cargado en 4.82 s (incluye calentamiento)
2026-10-05 14:32:07.413 INFO    Dispositivo de audio: [9] Realtek Audio USB: Audio (hw:3,0) | 44100 Hz nativos a 16000 Hz mono
2026-10-05 14:32:07.413 INFO    Cambio de entrada de audio: tecla 'f8'.
2026-10-05 14:32:07.413 INFO    Cambio de idioma: tecla 'f7'; modo automático: tecla 'f6'.
2026-10-05 14:32:07.413 INFO    Listo. Mantén pulsada la tecla 'ctrl_r' para dictar. Ctrl+C para salir.
2026-10-05 14:32:15.208 INFO    Grabando...
2026-10-05 14:32:26.391 INFO    Grabación terminada: 11.18 s. Transcribiendo con medium/es...
2026-10-05 14:32:27.421 INFO    Insertado (1.03 s, 0.09x tiempo real, 112 caracteres, medium/es): El juego de la pelota prehispánico, que se practicaba a lo largo del territorio...
2026-10-05 14:32:33.874 INFO    Entrada de audio cambiada: [4] HD-Audio Generic: ALC1220 Analog (hw:1,0) | 44100 Hz nativos a 16000 Hz mono
2026-10-05 14:33:11.864 WARNING El micrófono seleccionado se desconectó: HD-Audio Generic: ALC1220 Analog (hw:1,0).
2026-10-05 14:33:29.932 INFO    Micrófono reconectado: [4] HD-Audio Generic: ALC1220 Analog (hw:1,0) | 44100 Hz nativos a 16000 Hz mono
2026-10-05 14:32:40.105 INFO    Saliendo.
2026-10-05 14:32:40.160 INFO    Modelo medium liberado.
```

Con `[model] idle_timeout = 600`, tras 10 minutos sin dictar y al pulsar de nuevo la tecla:

```
2026-10-05 14:42:27.421 INFO    Modelo medium liberado por inactividad (600 s sin uso).
2026-10-05 14:55:03.100 INFO    Grabando...
2026-10-05 14:55:03.101 INFO    Modelo descargado: se carga medium mientras grabas.
2026-10-05 14:55:03.102 INFO    Cargando medium (int8, GPU)...
2026-10-05 14:55:07.930 INFO    Modelo cargado en 4.83 s (incluye calentamiento)
```

Cada línea lleva fecha, hora con milisegundos y nivel. Los avisos (`WARNING`) y errores (`ERROR`) salen por stderr, el resto por stdout; el aviso de estado de PortAudio de `audio.py` sale sin prefijo.

Opciones:

| Opción | Descripción | Defecto |
| ------ | ----------- | ------- |
| `--list-devices` | Lista los dispositivos de entrada y termina (`>` marca el del sistema). | — |
| `--device` | Índice o nombre del dispositivo de entrada. Falla con un mensaje claro si no existe. | primero que contenga "Realtek"; si no, el del sistema |
| `--model` | Modelo de `faster-whisper`. | `small` en CPU, `medium` en GPU |
| `--language` | Idioma de la transcripción: `es`, `en`, otro idioma de Whisper, o `auto` (detecta entre `es` y `en` en cada dictado). | `es` |
| `--key` | Tecla de disparo: nombre de `pynput.keyboard.Key` (`ctrl_r`, `f9`, ...) o un carácter suelto. Falla con un mensaje claro si no existe. | `ctrl_r` |
| `--switch-key` | Tecla de cambio de entrada de audio, mismo formato que `--key`. Debe ser distinta de `--key`; si no, el script sale con código 1. | `f8` |
| `--compute-device` | Dispositivo de Whisper: `auto` (GPU si funciona, si no CPU), `cpu` o `cuda`. Gana sobre `[model] device`. Ver [Modo solo CPU](#modo-solo-cpu). | `auto` |
| `--quiet` | Consola solo con `WARNING` y `ERROR` (equivale a `--log-level warning`). Omite el banner. No cambia el archivo de log ni las notificaciones. Excluyente con `--verbose` y `--log-level`. | — |
| `--verbose` | Consola con mensajes `DEBUG` (equivale a `--log-level debug`). No cambia el archivo de log. Excluyente con `--quiet` y `--log-level`. | — |
| `--log-level` | Nivel de la consola: `debug`, `info`, `warning` o `error`. Gana sobre `[log] level`. Ver [Niveles de log](#niveles-de-log). | `info` |
| `--config` | Archivo de configuración TOML. Si no existe, el script sale con código 1. | `$XDG_CONFIG_HOME/speechflow/config.toml` (`~/.config/speechflow/config.toml`) |

Un argumento escrito en la línea de comandos gana sobre el archivo de configuración (ver [Configuración](#configuración)).

- **Modelo:** se carga al arrancar, así que cada dictado responde rápido. Con `medium` int8 en la GTX 1060, ~11 s de audio tardaron 1.03 s. Con `[model] idle_timeout` desactivado (`0`, el defecto) no se vuelve a cargar.
- **Filtro de silencios (VAD):** con `[model] vad = true` (el defecto) Whisper solo recibe los tramos con voz, así que pulsar la tecla sin hablar registra `Sin texto reconocido (...)` y no inserta nada. Solo se recortan silencios de 2 s o más. Si recorta palabras con tu voz o tu micrófono, pon `vad = false`. El ajuste se lee al arrancar, aparece como `VAD: sí/no` en la línea `Modelo: ...` y se conserva al recargar el modelo tras una descarga por inactividad. `vad = 1` o `vad = "si"` hacen inválido el archivo.
- **Descarga por inactividad:** con `[model] idle_timeout = N` (`N` ≥ 30; `0` desactiva), tras `N` segundos en reposo sin dictar el modelo se libera de la GPU y se registra `Modelo {modelo} liberado por inactividad ({N} s sin uso).`. La cuenta empieza cada vez que el script vuelve a reposo: tras una transcripción, tras una grabación descartada por corta o tras una recarga fallida. No se libera mientras se graba ni se transcribe. No envía notificación de escritorio. Si `close()` no devuelve toda la VRAM (la caché de CUDA puede retener algo), esa memoria sigue ocupada hasta salir del proceso.
- **Recarga bajo demanda:** con el modelo descargado, pulsar la tecla de grabar abre el micrófono, empieza a grabar al instante y carga el modelo en paralelo (`Modelo descargado: se carga {modelo} mientras grabas.`, `Cargando ...`, `Modelo cargado en ...`). Al soltar, la transcripción espera a que acabe la carga y no se pierde nada de lo dictado. Si el micrófono falla al abrir, no se carga nada. Si la recarga falla, se registra `Error al recargar el modelo: ...`, se envía una notificación de error, se descarta el audio y la siguiente pulsación reintenta. La recarga con éxito no notifica.
- **Grabaciones cortas:** las de menos de 0.5 s (`[recording] min_seconds`) se descartan sin invocar al modelo (evita escribir texto basura por toques accidentales).
- **Límite:** a los 60 s (`[recording] max_seconds`) la grabación se corta sola, se transcribe lo grabado y se avisa. No empieza otra hasta soltar la tecla y volver a pulsarla (en modo toggle, hasta volver a pulsarla).
- **Modo toggle:** con `[recording] mode = "toggle"` (defecto `"hold"`) no hace falta mantener la tecla: una pulsación de `record` empieza a grabar y la siguiente para y transcribe. Soltar la tecla no hace nada y las repeticiones automáticas de la tecla mantenida se ignoran. Pulsar mientras se transcribe registra un `WARNING` y no graba. Las grabaciones menores que `min_seconds` se descartan igual, y `max_seconds` sigue cortando la grabación: para dictados largos, súbelo. El modo se lee solo al arrancar; cambiarlo exige reiniciar, y el mensaje `Listo. ...` indica cómo dictar según el modo.
- **Durante la transcripción:** pulsar la tecla no inicia otra grabación.
- **Avisos:** todo se muestra por consola con prefijo de fecha, hora y nivel. Como notificación de escritorio solo salen el ciclo de vida del modelo en el arranque y la salida (`Cargando {modelo}...`, `Modelo {modelo} cargado`, `Modelo liberado`), los errores (micrófono, transcripción, inserción o recarga del modelo) el cambio de entrada de audio (`Entrada de audio: {nombre}`) y las alertas del micrófono (`Micrófono desconectado: {nombre}`, `Micrófono reconectado: {nombre}` y, al arrancar, `Micrófono guardado no disponible: {nombre}`). Dictar no genera notificaciones. Si falta `notify-send`, se avisa una vez y sigue funcionando solo con consola. Con `[notifications] enabled = false` no sale ninguna notificación y ese aviso tampoco.
- **Cambio de entrada en caliente:** pulsar `--switch-key` (`f8`) pasa al siguiente dispositivo de entrada, en orden de índice y con vuelta al principio, sin recargar el modelo. Cada pulsación relee la lista de dispositivos, así que un micrófono conectado o desconectado con el script en marcha se tiene en cuenta. La rotación incluye todo lo que muestra `--list-devices` (también los `Loopback`; si el elegido no abre, el error sale al dictar y basta pulsar la tecla otra vez). Solo cambia en reposo: durante la grabación o la transcripción se registra un `WARNING` y no pasa nada. Con un único dispositivo se registra `Solo hay un dispositivo de entrada: ...` sin notificación. Un cambio efectivo guarda el nombre del dispositivo en `state.toml` (ver [Configuración](#configuración)), y al reiniciar se usa ese micrófono.
- **Cambio de idioma en caliente:** la tecla `[keys] language` (`f7`) alterna `es` ↔ `en` sin recargar el modelo; un idioma distinto (por ejemplo `fr`) pasa a `es`. La tecla `[keys] auto` (`f6`) activa la detección automática (`language = "auto"`, restringida a `es`/`en`) y, pulsada otra vez, vuelve al último idioma fijo. Estando en auto, la tecla de idioma sale de auto y fija el otro idioma respecto al último fijo (último `es` → `en`, último `en` → `es`, otro → `es`); si se arranca en auto, el último fijo es `es`. Ambas teclas solo actúan en reposo: grabando o transcribiendo se registra un `WARNING` y no pasa nada. Mantener la tecla pulsada cambia una sola vez. Cada cambio registra `Idioma cambiado: ...`, envía una notificación y se guarda en `state.toml`; también funciona con el modelo descargado por inactividad (el modelo recargado usa el idioma vigente). En auto, los logs `Insertado (...)` y `Sin texto reconocido (...)` muestran `auto→es` o `auto→en`; la línea `Transcribiendo con ...` muestra `auto`, porque aún no se ha detectado. Las teclas solo se configuran en el TOML (no hay opciones de CLI).
- **Vigilancia del micrófono:** un hilo comprueba cada `[audio] watch_interval` segundos (defecto 3, mínimo 1) que el micrófono seleccionado sigue conectado; lo identifica por nombre, porque los índices cambian al releer los dispositivos. En reposo relee los dispositivos (`refresh_devices()`) bajo el mismo bloqueo que las teclas, así que una pulsación puede esperar unos instantes. Al desconectarse registra un `WARNING` (`El micrófono seleccionado se desconectó: ...`) y envía una notificación, una sola vez. Mientras está desconectado, la tecla de grabar solo muestra un `WARNING` y no graba; reconectarlo o pulsar `--switch-key` lo resuelve. Al reconectarse registra `Micrófono reconectado: ...`, notifica y vuelve a usarlo sin pulsar nada. Si cae durante una grabación (no relee dispositivos en ese caso, solo comprueba que el stream siga activo), registra `...se desconectó durante la grabación: ...`, detiene la grabación y transcribe lo capturado si dura al menos `min_seconds`. PortAudio puede imprimir por stderr líneas `Expression 'alsa_snd_pcm_...' failed` en ese momento; no pasan por el log. No cambia solo de micrófono.
- **Salida:** `Ctrl+C`, `SIGTERM` (`kill`, `systemctl stop`) y `SIGHUP` (cierre de la terminal) siguen la misma ruta. La consola muestra `Saliendo.` (con `SIGTERM` o `SIGHUP`, `Señal {nombre} recibida. Saliendo.`) y se ignoran las teclas de grabar y de cambio de entrada. Una grabación en curso se descarta sin transcribir (`Grabación descartada por cierre.`). Una transcripción en curso se espera hasta 30 s: su texto se inserta como siempre; si no termina en ese tiempo, se registra un `WARNING` y se sale sin liberar el modelo. También se espera a una recarga del modelo en curso. Después se libera el modelo con `Transcriber.close()` (suelta la GPU antes de terminar el proceso) y se notifica `Modelo liberado`; la consola muestra `Modelo {modelo} liberado.`. Si el modelo ya estaba descargado por inactividad, solo muestra el mensaje de salida. Una segunda señal durante la espera fuerza la salida inmediata (`Segunda señal recibida; salida inmediata.`). El código de salida es siempre 0. Las señales durante el arranque (validaciones y carga inicial del modelo) conservan el comportamiento anterior.
- **Requisitos:** sesión X11 y `xdotool` instalado; si falta, el script sale al arrancar con código 1 y una línea `ERROR` indicando `sudo apt install xdotool`. Con `[text] insert_method = "clipboard"` (el defecto) también hace falta `xclip`, con el mismo trato (`sudo apt install xclip`); con `"type"` no se exige. Los errores de arranque (`--key`, `--switch-key` o `--device` inválidos, o dos de las teclas `--key`, `--switch-key`, `[keys] language` y `[keys] auto` iguales) también terminan con código 1.
- **Inserción por portapapeles:** con `[text] insert_method = "clipboard"` (el defecto), el dictado se copia a la selección `CLIPBOARD` y se pega con `Ctrl+V`, o con `Ctrl+Shift+V` si la clase de la ventana con foco es una terminal conocida (`gnome-terminal`, `konsole`, `xterm`, `alacritty`, `kitty`, `xfce4-terminal`, `terminator`, `tilix`, `wezterm`, `foot` y otras). Así los acentos, la `ñ`, `¿` y `¡` llegan íntegros, sea cual sea la distribución del teclado. Tras 0,3 s se restaura el texto que había en el portapapeles. Si tu terminal no está en la lista y `Ctrl+V` no pega, averigua su clase con `xprop -id $(xdotool getwindowfocus) WM_CLASS` (con la terminal enfocada; se compara con la instancia y con la clase) y añádela en `[text] terminal_classes = ["miterm"]` (se suma a las de serie; no distingue mayúsculas). La selección `PRIMARY` (clic central) no se toca. Para volver a teclear con `xdotool type`, usa `[text] insert_method = "type"`. Ambas claves se leen solo al arrancar. Limitaciones:
  - Una aplicación que lea el portapapeles pasados 0,3 s pegará el contenido restaurado en vez del dictado.
  - Solo se restaura texto: si el portapapeles contenía una imagen o archivos, se pierde y queda el dictado.
  - Los gestores de historial del portapapeles verán el dictado y el contenido restaurado.
  - Algunos campos que bloquean el pegado (contraseñas, algunas máquinas virtuales) lo ignoran sin error; ahí usa `"type"`.
  - El `WARNING` `Portapapeles no disponible (...)` solo salta si falla un comando, no si el pegado no tiene efecto.
- **Foco:** el texto se escribe en la ventana que tenga el foco cuando termina la transcripción. Si cambias de ventana mientras se transcribe, se escribirá en la nueva.
- **Una sola instancia:** no ejecutes dos a la vez; ambas reaccionarían a la misma tecla y competirían por el micrófono.

## Comandos de voz de puntuación

Con `[text] punctuation_commands = true` (el defecto), el texto transcrito pasa por `apply_voice_punctuation()` antes de insertarse: las palabras dictadas de la tabla se sustituyen por su signo. El vocabulario depende del idioma usado en el dictado (en modo `auto`, el detectado); con cualquier otro idioma (por ejemplo `fr`) el texto se inserta tal cual.

| Resultado | Español | Inglés |
| --------- | ------- | ------ |
| `.` | `punto` | `period` |
| `,` | `coma` | `comma` |
| `;` | `punto y coma` | `semicolon` |
| `:` | `dos puntos` | `colon` |
| `?` | `interrogación`, `cerrar interrogación` | `question mark` |
| `¿` | `abrir interrogación` | — |
| `!` | `exclamación`, `cerrar exclamación` | `exclamation mark` |
| `¡` | `abrir exclamación` | — |
| `...` | `puntos suspensivos` | `ellipsis` |
| salto de línea | `nueva línea` | `new line` |
| párrafo (dos saltos) | `nuevo párrafo` | `new paragraph` |
| `(` / `)` | `abrir paréntesis` / `cerrar paréntesis` | `open parenthesis` / `close parenthesis` |
| `"` (apertura / cierre) | `abrir comillas` / `cerrar comillas` | `open quote` / `close quote` |
| `-` (con un espacio a cada lado) | `guion` | `dash` |

Ejemplo: dictar "hola coma mundo punto" inserta `Hola, mundo.`.

- **Coincidencia:** no distingue mayúsculas ni la puntuación que Whisper pega a las palabras del comando (`Punto.` y `coma,` valen como `punto` y `coma`). Gana la frase más larga: `punto y coma` antes que `punto`, y `dos puntos` antes que `puntos suspensivos`. Si el comando es `. , ; : ? ! ...`, también se quita la puntuación final de la palabra anterior (`Hola, coma` no da `Hola,,`).
- **Espaciado:** sin espacio antes de `. , ; : ? ! ...`, `)` ni la comilla de cierre; sin espacio después de `¿ ¡ (` ni la comilla de apertura.
- **Mayúsculas:** la primera letra del texto y la que sigue a `.`, `?`, `!` y a los saltos de línea se ponen en mayúscula (atravesando `¿ ¡ ( "`). **Con la función activa, la primera letra de cada dictado sale en mayúscula aunque no uses ningún comando**, también si continúas una frase ya empezada en la ventana de destino. No se capitaliza tras `...` ni los nombres propios.
- **Palabra de escape:** `literal` (en inglés, `literally`) justo delante de un comando lo deja como palabra normal y se descarta; solo afecta a una palabra. "Un literal punto de vista" inserta `Un punto de vista`. Si no precede a un comando, `literal` se conserva. No hay forma de escribir `literal` seguido de un comando.
- **`nueva línea` y `nuevo párrafo`:** con `[text] insert_method = "clipboard"` (el defecto) se pega un salto de línea, no se teclea `Return`; en un chat o formulario puede no enviar el mensaje, según cómo trate la aplicación el texto pegado. Con `"type"` se teclea `Return` (`xdotool type`) y en un chat puede enviarlo; si te pasa, apaga la función.
- **Palabras ambiguas:** `punto`, `coma`, `guion` o `comillas` en una frase normal también se sustituyen. Usa `literal` o apaga la función. Cuando el texto cambia, el log muestra `Texto original: ...` justo antes de `Insertado (...)`, para ver qué se sustituyó.
- **Apagarla:** `[text] punctuation_commands = false` inserta exactamente lo que devuelve Whisper, sin mayúscula inicial. Se lee solo al arrancar; cambiarla exige reiniciar. No hay opción de CLI ni tecla en caliente.

```
2026-10-09 10:15:03.221 INFO    Texto original: hola coma mundo punto
2026-10-09 10:15:03.222 INFO    Insertado (0.42 s, 0.12x tiempo real, 12 caracteres, medium/es): Hola, mundo.
```

## Diccionario de reemplazos e `initial_prompt`

Whisper escribe mal nombres propios, marcas y jerga (`git hub`, `pi torch`, `cuber netis`). Hay dos palancas complementarias: darle contexto antes de transcribir (`[model] initial_prompt`, que reduce el error) y corregir lo que aun así falla después (`[replacements]`, que lo elimina de forma determinista). Ambas se leen solo al arrancar; cambiarlas exige reiniciar.

### `[model] initial_prompt`

Texto que se pasa a Whisper como contexto en cada dictado. Vacío (el defecto) significa sin prompt. No se usa en la detección automática de idioma y se conserva al recargar el modelo tras la descarga por inactividad.

```toml
[model]
initial_prompt = "Hablo de GitHub, PyTorch y Kubernetes."
```

- **Longitud:** Whisper solo usa los últimos ~224 tokens. Si pasa de 1000 caracteres, el arranque registra `WARNING` `model.initial_prompt tiene <n> caracteres; Whisper solo usa los últimos ~224 tokens.` y se usa sin truncar.
- **Consejos:** escribe una frase corta y natural con los términos tal como quieres verlos (mayúsculas y grafía incluidas), en el idioma que más dictas; una lista de palabras sueltas funciona peor que una frase. Un prompt mal elegido puede sesgar o empeorar la transcripción (que repita el prompt o invente vocabulario); si pasa, déjalo vacío o acórtalo. Es único para todos los idiomas.

### `[replacements]`

Reglas `"patrón" = "reemplazo"` que se aplican al texto ya con la puntuación por voz y antes de guardarlo en el historial y de insertarlo.

```toml
[replacements]
"git ?hub" = "GitHub"
"pi ?torch" = "PyTorch"
'(\d+) por ciento' = '\1 %'

[replacements.es]
"cuber ?netis" = "Kubernetes"

[replacements.en]
"cube ?r ?netes" = "Kubernetes"
```

- **Sintaxis:** el patrón es una expresión regular de Python (`re`) y el reemplazo admite `\1` y `\g<nombre>`. No distingue mayúsculas (`re.IGNORECASE`); para distinguirlas usa `(?-i:...)` dentro del patrón. El reemplazo se inserta tal cual, sin adaptar la capitalización.
- **Barras invertidas en TOML:** en una cadena con comillas dobles hay que duplicarlas (`"(\\d+) por ciento"`); con comillas simples se escriben tal cual (`'(\d+) por ciento' = '\1 %'`).
- **Orden:** primero la subtabla `[replacements.<idioma>]` del idioma usado en el dictado (en modo `auto`, el detectado), después la tabla plana; cada una en el orden en que aparece en el archivo. Cada regla ve la salida de la anterior, así que el orden en el archivo importa. Las subtablas de un idioma que nunca usas no tienen efecto; cualquier nombre de idioma es válido.
- **Texto vacío:** una regla puede borrar muletillas (`"eh+" = ""`). Si tras los reemplazos no queda texto, no se inserta ni se guarda nada y se registra `INFO` `Sin texto tras los reemplazos (... s, modelo/idioma).`.
- **Historial y log:** `original` en el historial y la línea `Texto original: ...` siguen siendo el texto de Whisper; `text` es el final, con puntuación y reemplazos. Los patrones y reemplazos no se escriben en el log.
- **Validación:** un valor que no sea texto, un patrón vacío, una regex que no compila (`"(" = "x"`), un reemplazo con un grupo inexistente (`"a" = "\\1"`) o un patrón que coincide con la cadena vacía (`"x*" = "y"`) hacen inválido el archivo; el error nombra `replacements.<clave>` (o `replacements.<idioma>.<clave>`) y la causa.
- **Cuidado:** una regla demasiado amplia se come texto válido (`"a" = ""`); revisa `Texto original` o el historial para ver qué cambió. Una regex con retroceso catastrófico puede congelar la transcripción: las reglas las escribes tú, y los dictados son cortos.

## Niveles de log

El nivel de la consola se elige con `--quiet`, `--verbose` o `--log-level` (excluyentes entre sí) y, si no se da ninguno, con `[log] level` (defecto `info`). El nivel del archivo `speechflow.log` solo se elige con `[log] file_level` (defecto `info`); las opciones de CLI no lo tocan, así que `--quiet` deja el archivo registrando igual que siempre.

| Nivel de consola | Se muestra | Banner |
| ---------------- | ---------- | ------ |
| `debug` | `DEBUG`, `INFO`, `WARNING` y `ERROR` | sí |
| `info` (defecto) | `INFO`, `WARNING` y `ERROR` | sí |
| `warning` | `WARNING` y `ERROR` | no |
| `error` | solo `ERROR` | no |

- **Orden de arranque:** el logger se crea con el nivel de la CLI (o `info`), se lee la configuración y entonces se aplican los niveles definitivos. Por eso las líneas de `resolve_config` (`Configuración: ...`) respetan la CLI pero no `[log] level`. El banner se imprime después de leer la configuración, así que `Configuración: ...` queda por encima de él.
- **`DEBUG`:** por ahora solo existe la línea `Niveles de log: consola=..., archivo=...`, que sale con consola en `debug` y llega al archivo si `file_level = "debug"`.
- **Notificaciones:** no dependen del nivel de log.
- **Privacidad:** con `file_level = "warning"` o `"error"` el archivo no guarda el texto dictado (`Insertado (...)`).
- Los niveles se leen solo al arrancar; cambiarlos exige reiniciar. Valores válidos en minúsculas.

```bash
speechflow --quiet                # consola solo con avisos y errores
speechflow --verbose              # consola con DEBUG
speechflow --log-level error
```

## Historial de transcripciones

Cada dictado con texto se guarda como una línea JSON en `$XDG_STATE_HOME/speechflow/history.jsonl` (defecto `~/.local/state/speechflow/history.jsonl`). Sirve para recuperar un dictado cuya inserción falló o cuya ventana cambió; la futura GUI lo leerá. Esta versión solo lo escribe: no hay subcomando para consultarlo.

```json
{"ts": "2026-10-13T10:42:07.318-05:00", "text": "Hola, mundo.", "original": "hola coma mundo punto", "language": "es", "model": "small", "audio_seconds": 2.4, "seconds": 0.61}
```

| Campo | Significado |
| ----- | ----------- |
| `ts` | Fecha y hora local, ISO 8601 con milisegundos y desfase. |
| `text` | Texto final, tal como se entrega a la inserción (tras la puntuación por voz). |
| `original` | Texto de Whisper antes de la puntuación por voz; igual a `text` si no hubo cambios o la función está apagada. |
| `language` | Idioma usado; en modo automático, el detectado. |
| `model` | Modelo cargado. |
| `audio_seconds` | Duración del audio, con 2 decimales. |
| `seconds` | Tiempo de transcripción, con 2 decimales. |

- **Cuándo se guarda:** después de la puntuación por voz y **antes** de insertar, así que queda guardado aunque la inserción falle. No se guardan los dictados sin texto reconocido (`Sin texto reconocido`) ni las grabaciones descartadas. No se guarda el audio.
- **Claves:** `[history] enabled` (`true` por defecto; `false` no crea ni escribe el archivo) y `[history] max_mb` (defecto `5`; mayor que 0). Se leen solo al arrancar.
- **Rotación:** al superar `max_mb` el archivo activo pasa a `history.jsonl.1`; se conservan `history.jsonl.1` (el más reciente) y `history.jsonl.2` (el más antiguo), así que el total no pasa de unas 3 veces `max_mb`. Los tres archivos se crean con permisos `0600`.
- **Fallos:** si el archivo no se puede abrir al arrancar, se registra `No se puede escribir el historial en <ruta>: <causa>. Se sigue sin historial.` y se dicta con normalidad. Si una escritura falla después, se registra una vez `No se pudo guardar el dictado en el historial: <causa>` (otra vez solo tras una escritura correcta) y el dictado se inserta igualmente.
- **Privacidad:** el historial guarda **en claro todo lo que dictas**, incluidas contraseñas o datos privados, y no se cifra. Los permisos `0600` solo lo protegen de otros usuarios del equipo. Para no guardarlo, pon `[history] enabled = false`. Para borrarlo: `rm ~/.local/state/speechflow/history.jsonl*`.
- **Consulta con `jq`:**

```bash
jq . ~/.local/state/speechflow/history.jsonl          # todas las entradas, legibles
tail -n 1 ~/.local/state/speechflow/history.jsonl | jq -r .text   # el último dictado
jq -r 'select(.language == "en") | .text' ~/.local/state/speechflow/history.jsonl*   # solo los dictados en inglés
```

## Modo solo CPU

Whisper puede ejecutarse sin GPU. La clave `[model] device` y la opción `--compute-device` (que gana sobre el TOML) aceptan:

| Valor | Comportamiento |
| ----- | -------------- |
| `auto` (defecto) | Usa la GPU si `ctranslate2.get_cuda_device_count()` es mayor que 0 y el modelo carga. Si no hay GPU, o la carga o el calentamiento fallan, libera lo cargado y reintenta en CPU con un `WARNING` que da el motivo, y envía la notificación `Sin GPU utilizable: se usa la CPU`. |
| `cpu` | Solo CPU, sin consultar CUDA. |
| `cuda` | Solo GPU. Si falla, el script sale con código 1 y un `ERROR` que sugiere `--compute-device cpu`; no cae a CPU. |

- **Hilos:** `[model] cpu_threads` (entero, `0` por defecto) fija los hilos de CPU de Whisper; `0` deja el valor por defecto de `faster-whisper`. Solo cuenta cuando el dispositivo resuelto es CPU; un valor negativo hace inválido el archivo.
- **Tipo de cómputo:** `int8` en CPU y en GPU.
- **Modelo por defecto:** si no fijas `--model` ni `[model] name`, se carga `small` cuando el dispositivo resuelto es CPU (incluido `auto` sin GPU o con la GPU fallida) y `medium` en GPU. Se registra `Modelo no fijado: se usa small por defecto en CPU.` Con `auto` sin modelo fijado, el log inicial dice `Cargando el modelo por defecto (int8, auto)...` y la notificación `Cargando modelo...`; el modelo real aparece tras cargar. La primera vez `small` se descarga de Hugging Face (~0.5 GB).
- **Log:** muestra el dispositivo y el modelo reales (`Cargando small (int8, CPU)...`, `Modelo: small | ... | CPU | ...`).
- **Forzar `medium` en CPU:** `--model medium` o `[model] name = "medium"`. Un modelo fijado se respeta siempre y, con `medium` o mayor en CPU, se registra un `WARNING` de lentitud que sugiere `small`.
- **Recargas:** tras la liberación por inactividad (`idle_timeout`) el modelo se recarga en el dispositivo ya resuelto, así que no se vuelve a intentar una GPU que falló.
- **Reinicio:** `device` y `cpu_threads` se leen solo al arrancar.
- **Entorno:** `environment.yml` no cambia; cuBLAS y cuDNN se instalan aunque en CPU no se usen.
- **Límite:** un fallo nativo del driver que aborte el proceso no se puede capturar; en ese caso usa `--compute-device cpu` o `CUDA_VISIBLE_DEVICES=""`.

```bash
speechflow --compute-device cpu                  # carga small
speechflow --compute-device cpu --model medium  # fuerza medium (lento)
CUDA_VISIBLE_DEVICES="" speechflow --compute-device cpu
```

## Servicio de usuario

`speechflow service` registra `speechflow` como servicio de `systemd --user`: arranca con la sesión gráfica, se reinicia si falla y su salida va a `journalctl`.

```bash
speechflow service install     # escribe la unidad, la habilita y la arranca
speechflow service status      # equivale a systemctl --user status speechflow
speechflow service uninstall   # desactiva, para y borra la unidad
```

- **Unidad:** `~/.config/systemd/user/speechflow.service` (respeta `XDG_CONFIG_HOME`). Usa el Python y el entorno conda desde los que ejecutaste `install`, por lo que el entorno no necesita estar activado en tiempo de ejecución. `LD_LIBRARY_PATH` apunta a `<entorno>/lib` para que se encuentren cuBLAS y cuDNN.
- **Logs:** `journalctl --user -u speechflow` (añade `-f` para seguirlos). El log rotativo de archivo sigue escribiéndose igual.
- **Control:** `systemctl --user stop|start|restart speechflow`. `Restart=on-failure` no reinicia tras una salida limpia (`stop`, cierre de sesión), pero sí tras un fallo; se detiene tras 5 fallos en 60 s.
- **Idempotente:** volver a ejecutar `install` reescribe la unidad pero no reinicia un servicio activo; aplica los cambios con `systemctl --user restart speechflow`.
- **Configuración:** el servicio no recibe opciones de la CLI (`--device`, `--model`...); configúralo con el TOML de la sección [Configuración](#configuración).
- **Requisito de sesión gráfica:** el servicio cuelga de `graphical-session.target` (GNOME) porque necesita `DISPLAY`, `XAUTHORITY` y el micrófono de la sesión. Si faltan `DISPLAY` o `XAUTHORITY` en otra sesión: `systemctl --user import-environment DISPLAY XAUTHORITY`. No arranca sin sesión (no usa `loginctl enable-linger`).
- **No ejecutes dos instancias:** una a mano y la del servicio capturarían la misma tecla y dictarían dos veces. Para usar `speechflow` en la terminal, para antes el servicio con `systemctl --user stop speechflow`.
- **Entorno movido o borrado:** si cambias de sitio o borras el entorno conda, la unidad queda apuntando a una ruta inexistente; vuelve a ejecutar `speechflow service install` desde el entorno nuevo.
- **Requisitos del servicio:** `install` falla con código 1 si falta `systemctl` o si la ruta del Python o del entorno contiene espacios o `%`.

## Configuración

La app de push-to-talk lee un archivo TOML opcional (solo ella; `capture_mic.py`, `benchmark_stt.py` y `--list-devices` no lo usan). Se usa el primero que exista, sin fusionar:

1. `--config RUTA` (si no existe, el script sale con `ERROR` y código 1).
2. `$XDG_CONFIG_HOME/speechflow/config.toml` (defecto `~/.config/speechflow/config.toml`), sea cual sea el directorio de trabajo.

Rutas de usuario (estándar XDG; una variable `XDG_*` vacía o con ruta relativa se ignora):

| Archivo | Ruta | Defecto |
| ------- | ---- | ------- |
| Configuración (la editas tú) | `$XDG_CONFIG_HOME/speechflow/config.toml` | `~/.config/speechflow/config.toml` |
| Plantilla de emergencia | `$XDG_CONFIG_HOME/speechflow/config.emergency.toml` | `~/.config/speechflow/config.emergency.toml` |
| Estado (lo escribe el script) | `$XDG_STATE_HOME/speechflow/state.toml` | `~/.local/state/speechflow/state.toml` |
| Log (lo escribe el script) | `$XDG_STATE_HOME/speechflow/speechflow.log` | `~/.local/state/speechflow/speechflow.log` |
| Historial (lo escribe el script) | `$XDG_STATE_HOME/speechflow/history.jsonl` | `~/.local/state/speechflow/history.jsonl` |

Las carpetas se crean al escribir la plantilla, el estado, el log o el historial. Un `speechflow.toml`, `speechflow.emergency.toml` o `.speechflow-state.toml` en la raíz del repo (rutas anteriores) se ignora y **no se migra** ni se avisa de ello: muévelos a mano a las rutas nuevas (`speechflow.toml` → `config.toml`, `.speechflow-state.toml` → `state.toml`).

**Log en archivo:** `speechflow.log` repite las líneas `INFO`, `WARNING` y `ERROR` de la consola (no el banner). Rota al llegar a 1 MB y conserva 3 copias (`speechflow.log.1` a `.3`), así que ocupa unos 4 MB como máximo. **Contiene el texto dictado** (`Insertado (...): {texto}`), por eso se crea con permisos `0600`. Para borrarlo: `rm ~/.local/state/speechflow/speechflow.log*`. Siempre está activo y no tiene opciones de configuración.

`speechflow.example.toml` es un ejemplo con todas las claves comentadas; cópialo a `~/.config/speechflow/config.toml`. Todas las claves son opcionales:

```toml
[model]
# name = "medium"           # sin fijar: medium en GPU, small en CPU; fijarlo lo usa en cualquier dispositivo
language = "es"                # "es", "en", otro idioma de Whisper, o "auto" (detecta entre es y en en cada dictado)
idle_timeout = 0.0          # segundos sin dictar antes de liberar el modelo de la GPU; 0 desactiva; mínimo 30.0
device = "auto"             # "auto": GPU si hay y funciona, si no CPU; "cpu": solo CPU; "cuda": solo GPU (falla si no hay)
cpu_threads = 0             # hilos de CPU para Whisper; 0 usa el defecto de faster-whisper
vad = true                  # filtra silencios y ruido sin voz antes de transcribir; false desactiva
# initial_prompt = ""       # contexto para Whisper en cada dictado; ej.: "Hablo de GitHub, PyTorch y Kubernetes."; vacío = sin prompt

[keys]
record = "ctrl_r"
switch = "f8"
language = "f7"             # alterna es <-> en en caliente
auto = "f6"                 # activa o desactiva la detección automática de idioma

[audio]
device = "Realtek"          # índice (entero) o parte del nombre; sin defecto
watch_interval = 3.0        # segundos entre comprobaciones de que el micrófono sigue conectado; mínimo 1.0

[recording]
min_seconds = 0.5
max_seconds = 60.0
mode = "hold"               # "hold": graba mientras mantienes la tecla; "toggle": una pulsación empieza y otra para

[notifications]
enabled = true

[text]
punctuation_commands = true # sustituye "punto", "coma", "nueva línea"... por su signo; false inserta lo que transcribe Whisper
insert_method = "clipboard" # "clipboard": copia y pega con Ctrl+V (Ctrl+Shift+V en terminales) y restaura el portapapeles; "type": teclea con xdotool
# terminal_classes = []     # clases de ventana extra que se pegan con Ctrl+Shift+V; ver: xprop -id $(xdotool getwindowfocus) WM_CLASS

[log]
level = "info"              # nivel de la consola: "debug", "info", "warning" o "error"; --quiet, --verbose y --log-level ganan
file_level = "info"         # nivel del archivo speechflow.log; las opciones de CLI no lo cambian

[history]
enabled = true              # guarda cada dictado en history.jsonl (texto en claro, permisos 0600); false no crea el archivo
max_mb = 5.0                # tamaño máximo del archivo activo antes de rotar (se conservan 2 copias); mayor que 0

[replacements]              # "regex" = "reemplazo"; ver "Diccionario de reemplazos e initial_prompt"
# "git ?hub" = "GitHub"

# [replacements.es]         # solo si el idioma del dictado es es; antes que la tabla plana
# "cuber ?netis" = "Kubernetes"
```

**Precedencia por valor:** argumento de CLI (solo si se escribió) > estado guardado (solo dispositivo e idioma) > archivo > defectos. En concreto, el dispositivo es `--device` > `state.toml` > `[audio] device` > el que contenga "Realtek", si no el del sistema, y el idioma es `--language` > `state.toml` > `[model] language` > `es`.

**Validación:** una clave o sección desconocida, un tipo incorrecto, `min_seconds <= 0` o `max_seconds <= min_seconds` o `watch_interval < 1.0`, un `idle_timeout` distinto de 0 y menor que 30.0, un `device` que no sea `"auto"`, `"cpu"` ni `"cuda"` (el error nombra `model.device`), un `cpu_threads` negativo (nombra `model.cpu_threads`), un `mode` que no sea `"hold"` ni `"toggle"`, un `punctuation_commands` que no sea `true` ni `false` (por ejemplo `"si"`), un `[text] insert_method` que no sea `"clipboard"` ni `"type"` (el error nombra `text.insert_method`), un `[text] terminal_classes` que no sea una lista de textos no vacíos (nombra `text.terminal_classes`), o un `[log] level` o `[log] file_level` que no sea `"debug"`, `"info"`, `"warning"` ni `"error"` (el error nombra `log.level` o `log.file_level`), un `[history] enabled` que no sea `true` ni `false` (nombra `history.enabled`), un `[history] max_mb` que no sea un número o sea menor o igual que 0 (nombra `history.max_mb`), un `[model] initial_prompt` que no sea texto (nombra `model.initial_prompt`), o un `[replacements]` inválido (nombra `replacements.<clave>`, ver [Diccionario de reemplazos e `initial_prompt`](#diccionario-de-reemplazos-e-initial_prompt)) hacen inválido el archivo. Las teclas se siguen validando al arrancar con mensajes `ERROR` que nombran la clave (`--key`, `--switch-key`, `[keys] language`, `[keys] auto`); si dos de las cuatro coinciden, el script sale con código 1 y nombra las dos.

**Archivo de emergencia:** si no se encuentra ningún archivo, o el encontrado no se puede leer o no es válido, el script registra un `WARNING` con la causa, crea `config.emergency.toml` junto al archivo de configuración con todos los valores por defecto (sin sobrescribirlo si ya existe) y sigue con los defectos. El archivo inválido del usuario no se toca. La plantilla de emergencia no se lee nunca: cópiala o renómbrala a `config.toml` para usarla.

```
2026-10-05 14:32:02.580 WARNING Configuración inválida en /home/usuario/.config/speechflow/config.toml: clave desconocida model.modle. Se usan los valores por defecto; plantilla en /home/usuario/.config/speechflow/config.emergency.toml.
2026-10-05 14:32:02.580 INFO    Configuración: valores por defecto
```

**Micrófono guardado:** cada cambio efectivo con `--switch-key` escribe el **nombre** del dispositivo en `state.toml` (en `$XDG_STATE_HOME/speechflow/`; lo escribe el script, no se edita a mano). Al arrancar se usa ese micrófono salvo que se pase `--device`. Si ya no está disponible (por ejemplo, un USB desenchufado), se registra un `WARNING`, se envía la notificación `Micrófono guardado no disponible: {nombre}` y se usa el siguiente nivel de la precedencia. Ese micrófono no se vigila: el hilo vigila el que se haya elegido al arrancar.

**Idioma guardado:** cada cambio con `[keys] language` o `[keys] auto` escribe `language` (`"es"`, `"en"`, `"auto"`, ...) en `state.toml`, junto a `device` sin pisarse:

```toml
device = "Realtek ALC1220"
language = "auto"
```

Al arrancar se usa ese idioma salvo que se pase `--language`. **Ojo:** mientras exista `language` en `state.toml`, editar `[model] language` no tiene efecto; para volver al valor del TOML basta borrar esa línea de `state.toml`. Un `language` que no sea texto o esté vacío se ignora con un `WARNING`. El último idioma fijo (al que vuelve auto) no se guarda: arrancar en auto equivale a empezar con `es`.

Estos archivos viven fuera del repo; en el repo solo se versiona `speechflow.example.toml`.

## Captura del micrófono

`scripts/capture_mic.py` es una prueba de la cadena micrófono → WAV → texto: graba entre dos pulsaciones de Enter, guarda `benchmarks/captures/capture.wav` (no versionado), muestra duración, pico y RMS, y transcribe el audio con `faster-whisper` (`int8`, GPU).

```bash
python scripts/capture_mic.py --list-devices   # lista los dispositivos de entrada
python scripts/capture_mic.py                  # graba con el dispositivo preferido y transcribe
python scripts/capture_mic.py --device 6       # índice o nombre de otro dispositivo
python scripts/capture_mic.py --model small --language en
```

Flujo: Enter para empezar, hablar, Enter para parar. Salida de ejemplo:

```
Guardado benchmarks/captures/capture.wav
Duración: 16.62 s | Pico: 0.116 | RMS: 0.0171
Transcripción (1.26 s): Existe muchísima documentación sobre lenguajes ensamblador...
```

Opciones:

| Opción | Descripción | Defecto |
| ------ | ----------- | ------- |
| `--list-devices` | Lista los dispositivos de entrada y termina (`>` marca el del sistema). | — |
| `--device` | Índice o nombre del dispositivo de entrada. Falla con un mensaje claro si no existe. | primero que contenga "Realtek"; si no, el del sistema |
| `--model` | Modelo de `faster-whisper`. | `medium` |
| `--language` | Idioma de la transcripción. | `es` |
| `--output` | Ruta del WAV de salida. | `benchmarks/captures/capture.wav` |

- **Dispositivo:** sin `--device`, usa el primero cuyo nombre contenga "Realtek" (micrófono USB); si no hay, el del sistema. Si hay dudas sobre cuál se usa, ejecuta `--list-devices`.
- **Remuestreo:** en este equipo los dispositivos `hw:` de ALSA rechazan 16 kHz (`Invalid sample rate`) y solo aceptan su tasa nativa (44 100 Hz). Por eso el script graba a esa tasa y remuestrea a 16 kHz con `scipy.signal.resample_poly`. El WAV final es mono, 16 kHz, 16 bits, el formato nativo de Whisper descrito arriba.
- **Aviso de silencio:** si el pico es menor a 0.01 se avisa por stderr (posible micrófono mudo o equivocado). El ruido de fondo de un micrófono real puede superar ese umbral, así que el aviso solo detecta dispositivos casi mudos (p. ej. un `Loopback`).
- **Latencia:** la transcripción se mide sin contar la carga del modelo (hay un calentamiento previo). Con `medium` int8 en la GTX 1060, ~16 s de audio tardaron 1.26 s. El modelo se carga después de grabar, así que hay una espera antes de ver el texto.

## Desarrollo y tests

Con el extra `dev` instalado (`pip install -e .[dev]`) y el entorno `speechflow` activado:

```bash
pytest                # suite por defecto: sin micrófono, GPU, xdotool ni notify-send
pytest -m gpu         # smoke test con el modelo real
env -u DISPLAY pytest # sin servidor X (por ejemplo, en una terminal o un contenedor)
```

- **Suite por defecto:** cubre `config`, `audio`, `log`, `notifier`, `inserter`, `transcriber`, los helpers de `app.py` y `PushToTalk`, con dobles de `sounddevice`, `Recorder`, `Transcriber`, `notify` e `insert_text`. Ninguna prueba abre un micrófono, ejecuta `xclip`, `xdotool` o `notify-send`, ni carga un modelo. `HOME`, `XDG_CONFIG_HOME` y `XDG_STATE_HOME` apuntan a una carpeta temporal en cada test, así que la configuración real no se toca. Tarda unos segundos. Quedan fuera `main()` y las pruebas de integración con hardware, que se verifican a mano.
- **Smoke test de GPU (`pytest -m gpu`):** los tests marcados `gpu` se excluyen por defecto (`addopts = "-m 'not gpu'"` en `pyproject.toml`). El único que hay carga `Transcriber()` con el modelo por defecto (`medium`), transcribe un segundo de silencio y llama a `close()` dos veces. Requiere una GPU NVIDIA con CUDA y el modelo `medium` ya descargado en la caché de Hugging Face.
- **Sin servidor X:** si `DISPLAY` no está definido, `tests/conftest.py` fija `PYNPUT_BACKEND=dummy` antes de importar `speechflow.app`. Con ese backend todas las teclas de `pynput.keyboard.Key` valen lo mismo, así que los tests de `parse_key` que lo necesitan se saltan; el resto pasa.
