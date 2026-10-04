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
- GPU NVIDIA con driver compatible con CUDA 12 (probado con GTX 1060 6 GB y driver 550.163.01).
- [Conda](https://docs.conda.io/) (miniconda o similar).
- Para el push-to-talk, paquetes de sistema: `sudo apt install xdotool libnotify-bin` (`xdotool` es obligatorio; `libnotify-bin` aporta `notify-send` y es opcional).

## Instalación

```bash
conda env create -f environment.yml
conda activate speechflow
```

El entorno incluye Python 3.12, `faster-whisper`, `sounddevice` (con `portaudio`), `scipy`, `pynput`, y cuBLAS y cuDNN (CUDA 12) desde conda-forge.

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

`src/speechflow/transcriber.py` define `Transcriber`, que carga `faster-whisper` una sola vez (GPU, `int8`), hace un calentamiento y transcribe cuantas veces se quiera sin recargar el modelo.

```python
import sys
import wave

import numpy as np

sys.path.insert(0, "src")
from speechflow.transcriber import Transcriber

transcriber = Transcriber("medium", "es")  # carga y calienta el modelo una vez

with wave.open("benchmarks/captures/capture.wav", "rb") as wav:
    audio = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)

text, seconds = transcriber.transcribe(audio)
print(f"{seconds:.2f} s: {text}")
```

- **Entrada:** `numpy.ndarray` `int16`, mono, a 16 kHz. El módulo no valida la tasa: un audio a otra tasa da transcripciones erróneas sin aviso.
- **Salida:** `(texto, segundos)`. Los segundos no incluyen la carga del modelo ni el calentamiento. Un array vacío devuelve `("", 0.0)` sin invocar al modelo.
- **Parámetros:** modelo (defecto `medium`) e idioma (defecto `es`, fijo, sin detección automática).
- `scripts/capture_mic.py` usa este módulo.

## Módulos de captura, inserción y notificación

- `src/speechflow/audio.py`: dispositivos de entrada, remuestreo, medición, guardado de WAV y `Recorder` (`start()` / `stop()`), que graba a la tasa nativa del dispositivo y devuelve `int16` mono a 16 kHz. Lo usan `capture_mic.py` y `push_to_talk.py`.
- `src/speechflow/inserter.py`: `insert_text(text)` escribe el texto en la ventana con foco con `xdotool type --clearmodifiers`.
- `src/speechflow/notifier.py`: `notify(title, body)` envía una notificación de escritorio con `notify-send`; si no está instalado, no hace nada.

## Push-to-talk

`scripts/push_to_talk.py` permite dictar en cualquier aplicación de X11: mantén pulsada una tecla global (`Right Ctrl` por defecto), habla, y al soltarla el texto se escribe en la ventana con foco. Se ejecuta en primer plano y termina con `Ctrl+C`.

```bash
python scripts/push_to_talk.py --list-devices   # lista los dispositivos de entrada
python scripts/push_to_talk.py                  # Right Ctrl, modelo medium, español
python scripts/push_to_talk.py --key f9         # otra tecla de disparo
python scripts/push_to_talk.py --device 6 --model small --language en
```

Salida de ejemplo:

```
Cargando medium (int8, GPU)...
Listo. Mantén pulsada la tecla 'ctrl_r' para dictar. Ctrl+C para salir.
Grabando...
Grabación terminada: 11.18 s. Transcribiendo...
Insertado (1.03 s): El juego de la pelota prehispánico, que se practicaba a lo largo del territorio...
```

Opciones:

| Opción | Descripción | Defecto |
| ------ | ----------- | ------- |
| `--list-devices` | Lista los dispositivos de entrada y termina (`>` marca el del sistema). | — |
| `--device` | Índice o nombre del dispositivo de entrada. Falla con un mensaje claro si no existe. | primero que contenga "Realtek"; si no, el del sistema |
| `--model` | Modelo de `faster-whisper`. | `medium` |
| `--language` | Idioma de la transcripción. | `es` |
| `--key` | Tecla de disparo: nombre de `pynput.keyboard.Key` (`ctrl_r`, `f9`, ...) o un carácter suelto. Falla con un mensaje claro si no existe. | `ctrl_r` |

- **Modelo:** se carga una sola vez al arrancar, así que cada dictado responde rápido. Con `medium` int8 en la GTX 1060, ~11 s de audio tardaron 1.03 s.
- **Grabaciones cortas:** las de menos de 0.5 s se descartan sin invocar al modelo (evita escribir texto basura por toques accidentales).
- **Límite:** a los 60 s la grabación se corta sola, se transcribe lo grabado y se avisa. No empieza otra hasta soltar la tecla y volver a pulsarla.
- **Durante la transcripción:** pulsar la tecla no inicia otra grabación.
- **Avisos:** se muestran por consola y como notificación de escritorio (grabando, transcribiendo, texto insertado, error). Si falta `notify-send`, se avisa una vez y sigue funcionando solo con consola.
- **Requisitos:** sesión X11 y `xdotool` instalado; si falta, el script sale al arrancar indicando `sudo apt install xdotool`.
- **Foco:** el texto se escribe en la ventana que tenga el foco cuando termina la transcripción. Si cambias de ventana mientras se transcribe, se escribirá en la nueva.
- **Una sola instancia:** no ejecutes dos a la vez; ambas reaccionarían a la misma tecla y competirían por el micrófono.

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
