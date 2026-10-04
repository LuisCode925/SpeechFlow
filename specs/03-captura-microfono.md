# SPEC 03 — Prueba de captura de audio del micrófono

> **Estado:** Aprobado
> **Depende de:** SPEC 01, SPEC 02
> **Fecha:** 2026-10-04
> **Objetivo:** Verificar con un script que `sounddevice` captura audio del micrófono en Debian 13, lo guarda como WAV mono 16 kHz y que `faster-whisper` lo transcribe.

## Por qué existe esta spec

Las SPEC 01 y 02 fijaron el stack y el modelo (`medium` int8), pero solo con audios ya grabados. Antes de construir el push-to-talk hay que comprobar que la captura en vivo funciona: dispositivo de entrada, formato y que la cadena micrófono → WAV → texto produce una transcripción útil. Esta spec es una prueba, no la funcionalidad final.

## Alcance

**Dentro:**

- Añadir `sounddevice` y `portaudio` (conda-forge) a `environment.yml`.
- Crear `scripts/capture_mic.py`: lista dispositivos de entrada, graba del micrófono entre dos pulsaciones de Enter, guarda un WAV mono 16 kHz, reporta métricas y lo transcribe con `faster-whisper`.
- Opciones: `--list-devices`, `--device` (índice o nombre), `--model` (defecto `medium`), `--language` (defecto `es`), `--output` (defecto `benchmarks/captures/capture.wav`).
- Reportar duración, pico y RMS del audio capturado y la latencia de transcripción.
- Añadir `benchmarks/captures/` a `.gitignore`.
- Documentar el uso en `README.md`.

**Fuera de alcance (para futuras specs):**

- Atajo global y push-to-talk con tecla mantenida (`pynput`).
- Inserción del texto con `xdotool type`.
- Icono de bandeja, daemon y VAD.
- Streaming de audio hacia el modelo mientras se graba.
- Módulo reutilizable en `src/speechflow/`; el código vive solo en el script.
- Reducción de ruido, normalización de volumen y selección automática de micrófono.
- Medir calidad (WER) de la transcripción.

## Modelo de datos

No hay estructuras persistentes nuevas. Constantes del script y resultado en memoria:

```python
SAMPLE_RATE = 16000   # Hz, nativo de Whisper
CHANNELS = 1          # mono
DTYPE = "int16"

# Resultado en memoria, impreso por consola
{
    "device": "name",
    "audio_seconds": 0.0,
    "peak": 0.0,              # 0.0–1.0
    "rms": 0.0,               # 0.0–1.0
    "transcribe_seconds": 0.0,
    "text": "",
}
```

Archivo que aparece: `benchmarks/captures/capture.wav` (no versionado).

## Plan de implementación

1. Añadir `portaudio` y `sounddevice` a `environment.yml` y actualizar el entorno. Verificar: `python -c "import sounddevice; print(sounddevice.query_devices())"` lista al menos un dispositivo de entrada.
2. Crear `scripts/capture_mic.py` con `--list-devices`, que imprime índice, nombre y canales de entrada de cada dispositivo. Añadir `benchmarks/captures/` a `.gitignore`. Verificar: `python scripts/capture_mic.py --list-devices` muestra el micrófono.
3. Implementar la grabación: abrir `sounddevice.InputStream` a 16 kHz mono `int16`, empezar con Enter, parar con Enter, y guardar el WAV con el módulo `wave`. Verificar: el WAV generado se reproduce con `aplay` y dura lo grabado.
4. Calcular y mostrar duración, pico y RMS. Avisar por stderr si el pico es menor a 0.01 (posible micrófono mudo o equivocado). Verificar: grabar en silencio produce el aviso; hablar no.
5. Transcribir el WAV con `faster-whisper` (`--model`, `--language`, `int8`, GPU), imprimiendo texto y latencia. Verificar: decir una frase en español y ver su transcripción.
6. Actualizar `README.md` con la sección de captura. Verificar: el README coincide con las opciones reales del script.

## Criterios de aceptación

- [ ] `conda env update -f environment.yml` termina sin errores y `import sounddevice` funciona.
- [ ] `python scripts/capture_mic.py --list-devices` lista al menos un dispositivo de entrada.
- [ ] `python scripts/capture_mic.py` graba entre dos pulsaciones de Enter y escribe `benchmarks/captures/capture.wav`.
- [ ] El WAV resultante es mono, 16 000 Hz, 16 bits (verificable con `soxi` o `ffprobe`).
- [ ] La salida muestra duración, pico y RMS; hablar da un pico mayor a 0.01.
- [ ] Una frase de ~10 s en español dicha al micrófono se transcribe con texto reconocible.
- [ ] La transcripción de ~10 s tarda menos de 2 s con `medium` int8, sin contar la carga del modelo.
- [ ] `--device` permite elegir otro dispositivo de entrada y el script falla con un mensaje claro si no existe.
- [ ] `benchmarks/captures/` no está versionado en git.
- [ ] `README.md` documenta el script y sus opciones.

## Decisiones

- **Sí:** script en `scripts/capture_mic.py`, por elección del usuario. Es una prueba; el módulo reutilizable en `src/speechflow/` llegará con la funcionalidad real.
- **No:** `src/speechflow/audio.py` ahora. Diseñar la API antes de validar el micrófono sería adivinar.
- **Sí:** Enter para iniciar y parar, por elección del usuario. Simula el push-to-talk sin añadir `pynput`.
- **No:** duración fija. Descartada por el usuario; no refleja el uso real.
- **Sí:** capturar directo a 16 kHz mono `int16`. Es el formato nativo de Whisper y evita remuestrear (ver `README.md`).
- **Sí:** transcribir en el mismo script con el modelo por defecto `medium` int8 de la SPEC 02, para validar la cadena completa mic → texto.
- **Sí:** dispositivo por defecto del sistema, con `--list-devices` y `--device`, por elección del usuario. Facilita depurar si el micrófono equivocado se usa.
- **Sí:** `sounddevice` con `portaudio` de conda-forge, coherente con la SPEC 01 y con conda como gestor.
- **No:** `pyaudio`. Instalación más frágil y sin ventaja para este caso.
- **Sí:** el WAV se guarda en `benchmarks/captures/` y no se versiona, para no subir voz personal (igual que las muestras).

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El dispositivo por defecto no es el micrófono (hay `Loopback` y `Alt Analog` en `arecord -l`) | `--list-devices` y `--device`; aviso si el pico es menor a 0.01. |
| El dispositivo no soporta 16 kHz de forma nativa | PortAudio/ALSA remuestrea; si falla, el script muestra el error y se documenta en el README. |
| Entorno sin `portaudio` en el sistema | Se instala desde conda-forge dentro del entorno. |
| Enter pulsado con latencia añade silencio al inicio y fin | Aceptado en la prueba; el recorte con VAD va en otra spec. |

## Lo que **no** está en esta spec

- Push-to-talk con atajo global, inserción de texto, bandeja, daemon y VAD.
- Streaming, reducción de ruido y módulo reutilizable en `src/speechflow/`.
- Medición de WER.

Cada uno, si se aborda, va en su propia spec.
