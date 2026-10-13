# SPEC 23 — Modelo `small` por defecto en CPU

> **Estado:** Aprobado
> **Depende de:** SPEC 04, SPEC 10, SPEC 12, SPEC 16, SPEC 22
> **Fecha:** 2026-10-12
> **Objetivo:** Hacer que, cuando el usuario no fija el modelo (`[model] name` ni `--model`), `Transcriber` cargue `small` si el dispositivo resuelto es CPU y `medium` si es GPU.

## Por qué existe esta spec

SPEC 22 permitió ejecutar Whisper en CPU pero dejó fuera cambiar el modelo por defecto: en CPU `medium` es lento y solo se avisa. Hoy `Config.model` vale `"medium"` siempre, así que no se puede distinguir "el usuario eligió `medium`" de "el usuario no eligió nada". Esta spec introduce el estado "modelo sin fijar" y lo resuelve **después** de decidir el dispositivo, para que `auto` que cae a CPU también obtenga `small`. Un modelo fijado explícitamente se respeta siempre, con el aviso de lentitud de SPEC 22.

## Alcance

**Dentro:**

- Constantes en `src/speechflow/transcriber.py`: `DEFAULT_MODEL = "medium"` (GPU, sin cambios) y `DEFAULT_CPU_MODEL = "small"` (CPU).
- `Transcriber.__init__(model_name: str | None = None, ...)`: `None` significa "sin fijar". Se resuelve así, tras decidir el dispositivo:
  - dispositivo `cuda` → `DEFAULT_MODEL`;
  - dispositivo `cpu` → `DEFAULT_CPU_MODEL`;
  - `auto` sin GPU visible → `DEFAULT_CPU_MODEL`;
  - `auto` con GPU: intenta `DEFAULT_MODEL` en GPU; si la carga o el calentamiento fallan, libera lo cargado y reintenta en CPU con `DEFAULT_CPU_MODEL`.
  - Un `model_name` explícito se usa tal cual en todos los casos, incluido el reintento en CPU.
- Atributo público `Transcriber.model_name` (`str`) con el modelo realmente cargado; nunca vale `None`.
- Cuando se aplica `DEFAULT_CPU_MODEL` por no estar fijado el modelo, `Transcriber` registra un `INFO` `Modelo no fijado: se usa small por defecto en CPU.`
- `Config.model` pasa a `str | None`, con defecto `None`. En `config.py`: `Config.model: str | None = None`, el esquema `_SCHEMA["model"]["name"]` sigue aceptando `str`, y la plantilla de `write_emergency` deja `name` comentado (`# name = "medium"  # sin fijar: medium en GPU, small en CPU`) para que `load_config` dé `Config()`. Un `name` vacío o solo espacios se rechaza como inválido con un mensaje que nombra `model.name`.
- `app.py`:
  - `main()` pasa `model` (`--model` > `[model] name` > `None`) a `load_transcriber()` sin resolverlo.
  - `load_transcriber(model: str | None, ...)` registra `Cargando {modelo} (int8, {dispositivo})...`; con `model=None` y dispositivo `auto` registra `Cargando el modelo por defecto (int8, auto)...`; con `model=None` y dispositivo `cpu` o `cuda` usa el nombre ya conocido (`small` o `medium`).
  - La notificación inicial es `Cargando {model}...` si hay modelo fijado y `Cargando modelo...` si no.
  - Tras cargar, `main()` usa `transcriber.model_name` (no el valor de entrada) en la notificación `Modelo {nombre} cargado`, en la línea `Modelo: ... | ...`, en el aviso de lentitud (`is_heavy_for_cpu`), en `PushToTalk` y en el log de liberación al salir.
  - `--model` ayuda: `modelo de faster-whisper (defecto: small en CPU, medium en GPU)`.
- `PushToTalk` no cambia de firma: `main()` le pasa `transcriber.model_name` (ya resuelto), de modo que las recargas tras la liberación por inactividad (SPEC 12) cargan el mismo modelo y no vuelven a decidir.
- El aviso de lentitud de SPEC 22 se mantiene: con CPU y modelo `medium` o mayor (fijado explícitamente) sigue el `WARNING` que sugiere `small`. Con el defecto `small` no aparece.
- Actualizar tests (`tests/test_config.py`, `tests/test_transcriber.py`, `tests/test_app_helpers.py`, `tests/test_push_to_talk.py` si usa `Config.model`) y documentación (`speechflow.example.toml`, `README.md`, `TODO.md` si procede).

**Fuera de alcance (para futuras specs):**

- Cambiar el modelo por defecto en GPU (sigue `medium`).
- Elegir el modelo según RAM, núcleos o benchmark.
- Cambiar el modelo en caliente o al recargar tras un cambio de dispositivo.
- Persistir el modelo elegido en `state.toml`.
- Medir y documentar tiempos de `small` en CPU en el benchmark.
- Otros tipos de cómputo, otros aceleradores y selección de GPU por índice (siguen fuera, como en SPEC 22).
- Cambios en `scripts/benchmark_stt.py`, `scripts/capture_mic.py` y `environment.yml`.

## Modelo de datos

```python
# src/speechflow/transcriber.py
DEFAULT_MODEL = "medium"       # defecto en GPU
DEFAULT_CPU_MODEL = "small"    # defecto en CPU

class Transcriber:
    def __init__(self, model_name: str | None = None, language=..., vad=True, device="auto", cpu_threads=0) -> None: ...
    model_name: str            # el realmente cargado; nunca None

# src/speechflow/config.py
@dataclass(frozen=True)
class Config:
    model: str | None = None   # [model] name; None = sin fijar (medium en GPU, small en CPU)
```

```toml
[model]
# name = "medium"   # sin fijar: medium en GPU, small en CPU; fijarlo lo usa en cualquier dispositivo
```

Convenciones:

- `None` solo existe en `Config.model` y en los parámetros de entrada; `Transcriber.model_name` ya es un `str`.
- Un `name` explícito gana siempre sobre el defecto por dispositivo, también en el reintento de `auto`.
- El nombre del modelo se lee solo al arrancar; cambiarlo exige reiniciar.

## Plan de implementación

1. En `transcriber.py`, añadir `DEFAULT_CPU_MODEL`, aceptar `model_name: str | None`, resolverlo según el dispositivo (incluido el reintento de `auto`), exponer `Transcriber.model_name` y registrar el `INFO` del defecto en CPU. Tests en `tests/test_transcriber.py` con `WhisperModel` y `ctranslate2` dobles: `cpu` sin modelo carga `small`; `cuda` sin modelo carga `medium`; `auto` sin GPU carga `small`; `auto` con fallo de GPU reintenta con `small`; con `model_name="medium"` explícito, `cpu` y el reintento de `auto` cargan `medium`. Verificar: `pytest tests/test_transcriber.py` pasa.
2. En `config.py`, cambiar `Config.model` a `str | None = None`, validar `name` no vacío y ajustar la plantilla de `write_emergency`. Tests en `tests/test_config.py` (defecto `None`, `name = "small"` válido, `name = ""` inválido con `model.name`, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
3. En `app.py`, pasar `model` sin resolver a `load_transcriber()`, ajustar los mensajes `Cargando ...` y la notificación inicial, y usar `transcriber.model_name` tras la carga (notificación, línea `Modelo: ...`, aviso de lentitud, `PushToTalk`, log de salida). Actualizar el texto de ayuda de `--model`. Tests en `tests/test_app_helpers.py`. Verificar: `pytest` pasa y `speechflow --compute-device cpu` muestra `Cargando small (int8, CPU)...`.
4. Revisar `tests/test_push_to_talk.py` y `tests/conftest.py` por usos de `Config.model` o del literal `medium` que dependan del defecto, y ajustarlos. Verificar: `pytest` pasa completo.
5. Documentar en `speechflow.example.toml` y `README.md` (tabla de opciones: defecto `small` en CPU y `medium` en GPU; sección "Modo solo CPU": ya no se recomienda fijar `small`, se explica cómo forzar `medium`; ejemplos de log) y marcar lo que corresponda en `TODO.md`.

## Criterios de aceptación

- [ ] `Config().model is None`.
- [ ] `[model] name = "small"` y `name = "medium"` son válidos en el TOML y dan `Config.model` igual a ese valor.
- [ ] `[model] name = ""` hace inválido el archivo con un mensaje que nombra `model.name`.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `Transcriber(device="cpu")` sin modelo crea `WhisperModel("small", ...)` y deja `Transcriber.model_name == "small"`.
- [ ] `Transcriber(device="cuda")` sin modelo crea `WhisperModel("medium", ...)` y deja `model_name == "medium"`.
- [ ] `Transcriber(device="auto")` sin GPU visible y sin modelo carga `small`.
- [ ] `Transcriber(device="auto")` con GPU cuyo `WhisperModel("medium")` falla reintenta en CPU con `small` y deja `model_name == "small"` y `device == "cpu"`.
- [ ] `Transcriber("medium", device="cpu")` carga `medium` (el modelo explícito se respeta).
- [ ] `Transcriber("medium", device="auto")` con fallo de GPU reintenta en CPU con `medium`.
- [ ] `Transcriber.model_name` nunca vale `None`.
- [ ] Al aplicarse `small` por defecto en CPU se registra el `INFO` `Modelo no fijado: se usa small por defecto en CPU.`; con un modelo explícito no se registra.
- [ ] `speechflow --compute-device cpu` sin `--model` ni `[model] name` muestra `Cargando small (int8, CPU)...`, la línea `Modelo: small | ...| CPU | ...` y no muestra el aviso de lentitud.
- [ ] `speechflow --compute-device cpu --model medium` carga `medium` y muestra el `WARNING` de lentitud que sugiere `small`.
- [ ] `speechflow --compute-device cuda` sin modelo fijado carga `medium` (sin cambios respecto a antes).
- [ ] Con `auto` sin modelo fijado, la notificación inicial es `Cargando modelo...` y la de carga correcta nombra el modelo realmente cargado.
- [ ] `PushToTalk` recibe `transcriber.model_name`, y una recarga tras la liberación por inactividad carga ese mismo modelo.
- [ ] Con GPU funcional, `device = "auto"` y sin modelo fijado, el comportamiento es el de antes (`medium`, GPU, `int8`).
- [ ] `--model` ayuda indica `small` en CPU y `medium` en GPU.
- [ ] `pytest` pasa con código 0 y no escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts environment.yml` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan el modelo por defecto según dispositivo.

## Decisiones

- **Sí:** aplicar `small` cuando el dispositivo **resuelto** es CPU (incluye `auto` que cae), por elección del usuario. Quien no tiene GPU utilizable no debería tener que configurar nada para obtener un modelo usable.
- **No:** aplicarlo solo con `device = "cpu"` explícito. `auto` sin GPU seguiría cargando `medium` lento.
- **Sí:** `Config.model` pasa a `str | None` con `None` = sin fijar, por elección del usuario. Es la única forma de distinguir "eligió `medium`" de "no eligió nada" y poder forzar `medium` en CPU a propósito.
- **No:** comparar con `"medium"` y sustituir por `small`. Hace imposible pedir `medium` en CPU.
- **Sí:** en el reintento de `auto` tras fallo de GPU, usar `small` si el modelo no estaba fijado, por elección del usuario. Coherente con el defecto en CPU; un modelo fijado se mantiene.
- **No:** reintentar siempre con el modelo ya elegido. Un fallo de GPU llevaría a `medium` en CPU.
- **Sí:** `INFO` de "modelo no fijado" y aviso de lentitud solo para `medium` o mayor fijado en CPU, por elección del usuario. El usuario ve por qué se cargó `small` sin ruido extra.
- **Sí:** `Transcriber.model_name` expone el modelo real y `main()` lo usa para todo lo posterior. Decisión del diseño: con `auto` el modelo solo se conoce tras cargar, y `PushToTalk` necesita un nombre fijo para las recargas (SPEC 12).
- **Sí:** `PushToTalk` no cambia de firma. Decisión del diseño: recibe el nombre ya resuelto y evita decidir de nuevo en cada recarga, igual que con el dispositivo en SPEC 22.
- **Sí:** `medium` sigue siendo el defecto en GPU. Decisión del diseño: no hay motivo para cambiar el comportamiento de quien ya tiene GPU.
- **No:** persistir el modelo elegido en `state.toml`. El modelo se lee solo al arrancar, como el resto de `[model]`.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Usuarios con CPU que ya dependían de `medium` por defecto notan peor precisión | `INFO` explícito en el log y documentación de cómo fijar `name = "medium"`; el aviso de lentitud sigue para quien lo fije. |
| El modelo `small` no está en la caché de Hugging Face y la primera carga lo descarga (~0.5 GB) | `README.md` lo menciona; la notificación inicial ya indica que se está cargando. |
| Código que lee `Config.model` esperando un `str` falla con `None` | Los usos están en `main()`; se revisan con `grep` en el paso 3 y los tests cubren el defecto `None`. |
| Con `auto`, el nombre del modelo no se conoce hasta tras la carga y los logs iniciales son menos específicos | Mensajes `Cargando el modelo por defecto ...` y, tras cargar, el nombre real en `Modelo: ...` y en la notificación. |
| Los dobles de `WhisperModel` no reflejan el comportamiento real al reintentar | Prueba manual con `CUDA_VISIBLE_DEVICES=""` en los criterios (`Cargando small (int8, CPU)...`). |

## Lo que **no** está en esta spec

- Cambiar el modelo por defecto en GPU.
- Elegir el modelo por hardware o benchmark.
- Cambiar el modelo en caliente.
- Persistir el modelo en `state.toml`.
- Benchmark de `small` en CPU.
- Cambios en `scripts/` o `environment.yml`.

Cada uno, si se aborda, va en su propia spec.
