# SPEC 22 — Modo solo CPU

> **Estado:** Aprobado
> **Depende de:** SPEC 04, SPEC 10, SPEC 12, SPEC 16
> **Fecha:** 2026-10-12
> **Objetivo:** Añadir la clave `[model] device` (`auto`, `cpu` o `cuda`) y `[model] cpu_threads` para que `Transcriber` pueda ejecutar Whisper solo en CPU, y que `auto` caiga a CPU con aviso cuando no haya GPU utilizable.

## Por qué existe esta spec

Hoy `Transcriber` fija `device="cuda"`. En un equipo sin GPU NVIDIA, o con un driver roto o incompatible, `WhisperModel` lanza una excepción al arrancar y `speechflow` no se puede usar. `faster-whisper` ya soporta CPU con `int8`, así que el cambio es de selección y de mensajes, no de motor. En CPU el modelo `medium` es lento; esta spec no cambia el modelo por defecto, solo avisa.

## Alcance

**Dentro:**

- Clave `[model] device` (`str`, defecto `"auto"`) en `src/speechflow/config.py`: campo `Config.device_compute`, esquema `_SCHEMA["model"]["device"]` y línea en la plantilla de `write_emergency`. Valores válidos: `"auto"`, `"cpu"`, `"cuda"`; otro valor hace inválido el archivo con un mensaje que nombra `model.device`.
- Clave `[model] cpu_threads` (`int`, defecto `0`) en `config.py`: campo `Config.cpu_threads`. `0` deja el valor por defecto de `faster-whisper`; un entero positivo se pasa como `cpu_threads` a `WhisperModel`. Un valor negativo hace inválido el archivo y el mensaje nombra `model.cpu_threads`. Solo se usa cuando el dispositivo resuelto es `cpu`.
- Opción de CLI `--compute-device {auto,cpu,cuda}` en `app.py`; gana sobre el TOML. El nombre evita chocar con `--device`, que es el micrófono.
- Parámetros nuevos en `Transcriber.__init__`: `device: str = "auto"` y `cpu_threads: int = 0`. Atributo público `Transcriber.device` con el dispositivo realmente usado (`"cpu"` o `"cuda"`).
- Resolución del dispositivo en `transcriber.py`:
  - `"cpu"`: carga en CPU con `compute_type="int8"`.
  - `"cuda"`: carga en GPU; si falla, la excepción sube y `main()` sale con un error claro que sugiere `--compute-device cpu`. No cae a CPU.
  - `"auto"`: si `ctranslate2.get_cuda_device_count() == 0`, usa CPU. Si hay GPU pero la carga o el calentamiento fallan, libera lo cargado y reintenta en CPU. En ambos casos de caída registra un `WARNING` con el motivo.
- `COMPUTE_TYPE` sigue siendo `int8` para ambos dispositivos.
- `main()` y `load_transcriber()` registran el dispositivo realmente usado en lugar del literal `GPU` (`Cargando medium (int8, CPU)...`, línea `Modelo: ... | CPU | ...`). Si el dispositivo es CPU y el modelo es `medium` o mayor, se añade un `WARNING` de que la transcripción será lenta y se sugiere `small`.
- Cuando `auto` cae a CPU, `main()` envía una notificación `Sin GPU utilizable: se usa la CPU`.
- `PushToTalk` recibe `compute_device: str` y `cpu_threads: int` y los pasa en las recargas tras la liberación por inactividad (SPEC 12). `main()` le pasa el dispositivo ya resuelto (`transcriber.device`), de modo que una recarga no vuelve a intentar la GPU que ya falló.
- Actualizar tests (`tests/test_config.py`, `tests/test_app_helpers.py`, `tests/test_push_to_talk.py`, un test nuevo del `Transcriber` con `WhisperModel` doble) y documentación (`speechflow.example.toml`, `README.md`, `TODO.md` si procede).

**Fuera de alcance (para futuras specs):**

- Cambiar el modelo por defecto o elegirlo según el dispositivo.
- Otros tipos de cómputo (`float16`, `int8_float16`, `float32`) o clave `compute_type`.
- Otros aceleradores (ROCm, Metal, OpenVINO) y selección de GPU por índice.
- Entorno conda sin CUDA (`environment-cpu.yml`); `environment.yml` no cambia.
- Cambio de dispositivo en caliente con una tecla.
- Cambios en `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.
- Medir y documentar tiempos de CPU en el benchmark.

## Modelo de datos

```python
# src/speechflow/config.py
COMPUTE_DEVICES = ("auto", "cpu", "cuda")

@dataclass(frozen=True)
class Config:
    ...
    device_compute: str = "auto"   # [model] device; "auto", "cpu" o "cuda"
    cpu_threads: int = 0           # [model] cpu_threads; 0 = defecto de faster-whisper

_SCHEMA["model"]["device"] = ((str,), "device_compute")
_SCHEMA["model"]["cpu_threads"] = ((int,), "cpu_threads")
```

```toml
[model]
# device = "auto"        # "auto": GPU si hay y funciona, si no CPU; "cpu": solo CPU; "cuda": solo GPU (falla si no hay)
# cpu_threads = 0        # hilos de CPU para Whisper; 0 usa el defecto de faster-whisper
```

```python
# src/speechflow/transcriber.py
class Transcriber:
    def __init__(self, model_name=..., language=..., vad=True, device: str = "auto", cpu_threads: int = 0) -> None: ...
    device: str  # "cpu" o "cuda", el realmente usado

# src/speechflow/app.py
# PushToTalk.__init__(..., compute_device: str = "auto", cpu_threads: int = 0)
```

Convenciones:

- `Config.device_compute` se llama así para no chocar con `Config.device`, que es el micrófono (`[audio] device`).
- `Transcriber.device` nunca vale `"auto"`.
- Los valores de `device` y `cpu_threads` se leen solo al arrancar; cambiarlos exige reiniciar.
- `--compute-device` gana sobre `[model] device`.

## Plan de implementación

1. En `config.py`, añadir `Config.device_compute`, `Config.cpu_threads`, las claves en `_SCHEMA["model"]`, la validación (`device` en `COMPUTE_DEVICES`, `cpu_threads >= 0`) y las líneas de plantilla de `write_emergency`. Tests en `tests/test_config.py` (defectos, valores válidos, `"gpu"` inválido con error que nombra `model.device`, `cpu_threads = -1` inválido, tipo incorrecto, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. En `transcriber.py`, añadir `device` y `cpu_threads` a `Transcriber`, la resolución `cpu` / `cuda` / `auto`, el atributo `Transcriber.device` y el `WARNING` de la caída. Tests con `WhisperModel` y `ctranslate2` sustituidos por dobles: `cpu` no toca CUDA y pasa `cpu_threads`; `cuda` con fallo propaga la excepción; `auto` sin GPU usa CPU; `auto` con fallo de carga reintenta en CPU y deja `device == "cpu"`. Verificar: `pytest` pasa y `Transcriber(..., device="cpu")` carga en una máquina con la GPU oculta (`CUDA_VISIBLE_DEVICES=""`).
3. En `app.py`, añadir `--compute-device`, pasar `device` y `cpu_threads` a `load_transcriber()` y registrar el dispositivo real en las líneas `Cargando ...` y `Modelo: ...`. Añadir el aviso de lentitud para `medium` o mayor en CPU y la notificación de caída de `auto`. Capturar el error de `device = "cuda"` en `main()` con mensaje claro y `sys.exit(1)`. Tests en `tests/test_app_helpers.py`. Verificar: `pytest` pasa y `speechflow --compute-device cpu` arranca y muestra `CPU` en el log.
4. En `PushToTalk`, añadir `compute_device` y `cpu_threads`, usarlos en la recarga tras la liberación por inactividad y pasar desde `main()` el dispositivo resuelto. Test en `tests/test_push_to_talk.py`: la recarga usa el dispositivo resuelto, no `auto`. Verificar: `pytest` pasa.
5. Documentar en `speechflow.example.toml` y `README.md` (nueva sección "Modo solo CPU": claves, opción de CLI, comportamiento de `auto`, aviso de lentitud, sugerencia de `small`; ajustar la línea de requisitos que hoy exige GPU NVIDIA) y marcar lo que corresponda en `TODO.md`.

## Criterios de aceptación

- [ ] `Config()` tiene `device_compute == "auto"` y `cpu_threads == 0`.
- [ ] `[model] device = "cpu"`, `"cuda"` y `"auto"` son válidos en el TOML.
- [ ] `[model] device = "gpu"` hace inválido el archivo con un mensaje que nombra `model.device`.
- [ ] `[model] cpu_threads = -1` hace inválido el archivo con un mensaje que nombra `model.cpu_threads`.
- [ ] Una clave desconocida en `[model]` se rechaza como antes.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `Transcriber(device="cpu")` crea `WhisperModel` con `device="cpu"`, `compute_type="int8"` y los `cpu_threads` indicados, sin consultar CUDA.
- [ ] Con `cpu_threads = 0` no se pasa `cpu_threads` a `WhisperModel` (se usa su defecto).
- [ ] `Transcriber(device="cuda")` con fallo de carga propaga la excepción y no reintenta en CPU.
- [ ] `Transcriber(device="auto")` sin GPU visible carga en CPU y deja `Transcriber.device == "cpu"`.
- [ ] `Transcriber(device="auto")` con GPU cuyo `WhisperModel` falla reintenta en CPU y registra un `WARNING` con el motivo.
- [ ] `Transcriber.device` nunca vale `"auto"`.
- [ ] `speechflow --compute-device cpu` arranca con `CUDA_VISIBLE_DEVICES=""`, el log muestra `Cargando medium (int8, CPU)...` y un dictado se transcribe e inserta.
- [ ] Con dispositivo CPU y modelo `medium`, el log muestra un `WARNING` de lentitud que sugiere `small`.
- [ ] Con `small` en CPU no se muestra ese aviso.
- [ ] Cuando `auto` cae a CPU se envía la notificación `Sin GPU utilizable: se usa la CPU`.
- [ ] `speechflow --compute-device cuda` sin GPU sale con código 1 y un mensaje que sugiere `--compute-device cpu`.
- [ ] `--compute-device` gana sobre `[model] device`.
- [ ] Tras la liberación por inactividad, la recarga usa el dispositivo resuelto y no vuelve a intentar la GPU fallida.
- [ ] Con GPU funcional y `device = "auto"`, el comportamiento es el de antes (GPU, `int8`).
- [ ] `pytest` pasa con código 0 y no escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts environment.yml` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[model] device`, `[model] cpu_threads` y `--compute-device`.

## Decisiones

- **Sí:** clave `[model] device` con `auto` por defecto, por elección del usuario. Cubre el equipo sin GPU y el driver roto sin configurar nada, y no cambia nada si la GPU funciona.
- **No:** solo clave `cpu`/`cuda` o solo un flag `--cpu`. El primero obliga a editar el TOML justo cuando el driver falla; el segundo no persiste.
- **Sí:** en `auto`, caer a CPU con `WARNING` y notificación, por elección del usuario. El fallo no queda escondido.
- **Sí:** con `cuda` explícito, fallar con error claro, por elección del usuario. Quien fuerza GPU quiere saber que no la tiene.
- **No:** caer a CPU también con `cuda` explícito. Esconde el problema del driver.
- **Sí:** `cpu_threads` configurable, por elección del usuario, con `0` como "defecto de faster-whisper". Decisión del diseño: `0` evita imponer un número y mantiene el comportamiento actual.
- **No:** bajar a `small` automáticamente en CPU. El modelo es decisión del usuario; solo se avisa.
- **Sí:** no tocar `environment.yml` y documentar en el README, por elección del usuario. cuBLAS y cuDNN se instalan pero no se usan en CPU.
- **No:** `environment-cpu.yml`. Más mantenimiento para un solo caso de uso.
- **Sí:** `int8` en CPU y GPU. Decisión del diseño: es el tipo que ya se usa y el más rápido en CPU con `faster-whisper`; añadir `compute_type` configurable queda fuera.
- **Sí:** `Config.device_compute` y `--compute-device`. Decisión del diseño: `device` ya es el micrófono en `Config`, CLI y TOML (`[audio] device`).
- **Sí:** `PushToTalk` recibe el dispositivo ya resuelto. Decisión del diseño: evita repetir un intento de GPU fallido en cada recarga de SPEC 12.
- **Sí:** detectar la GPU con `ctranslate2.get_cuda_device_count()`, que es la comprobación que ya usa el README. Decisión del diseño: no añade dependencias.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `medium` en CPU tarda decenas de segundos por dictado y parece colgado | `WARNING` de lentitud con sugerencia de `small`; el log ya muestra la duración de cada transcripción. |
| El driver roto cuelga o aborta el proceso en lugar de lanzar una excepción en Python | `auto` primero consulta `get_cuda_device_count()`; un abort nativo queda sin cubrir y se resuelve con `--compute-device cpu` o `CUDA_VISIBLE_DEVICES=""`. |
| La GPU falla a medias y deja memoria ocupada antes del reintento en CPU | Se libera el modelo parcial (`gc.collect()`, como en `close()`) antes de reintentar. |
| Los dobles de `WhisperModel` no reflejan el error real de CUDA | Una prueba manual con `CUDA_VISIBLE_DEVICES=""` queda en el plan y en los criterios. |
| `auto` oculta que la GPU dejó de funcionar y el usuario nota solo la lentitud | `WARNING` en el log y notificación en cada arranque que cae a CPU. |

## Lo que **no** está en esta spec

- Elegir el modelo según el dispositivo o cambiar el modelo por defecto.
- Otros tipos de cómputo o clave `compute_type`.
- Otros aceleradores y selección de GPU por índice.
- Entorno conda sin CUDA.
- Cambio de dispositivo en caliente.
- Cambios en `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.
- Benchmark de CPU.

Cada uno, si se aborda, va en su propia spec.
