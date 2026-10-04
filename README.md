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

## Instalación

```bash
conda env create -f environment.yml
conda activate speechflow
```

El entorno incluye Python 3.12, `faster-whisper`, `sounddevice` (con `portaudio`), `scipy`, y cuBLAS y cuDNN (CUDA 12) desde conda-forge.

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

## Captura del micrófono

`scripts/capture_mic.py` es una prueba de captura: graba entre dos pulsaciones de Enter y guarda `benchmarks/captures/capture.wav` (no versionado).

```bash
python scripts/capture_mic.py --list-devices   # lista los dispositivos de entrada
python scripts/capture_mic.py                  # graba con el dispositivo preferido
python scripts/capture_mic.py --device 6       # índice o nombre de otro dispositivo
```

- **Dispositivo:** sin `--device`, usa el primero cuyo nombre contenga "Realtek" (micrófono USB); si no hay, el del sistema.
- **Remuestreo:** en este equipo los dispositivos `hw:` de ALSA rechazan 16 kHz (`Invalid sample rate`) y solo aceptan su tasa nativa (44 100 Hz). Por eso el script graba a esa tasa y remuestrea a 16 kHz con `scipy.signal.resample_poly`. El WAV final es mono, 16 kHz, 16 bits, el formato nativo de Whisper descrito arriba.
