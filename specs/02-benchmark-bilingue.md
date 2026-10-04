# SPEC 02 — Benchmark de STT bilingüe (español e inglés)

> **Estado:** Implementado
> **Depende de:** SPEC 01
> **Fecha:** 2026-10-04
> **Objetivo:** Volver a correr el benchmark de STT con las muestras en español e inglés, detectando el idioma de cada WAV por el prefijo de su nombre, para decidir el modelo por defecto con datos de ambos idiomas.

## Por qué existe esta spec

La SPEC 01 dejó el benchmark fijado a un solo idioma (`--language es`) y `benchmarks/results.md` declara "sin muestras en inglés todavía". Ya existen los audios en inglés (`bug-lower_NNN.wav`), pero el script no sabe asociar idioma a cada muestra y solo usa las primeras 5. El modelo por defecto para la siguiente spec debe cumplir latencia y VRAM en los dos idiomas.

## Alcance

**Dentro:**

- Modificar `scripts/benchmark_stt.py` para asignar el idioma de cada muestra por el prefijo del nombre (`mercado-libre` → `es`, `bug-lower` → `en`) y pasarlo a `model.transcribe(language=...)`.
- Usar todos los fragmentos `<prefijo>_NNN.wav` de `benchmarks/samples/` (≈44 en español y ≈74 en inglés) con `small` y `medium` en `int8`.
- Seguir ignorando los WAV de más de 30 s (`bug-lower.wav`, `mercado-pago.wav`).
- Añadir la columna `Idioma` a la tabla de `benchmarks/results.md`, y mostrar la mediana por modelo e idioma.
- Elegir un único modelo por defecto que cumpla latencia y VRAM en ambos idiomas.
- Regenerar `benchmarks/results.md` (sobrescrito) y actualizar `README.md`.

**Fuera de alcance:**

- Medir audios largos (>30 s) por separado.
- Medir calidad de transcripción (WER) contra una transcripción de referencia; las transcripciones se guardan solo para lectura manual.
- Detección automática de idioma de Whisper (`language=None`) y modelos adicionales (`large`, `turbo`) o compute types distintos de `int8`.
- Cualquier funcionalidad de SpeechFlow (micrófono, atajo, inserción, bandeja, VAD), igual que en la SPEC 01.

## Modelo de datos

No hay estructuras persistentes nuevas. El resultado en memoria de la SPEC 01 gana un campo, y el script una constante:

```python
# Resultado por (modelo, muestra) — solo en memoria
{
    "model": "small",          # "small" | "medium"
    "compute_type": "int8",
    "language": "es",          # NUEVO: "es" | "en", derivado del prefijo
    "sample": "mercado-libre_000.wav",
    "audio_seconds": 10.0,
    "load_seconds": 0.0,
    "transcribe_seconds": 0.0,
    "vram_mb": 0,
    "text": "",
}

# Constante en scripts/benchmark_stt.py
LANGUAGE_BY_PREFIX = {"mercado-libre": "es", "bug-lower": "en"}
```

Archivos que cambian: `scripts/benchmark_stt.py`, `benchmarks/results.md`, `README.md`. No se mueven los WAV ni cambia `.gitignore`.

## Plan de implementación

1. Añadir `LANGUAGE_BY_PREFIX` y una función que resuelva el idioma de un WAV por su prefijo (`<prefijo>_NNN.wav`). Un WAV sin prefijo conocido se omite con una advertencia en stderr. Verificar: ejecutar la función sobre `mercado-libre_000.wav`, `bug-lower_000.wav` y `otro.wav` devuelve `es`, `en` y omisión.
2. Cambiar `load_samples` para cargar todos los fragmentos válidos (≤30 s, prefijo conocido) con su idioma, sin el límite de 5 por defecto (`--max-samples` pasa a ser opcional y por idioma). Verificar: lista ≈44 muestras `es` y ≈74 `en`, sin `bug-lower.wav` ni `mercado-pago.wav`.
3. Cambiar `run_model` para transcribir cada muestra con su idioma, hacer el calentamiento una vez por modelo y registrar `language` en cada fila. Verificar: ejecución con `--models small --max-samples 2` produce 2 filas `es` y 2 `en` con texto coherente en cada idioma.
4. Cambiar `pick_default` para exigir latencia (mediana por 10 s < 2 s) y VRAM en **cada** idioma, y `write_results` para añadir la columna `Idioma`, la mediana por modelo e idioma, y quitar la leyenda "sin muestras en inglés todavía". Verificar: `results.md` generado tiene la columna y las cuatro medianas (2 modelos × 2 idiomas).
5. Ejecutar `python scripts/benchmark_stt.py` completo y commitear el `benchmarks/results.md` resultante. Verificar: ver criterios de aceptación.
6. Actualizar `README.md` (sección de benchmark): convención de nombres/prefijos por idioma, que ya no hay límite de 5 muestras y la opción `--max-samples`. Verificar: el README coincide con el comportamiento real del script.

## Criterios de aceptación

- [ ] `python scripts/benchmark_stt.py` termina sin errores con `small` y `medium` en `int8` sobre GPU.
- [ ] `benchmarks/results.md` tiene filas de ambos idiomas por cada modelo, con la columna `Idioma` y los campos de la SPEC 01 (carga, transcripción, duración, VRAM).
- [ ] Los WAV >30 s y sin prefijo conocido no aparecen en `results.md`.
- [ ] Cada fila usa el idioma de su prefijo (`mercado-libre` → `es`, `bug-lower` → `en`) y las transcripciones de las filas `en` están en inglés.
- [ ] `results.md` muestra la mediana de transcripción normalizada a 10 s por cada combinación modelo/idioma.
- [ ] El pico de VRAM de cada modelo es menor a 6 GB.
- [ ] `results.md` indica un único modelo por defecto que cumple < 2 s por 10 s de audio y VRAM < 6 GB en ambos idiomas, o documenta explícitamente que ninguno lo logra.
- [ ] `results.md` ya no contiene la leyenda "sin muestras en inglés todavía".
- [ ] `benchmarks/samples/` sigue sin versionarse en git.
- [ ] `README.md` documenta la convención de prefijos y el comportamiento actual de `--max-samples`.

## Decisiones

- **Sí:** idioma por prefijo del nombre mediante un mapa fijo en el script, por elección del usuario. Simple y sin mover archivos; el costo es que cada familia de audios nueva exige añadir su prefijo.
- **No:** subcarpetas `es/` y `en/` y dos corridas con `--language`. Descartadas por el usuario; las subcarpetas habrían sido más explícitas.
- **Sí:** usar todos los fragmentos `_NNN` (≈118 muestras por modelo), por elección del usuario. Más robusto estadísticamente que 5 por idioma, a costa de una corrida más larga y un `results.md` mucho más grande (≈236 filas y transcripciones).
- **Sí:** ignorar los WAV >30 s, como en la SPEC 01. Los fragmentos de ~10 s son los representativos del objetivo de latencia.
- **Sí:** una sola tabla con columna `Idioma` y un modelo por defecto único que cumpla en ambos idiomas. Evita que la siguiente spec tenga que gestionar un modelo distinto por idioma.
- **No:** defecto por idioma. Complica la configuración sin una necesidad demostrada.
- **Sí:** mantener las transcripciones en `results.md` para revisión manual de calidad, sin WER.
- **Sí:** el calentamiento se hace una vez por modelo y no se mide, como antes; los tiempos de carga de `medium` ya no incluyen descarga porque el modelo está en caché.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Los fragmentos finales son más cortos (`mercado-libre_043` ≈2 s, `bug-lower_073` ≈4 s) y su tiempo normalizado a 10 s se distorsiona por el costo fijo de inferencia | Se usa la mediana, que absorbe un par de valores atípicos entre ~118 muestras. |
| El `results.md` con ≈236 filas es largo y difícil de leer | Las medianas por modelo e idioma y el modelo por defecto van al inicio, antes de la tabla. |
| La corrida completa tarda varios minutos | Se documenta en el README y `--max-samples` permite una corrida corta de prueba. |
| Algún audio en inglés tiene un prefijo distinto de `bug-lower` | Se omite con advertencia en stderr; se añade al mapa si corresponde. |

## Lo que **no** está en esta spec

- Medición de WER, audios largos, más modelos o compute types.
- Cualquier funcionalidad de la aplicación SpeechFlow.

Cada uno, si se aborda, va en su propia spec.
