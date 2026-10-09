# SPEC 18 — VAD y filtrado de silencios

> **Estado:** Aprobado
> **Depende de:** SPEC 04, SPEC 10, SPEC 12, SPEC 16
> **Fecha:** 2026-10-09
> **Objetivo:** Activar el filtro de voz `vad_filter` (Silero) de `faster-whisper` en cada transcripción, con la clave `[model] vad` (defecto `true`) para desactivarlo, de modo que los silencios no lleguen a Whisper ni produzcan texto inventado.

## Por qué existe esta spec

Whisper alucina con el silencio y el ruido de fondo: sobre audio sin voz suele devolver frases como "Gracias por ver el video" o "Subtítulos de ...". Hoy `Transcriber.transcribe()` pasa todo el audio al modelo, así que una pulsación sin hablar, o con pausas largas dentro de la grabación, puede insertar texto en la aplicación activa. `faster-whisper` incluye el VAD Silero (ONNX, dependencia ya instalada) y lo expone con `vad_filter=True`, sin código de recorte propio. Es el primer ítem del roadmap "Antes de la GUI" de `TODO.md`.

## Alcance

**Dentro:**

- Pasar `vad_filter=True` a `WhisperModel.transcribe()` en `Transcriber.transcribe()` cuando el VAD está activo.
- Usar los parámetros por defecto de `faster-whisper` (`VadOptions()`: `threshold=0.5`, `min_silence_duration_ms=2000`, `speech_pad_ms=400`), sin pasarlos explícitamente.
- Nuevo parámetro `vad: bool = True` en `Transcriber.__init__()`, guardado como `self.vad`.
- Calentamiento: con `vad=True`, además de la llamada actual (sin filtro, para calentar el decodificador de Whisper), una segunda llamada con `vad_filter=True` sobre el mismo segundo de silencio, para que Silero se cargue al arrancar y no en el primer dictado.
- Nuevo campo `Config.vad: bool = True` y clave `[model] vad` en `src/speechflow/config.py`: esquema, validación de tipo (`bool` estricto, como `notifications.enabled`) y plantilla de `write_emergency`.
- `load_transcriber(model, language, vad)` y `PushToTalk(..., vad=True)` en `src/speechflow/app.py`, para que la recarga tras la descarga por inactividad (SPEC 12) conserve el ajuste. `main()` pasa `config.vad`.
- Añadir `VAD: sí/no` a la línea informativa de arranque `Modelo: ... | idioma: ... | compute_type: ... | GPU`.
- Una grabación sin voz sigue el camino existente del texto vacío: `INFO` `Sin texto reconocido (...)`, sin insertar y sin notificación.
- Actualizar tests (`tests/test_transcriber.py`, `tests/test_config.py`, `tests/test_app_helpers.py`, `tests/test_push_to_talk.py`) y documentación (`speechflow.example.toml`, `README.md`, `TODO.md`).

**Fuera de alcance (para futuras specs):**

- Parámetros del VAD ajustables (`threshold`, `min_silence_duration_ms`, `speech_pad_ms`) en el TOML o en la CLI.
- Opción de CLI (`--no-vad`); la clave del TOML basta.
- Recorte propio de silencios por energía en `audio.py`.
- Cambios en `scripts/benchmark_stt.py` (usa `WhisperModel` directo) y medición del efecto del VAD sobre latencia o WER.
- Detener la grabación automáticamente al detectar silencio.
- Streaming de la captura y de la transcripción.
- Notificación de escritorio o mensaje nuevo distinto de `Sin texto reconocido` cuando no hay voz.

## Modelo de datos

Esta spec no introduce estructuras nuevas; añade un campo y una clave:

```python
# src/speechflow/config.py
@dataclass
class Config:
    ...
    vad: bool = True   # [model] vad; filtra silencios con Silero antes de transcribir

_SCHEMA["model"]["vad"] = ((bool,), "vad")
```

```toml
[model]
# vad = true             # filtra silencios y ruido sin voz antes de transcribir; false desactiva
```

```python
# src/speechflow/transcriber.py
class Transcriber:
    def __init__(self, model_name=DEFAULT_MODEL, language=DEFAULT_LANGUAGE, vad: bool = True) -> None: ...
    # transcribe(): self._model.transcribe(samples, language=self.language, vad_filter=self.vad)
```

Convenciones:

- `vad` es un `bool` estricto: `vad = 1` es inválido (mismo criterio que `notifications.enabled`).
- El ajuste se lee solo al arrancar; cambiarlo exige reiniciar.
- La firma de `Transcriber.transcribe()` no cambia: sigue devolviendo `(texto, segundos)`.
- Si `PushToTalk` recarga el modelo por inactividad, usa el mismo `vad` con el que se creó.

## Plan de implementación

1. En `config.py`, añadir `Config.vad`, la clave `vad` en `_SCHEMA["model"]` y la línea de plantilla de `write_emergency`. Tests en `tests/test_config.py` (válido, `false`, tipo incorrecto, entero rechazado, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. En `transcriber.py`, añadir el parámetro `vad`, pasar `vad_filter=self.vad` en `transcribe()` y el segundo calentamiento. Tests con `WhisperModelFalso`: `vad_filter` es `True` por defecto y `False` con `vad=False`; el calentamiento hace dos llamadas con `vad=True` y una con `vad=False`. Verificar: `pytest tests/test_transcriber.py` pasa.
3. En `app.py`, añadir `vad` a `load_transcriber()` y `PushToTalk`, pasar `config.vad` desde `main()` y ampliar la línea de arranque. Actualizar los tests de `load_transcriber` y de recarga por inactividad. Verificar: `pytest` pasa y `speechflow` arranca mostrando `VAD: sí`.
4. Documentar la clave en `speechflow.example.toml` y `README.md` (sección de configuración y de transcripción), y marcar el ítem 1 de la Fase 3 y "VAD" en `TODO.md`.

## Criterios de aceptación

- [ ] Con `vad = true` (o sin la clave), `WhisperModel.transcribe()` recibe `vad_filter=True` en cada dictado.
- [ ] Con `vad = false`, recibe `vad_filter=False`.
- [ ] Pulsar la tecla 3 s sin hablar registra `Sin texto reconocido (...)` y no inserta nada en la aplicación activa.
- [ ] Dictar una frase con una pausa de 3 s en medio inserta ambas partes sin texto extra.
- [ ] `vad = "si"` o `vad = 1` en el TOML hacen inválido el archivo con un mensaje que nombra `model.vad`.
- [ ] El arranque registra `VAD: sí` o `VAD: no` en la línea `Modelo: ...`.
- [ ] Tras un `idle_timeout` y una recarga, el modelo recargado mantiene el ajuste `vad`.
- [ ] El primer dictado tras arrancar no tarda más que el segundo en cargar Silero (Silero se carga durante el calentamiento).
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `pytest` pasa con código 0.
- [ ] `git diff main -- scripts` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[model] vad`.

## Decisiones

- **Sí:** `vad_filter` de `faster-whisper`. Silero ya viene como dependencia, no añade paquetes ni código de recorte, y es lo que pidió el roadmap.
- **No:** recorte propio por energía en `audio.py`. Duplica el VAD, añade código y tests, y es peor detectando voz entre ruido.
- **Sí:** clave `[model] vad`, defecto `true`, por elección del usuario. Permite desactivarlo si recorta palabras con una voz o un micrófono concretos.
- **No:** siempre activo. Sin salida si el VAD falla con el micrófono del usuario.
- **No:** sección `[vad]` con parámetros. Más claves, validación y documentación por valores que aún no se han medido.
- **Sí:** parámetros por defecto de `faster-whisper`, fijos, por elección del usuario. Con `min_silence_duration_ms=2000` solo se recortan silencios de 2 s o más y `speech_pad_ms=400` evita comerse inicios y finales de palabra; si resulta lento o conservador, se ajusta en otra spec con datos.
- **Sí:** mantener el mensaje `Sin texto reconocido` para el caso sin voz. La firma de `transcribe()` no devuelve información del VAD, y un mensaje igual para "sin voz" y "sin texto" evita cambiar el contrato y los tests de SPEC 16. Desviación respecto a la propuesta inicial de un mensaje `Sin voz detectada`, tomada por el diseño.
- **No:** notificación de escritorio al no detectar voz. Una pulsación accidental sería ruido.
- **Sí:** doble calentamiento (sin filtro y con filtro). El primero calienta el decodificador de Whisper, que con el filtro activo no recibiría audio de voz; el segundo carga Silero. Decisión del diseño.
- **No:** `--no-vad` en la CLI. El archivo de configuración cubre el caso y evita otra precedencia que probar.
- **No:** tocar `scripts/benchmark_stt.py`. Mide Whisper, no el pipeline completo, y su salida no debe cambiar (criterio pendiente de la SPEC 14).

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Silero recorta el inicio o el final de una palabra con voz baja | `speech_pad_ms=400` por defecto; si ocurre, `vad = false` en el TOML. |
| Silero se carga en el primer dictado y añade latencia | El calentamiento con `vad_filter=True` lo carga al arrancar; hay un criterio de aceptación. |
| `onnxruntime` falla al cargar Silero en este entorno | El error sale en el arranque (calentamiento) y no en pleno dictado; `vad = false` evita la ruta. |
| Con `min_silence_duration_ms=2000` las pausas de 1–2 s no se recortan y Whisper puede alucinar en ellas | Aceptado: el caso grave es la grabación sin voz, que sí se filtra. Ajustar los parámetros queda para otra spec. |
| Los tests existentes asumen una sola llamada a `transcribe` en el calentamiento | El paso 2 actualiza `WhisperModelFalso` y los tests de `Transcriber`. |

## Lo que **no** está en esta spec

- Parámetros del VAD configurables, en el TOML o en la CLI.
- Opción `--no-vad`.
- Recorte propio de silencios por energía.
- Cambios en el benchmark y medición de latencia o WER con VAD.
- Parada automática de la grabación por silencio y streaming.
- Mensaje o notificación nuevos al no detectar voz.

Cada uno, si se aborda, va en su propia spec.
