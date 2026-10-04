# SPEC 04 — Módulo de transcripción reutilizable

> **Estado:** Aprobado
> **Depende de:** SPEC 02, SPEC 03
> **Fecha:** 2026-10-04
> **Objetivo:** Extraer la transcripción de `scripts/capture_mic.py` a un módulo reutilizable `src/speechflow/transcriber.py` que carga el modelo una sola vez y transcribe audio mono 16 kHz `int16`.

## Por qué existe esta spec

La SPEC 03 validó la cadena micrófono → WAV → texto, pero la transcripción vive dentro del script y carga el modelo en cada llamada a `transcribe()`. El push-to-talk necesita cargar `medium` una vez y transcribir muchas veces con baja latencia. Esta spec convierte la prueba en un componente real, sin tocar la captura ni añadir funcionalidad nueva.

## Alcance

**Dentro:**

- Crear `src/speechflow/transcriber.py` con la clase `Transcriber`: carga `WhisperModel` una sola vez (GPU, `int8`), hace un calentamiento y expone `transcribe(audio)`.
- Idioma fijo por parámetro del constructor (defecto `es`), sin detección automática.
- Modelo por parámetro del constructor (defecto `medium`, según la SPEC 02).
- Modificar `scripts/capture_mic.py` para que use `Transcriber` en lugar de su función `transcribe()` local, que se elimina junto con las constantes que ya no use.
- Mantener sin cambios las opciones, la salida y el comportamiento de `capture_mic.py`.
- Actualizar `README.md` con una breve sección del módulo.

**Fuera de alcance (para futuras specs):**

- Extraer captura, remuestreo o `save_wav` a `src/speechflow/audio.py`.
- Detección automática de idioma y cambio de idioma en caliente.
- Transcripción en streaming o por trozos, y VAD.
- Atajo global push-to-talk, inserción de texto con `xdotool`, bandeja y daemon.
- Empaquetado del proyecto (`pyproject.toml`, `pip install -e .`).
- Tests automatizados con `pytest`.
- Fallback a CPU, otros modelos o compute types distintos de `int8`.
- Medir calidad (WER).

## Modelo de datos

No hay estructuras persistentes nuevas. Interfaz pública del módulo (firma, no implementación):

```python
# src/speechflow/transcriber.py
SAMPLE_RATE = 16000   # Hz, nativo de Whisper
COMPUTE_TYPE = "int8"
DEFAULT_MODEL = "medium"
DEFAULT_LANGUAGE = "es"

class Transcriber:
    def __init__(self, model_name: str = DEFAULT_MODEL, language: str = DEFAULT_LANGUAGE) -> None: ...
    def transcribe(self, audio: np.ndarray) -> tuple[str, float]: ...
    # audio: int16 mono a SAMPLE_RATE. Devuelve (texto, segundos de transcripción).
    # Los segundos no incluyen la carga del modelo ni el calentamiento.
```

Convenciones:

- Un audio vacío devuelve `("", 0.0)` sin invocar al modelo.
- La conversión `int16` → `float32` (`/ 32768`) vive dentro de `transcribe()`.

## Plan de implementación

1. Crear `src/speechflow/transcriber.py` con `Transcriber`: el constructor carga el modelo y hace el calentamiento; `transcribe()` convierte a `float32`, transcribe y mide el tiempo. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.transcriber import Transcriber; print(Transcriber)"` no falla.
2. Cambiar `scripts/capture_mic.py` para importar `Transcriber` (añadiendo `src/` a `sys.path` al inicio del script), crearlo tras grabar y llamar a `transcriber.transcribe(audio)`. Eliminar su `transcribe()` local y las importaciones y constantes sin uso (`WhisperModel`, `COMPUTE_TYPE`, `DEFAULT_MODEL`, `DEFAULT_LANGUAGE` si pasan al módulo). Verificar: `python scripts/capture_mic.py`, decir una frase en español y ver la misma salida que antes.
3. Verificar el módulo sin micrófono con un WAV existente: leer `benchmarks/captures/capture.wav` con `wave` y `numpy`, transcribirlo dos veces con la misma instancia y comprobar que la segunda llamada no recarga el modelo. Verificar: el texto coincide con el de la grabación y la segunda llamada no tarda más que la primera.
4. Actualizar `README.md`: sección del módulo con el ejemplo de uso y la nota de que `capture_mic.py` lo usa. Verificar: el ejemplo del README se ejecuta tal cual.

## Criterios de aceptación

- [ ] `src/speechflow/transcriber.py` existe y define `Transcriber` con `transcribe(audio)`.
- [ ] `Transcriber("medium", "es")` carga el modelo una sola vez; dos llamadas seguidas a `transcribe()` no vuelven a cargarlo.
- [ ] `transcribe()` recibe `int16` mono a 16 kHz y devuelve `(texto, segundos)`.
- [ ] `transcribe()` con un array vacío devuelve `("", 0.0)` sin error.
- [ ] `python scripts/capture_mic.py` graba, guarda el WAV y muestra la transcripción con el mismo formato de salida que antes.
- [ ] `scripts/capture_mic.py` ya no contiene `WhisperModel` ni una función `transcribe()` propia.
- [ ] Las opciones `--list-devices`, `--device`, `--model`, `--language` y `--output` siguen funcionando igual.
- [ ] Transcribir `benchmarks/captures/capture.wav` con el módulo da texto reconocible en español.
- [ ] La transcripción de ~10 s tarda menos de 2 s con `medium` int8, sin contar la carga del modelo.
- [ ] `README.md` documenta el módulo y su ejemplo de uso.

## Decisiones

- **Sí:** clase `Transcriber` que carga el modelo en el constructor, por elección del usuario. Es el requisito para el push-to-talk: cargar una vez, transcribir muchas.
- **No:** función suelta que recarga el modelo en cada llamada, como en la SPEC 03. Añadiría segundos de espera a cada dictado.
- **Sí:** el calentamiento va en el constructor, no en `transcribe()`. El tiempo medido refleja solo la inferencia, como en las SPEC 02 y 03.
- **Sí:** idioma fijo por parámetro con defecto `es`, por elección del usuario. La detección automática se descartó en la SPEC 02 y falla con frases cortas.
- **Sí:** `capture_mic.py` importa el módulo nuevo, por elección del usuario. Elimina la duplicación y valida el módulo con el micrófono real.
- **Sí:** entrada `int16` mono 16 kHz, el formato que ya produce `capture_mic.py`. Evita cambios en la captura.
- **Sí:** `capture_mic.py` añade `src/` a `sys.path`. No hay `pyproject.toml` ni instalación editable, y empaquetar queda fuera de alcance.
- **No:** `pip install -e .` ahora. Obligaría a diseñar el empaquetado antes de que exista la aplicación.
- **Sí:** verificación manual con el micrófono y un WAV existente, por elección del usuario, coherente con las SPEC 02 y 03.
- **No:** `pytest`. Introduce una dependencia y una carpeta `tests/` sin necesidad aún.
- **No:** extraer `audio.py` en esta spec. Es una extracción distinta y va en su propia spec.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Importar `speechflow` falla al ejecutar el script desde otro directorio | `capture_mic.py` calcula la ruta de `src/` relativa a su propio archivo, no al directorio actual. |
| Cargar el modelo en el constructor retrasa el arranque de `capture_mic.py` | Se crea el `Transcriber` después de grabar, como ahora; el modelo en caché carga en pocos segundos. |
| Un `int16` con otra tasa que 16 kHz da transcripciones erróneas sin avisar | El contrato está en la docstring y en el README; la validación de tasa queda fuera de alcance. |
| Regresión en `capture_mic.py` al eliminar código | El paso 2 compara la salida con la anterior y el criterio de aceptación exige el mismo formato. |

## Lo que **no** está en esta spec

- Módulo `audio.py`, empaquetado y tests con `pytest`.
- Streaming, VAD, detección de idioma y WER.
- Push-to-talk con atajo global, inserción de texto, bandeja y daemon.

Cada uno, si se aborda, va en su propia spec.
