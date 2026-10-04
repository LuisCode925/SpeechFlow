# SPEC 01 — Stack tecnológico, esqueleto del proyecto y benchmark de STT

> **Estado:** Aprobado
> **Depende de:** ninguna
> **Fecha:** 2026-10-04
> **Objetivo:** Fijar el stack tecnológico de SpeechFlow, crear el esqueleto del proyecto y verificar con un benchmark que Whisper corre en la GTX 1060 dentro del objetivo de latencia.

## Por qué existe esta spec

SpeechFlow es una herramienta de dictado por voz para todo el sistema (ver `README.md`). Antes de escribir funcionalidad hay que validar que el hardware objetivo (Ryzen 7 3700X, GTX 1060 6 GB, 16 GB RAM, Debian 13) alcanza una latencia fluida con un motor local. La GTX 1060 es Pascal (compute 6.1) y no tiene FP16 rápido, así que la cuantización y el modelo elegido deben medirse y no suponerse.

## Alcance

**Dentro:**

- Registrar el stack elegido (ver Decisiones).
- Crear `environment.yml` (conda) con Python y las dependencias del stack.
- Crear la estructura de carpetas del paquete `speechflow`.
- Crear `scripts/benchmark_stt.py`, que mide carga del modelo y latencia de transcripción con `faster-whisper` en GPU (CUDA) para los modelos `small` y `medium` en `int8`.
- Documentar en `README.md` cómo crear el entorno y ejecutar el benchmark.
- Guardar el resultado del benchmark en `benchmarks/results.md` para decidir el modelo por defecto.

**Fuera de alcance (para futuras specs):**

- Captura de audio desde el micrófono (`sounddevice`).
- Atajo global push-to-talk y su valor por defecto.
- Inserción de texto con `xdotool type`.
- Icono de bandeja y daemon.
- VAD (`silero-vad`).
- Soporte Wayland.
- Streaming de transcripción en tiempo real.
- Ventana de configuración y archivo de configuración de usuario.
- Fallback a CPU o a API en la nube.

## Modelo de datos

Esta spec no introduce estructuras de datos persistentes. El benchmark produce únicamente un resultado en memoria que se imprime y se vuelca a `benchmarks/results.md`:

```python
# Resultado por (modelo, muestra) — solo en memoria
{
    "model": "small",          # "small" | "medium"
    "compute_type": "int8",
    "sample": "es_10s.wav",
    "audio_seconds": 10.0,
    "load_seconds": 0.0,       # carga del modelo (una sola vez por modelo)
    "transcribe_seconds": 0.0, # tiempo de model.transcribe + consumo del generador
    "vram_mb": 0,              # pico de VRAM medido con nvidia-smi
    "text": "",
}
```

Estructura de carpetas que aparece:

```text
environment.yml
scripts/benchmark_stt.py
src/speechflow/__init__.py
benchmarks/samples/      # WAV de prueba, ignorados por git
benchmarks/results.md    # resultado commiteado
```

## Plan de implementación

1. Crear `environment.yml` con el entorno conda `speechflow` (Python 3.12 o 3.13 según disponibilidad de wheels de `ctranslate2`) y `faster-whisper`. Verificar: `conda env create -f environment.yml` termina sin errores y `python -c "import faster_whisper"` funciona.
2. Resolver las librerías CUDA (cuBLAS y cuDNN compatibles con `ctranslate2`) dentro del entorno conda. Verificar: `python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"` imprime `1`.
3. Crear `src/speechflow/__init__.py` vacío (con `__version__`) y añadir `benchmarks/samples/` al `.gitignore`. Verificar: `python -c "import speechflow"` con `src` en el path.
4. Crear `scripts/benchmark_stt.py` con carga de un modelo e inferencia sobre un WAV pasado por argumento, imprimiendo tiempos. Verificar: ejecutarlo con un WAV de ejemplo y ver texto y tiempos.
5. Extender el script para recorrer `small` y `medium` en `int8`, medir pico de VRAM con `nvidia-smi` y escribir `benchmarks/results.md`. Verificar: el archivo se genera con una fila por modelo y muestra.
6. Añadir a `README.md` la sección de instalación y ejecución del benchmark. Verificar: seguir el README desde cero reproduce el resultado.

## Criterios de aceptación

- [ ] `conda env create -f environment.yml` crea el entorno `speechflow` sin errores en Debian 13.
- [ ] `ctranslate2.get_cuda_device_count()` devuelve `1` dentro del entorno.
- [ ] `python scripts/benchmark_stt.py` transcribe al menos un WAV en español y uno en inglés de `benchmarks/samples/` con `small` y `medium` en `int8` sobre GPU.
- [ ] `benchmarks/results.md` contiene tiempo de carga, tiempo de transcripción, duración del audio y pico de VRAM por cada combinación modelo/muestra.
- [ ] Al menos un modelo transcribe una muestra de ~10 s en menos de 2 s (sin contar la carga del modelo), o `results.md` documenta explícitamente que ninguno lo logra.
- [ ] El pico de VRAM de cada modelo es menor a 6 GB.
- [ ] `results.md` indica qué modelo queda como defecto para la siguiente spec.
- [ ] `benchmarks/samples/` no está versionado en git.
- [ ] `README.md` explica cómo crear el entorno y ejecutar el benchmark.

## Decisiones

- **Sí:** Python como lenguaje principal. `faster-whisper`, `sounddevice`, `pynput` y `silero-vad` están maduros, y el rendimiento lo da el motor nativo (CTranslate2/CUDA), no Python.
- **No:** Rust y C++. Mayor costo de desarrollo para un MVP; solo se justifican si Python resulta ser el cuello de botella.
- **Sí:** reconocimiento 100 % local en GPU. Privacidad, sin costo, sin internet.
- **No:** CPU como motor principal ni API en la nube. Más lento y con audio saliendo de la máquina, respectivamente.
- **Sí:** `faster-whisper` (CTranslate2) con cuantización `int8`. Pascal no tiene FP16 rápido, y `int8` reduce VRAM y tiempo.
- **Sí:** modelos multilingües `small` y `medium` para español e inglés.
- **Sí:** comparar `small` y `medium` en el benchmark y decidir el defecto con datos, no antes.
- **Sí:** conda como gestor de entorno, por elección del usuario.
- **No:** `uv`, `venv + pip` y Poetry. Descartados al elegir conda.
- **Sí:** X11 como servidor gráfico objetivo del MVP. `xdotool` y los atajos globales son simples y fiables.
- **No:** Wayland en el MVP. Exige `ydotool`/portales y permisos adicionales.
- **Sí:** activación por push-to-talk (mantener tecla). Sin falsos positivos y más simple que VAD continuo. El atajo concreto queda sin definir y será configurable en otra spec.
- **Sí:** inserción de texto con tecleo simulado (`xdotool type`), por elección del usuario, sin tocar el portapapeles. Es más lento y puede fallar con caracteres especiales según el layout; esto se validará en la spec de inserción.
- **Sí:** interfaz como daemon con icono de bandeja, en una spec posterior.
- **Sí:** objetivo de latencia < 2 s para frases de ~10 s, medido desde que termina el audio hasta tener el texto.
- **Sí:** las muestras de audio las aporta el usuario en `benchmarks/samples/` y no se versionan, para no inflar el repo ni subir voz personal.

## Riesgos

| Riesgo                                                                  | Mitigación                                                                                          |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Driver NVIDIA/CUDA de Debian 13 incompatible con las libs de CTranslate2 | Fijar versiones de cuBLAS/cuDNN en `environment.yml` y documentar la versión de driver en el README. |
| `medium` supera 2 s en la GTX 1060                                      | El benchmark lo registra; el defecto pasa a `small` y se documenta en `results.md`.                 |
| Sin wheels de `ctranslate2` para la versión de Python elegida           | Usar una versión de Python anterior en `environment.yml` (p. ej. 3.12).                             |
| Faltan muestras de audio                                                | El script falla con un mensaje claro indicando la carpeta y el formato esperado (WAV mono 16 kHz).  |

## Lo que **no** está en esta spec

- Captura de micrófono, atajo global, inserción de texto, bandeja y VAD.
- Soporte Wayland.
- Fallback a CPU o nube.
- Configuración de usuario.

Cada uno, si se aborda, va en su propia spec.
