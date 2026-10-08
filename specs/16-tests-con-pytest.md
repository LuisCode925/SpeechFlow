# SPEC 16 — Tests con `pytest`

> **Estado:** Aprobado
> **Depende de:** SPEC 04, SPEC 05, SPEC 10, SPEC 11, SPEC 12, SPEC 14, SPEC 15
> **Fecha:** 2026-10-08
> **Objetivo:** Añadir una suite de `pytest` que cubra `config`, `audio`, `log`, `notifier`, `inserter`, `transcriber`, los helpers de `app.py` y `PushToTalk` con dobles, sin hardware ni GPU por defecto, y con el smoke test de GPU marcado y excluido.

## Por qué existe esta spec

Tras las SPEC 13–15 el paquete es instalable, tiene rutas independientes del repo y un cierre limpio, pero cada criterio de aceptación se ha verificado a mano con el micrófono, `xdotool` y el modelo real. `PushToTalk` concentra hilos, temporizadores y un `lock` (SPEC 11, 12 y 15) y es donde una regresión pasa más fácilmente desapercibida. Es el último paso de la Fase 2 y deja una red de seguridad antes de la Fase 3 (`systemd`, log a archivo, bandeja), que tocará `app.py` y `log.py`.

## Alcance

**Dentro:**

- Declarar `pytest` en `pyproject.toml`: extra `dev` (`[project.optional-dependencies]`), marcador `gpu` y configuración en `[tool.pytest.ini_options]`.
- Excluir por defecto los tests marcados `gpu` (`addopts = "-m 'not gpu'"`); se ejecutan con `pytest -m gpu`.
- Crear la carpeta `tests/` en la raíz del repo con `conftest.py` y un archivo por módulo (ver **Modelo de datos**).
- `conftest.py` con aislamiento automático: `HOME`, `XDG_CONFIG_HOME` y `XDG_STATE_HOME` apuntan a `tmp_path`; `subprocess.run` está sustituido por un doble que registra las llamadas; `notifier` vuelve a su estado inicial tras cada test; y, si no hay `DISPLAY`, `PYNPUT_BACKEND=dummy` se fija antes de importar `speechflow.app`.
- Dobles de `sounddevice` (lista de dispositivos, `InputStream`, reinicio de PortAudio), de `Recorder`, de `Transcriber`/`WhisperModel`, de `notify` y de `insert_text`. Ningún test abre un micrófono, ejecuta `xdotool` o `notify-send`, ni carga un modelo salvo los marcados `gpu`.
- Tests de `config.py`: rutas XDG (variable ausente, vacía, relativa, absoluta, sin `HOME`), `find_config`, `load_config` (válido, omitido, sección y clave desconocidas, tipos, `bool` frente a `int`, rangos de `min_seconds`, `max_seconds`, `watch_interval` e `idle_timeout`), `write_emergency` (crea, no pisa, la plantilla se lee con `load_config` y da `Config()`), `load_state_device` y `save_state_device` (ida y vuelta, archivo ilegible, tipo inválido, escritura atómica).
- Tests de `audio.py` con `sounddevice` falseado: `parse_device`, `default_device`, `input_devices`, `device_index`, `device_name`, `input_device_by_name`, `next_input_device` (vuelta al principio, dispositivo ausente, sin dispositivos), `resample` (misma tasa y tasa distinta), `measure`, `save_wav` y `Recorder` (`start`, `stop`, `active`, stream caído).
- Tests de `log.py` (`setup_logging` no duplica manejadores, INFO a `stdout` y WARNING/ERROR a `stderr`, formato, `log_banner`), `notifier.py` (`set_enabled`, `notify` sin `notify-send`), `inserter.py` (texto vacío, argumentos de `xdotool`) y `transcriber.py` con `WhisperModel` falseado (`transcribe` con audio vacío, conversión a `float32`, texto unido, `close` idempotente).
- Tests de los helpers de `app.py`: `parse_key` (con `DISPLAY`; se salta sin él), `describe_device`, `load_transcriber` y `resolve_config` (archivo válido, inválido, ausente, `--config` inexistente con `SystemExit(1)`, sin `HOME`, plantilla de emergencia).
- Tests de `PushToTalk` con dobles, agrupados en cuatro bloques:
  - **Ciclo de dictado:** pulsar y soltar, repetición automática de la tecla, grabación más corta que `min_seconds` descartada, corte por `max_seconds`, texto vacío, error del modelo, inserción del texto, error al abrir el micrófono y micrófono desconectado al pulsar.
  - **Cambio de entrada y vigilante:** `switch_device` solo en `IDLE`, un único dispositivo, error al releer, guardado en `state.toml` y fallo de guardado; `_watch` en desconexión, reconexión y pérdida durante la grabación.
  - **Inactividad y recarga:** `idle_timeout` libera el modelo, `idle_timeout = 0` no lo libera, pulsar con el modelo descargado recarga en paralelo, fallo de recarga descarta el audio.
  - **Cierre (SPEC 15):** `begin_shutdown` descarta la grabación en curso y ignora las teclas, `shutdown` espera a la transcripción y a la recarga, devuelve `False` sin llamar a `close()` si vence el tope, y no hace nada con el modelo ya descargado.
- Un smoke test marcado `gpu` que carga `Transcriber()` con el modelo por defecto (`medium`), transcribe un segundo de silencio y llama a `close()` dos veces.
- Añadir `.pytest_cache/` a `.gitignore`.
- Cambiar `environment.yml` para instalar el paquete con el extra: `- -e .[dev]`.
- Actualizar `README.md` (sección de desarrollo y tests) y `TODO.md` (marcar la SPEC 16 y "Tests con `pytest`").

**Fuera de alcance (para futuras specs):**

- `main()`: argparse, precedencia CLI > estado > archivo > defectos, instalación de manejadores de señales y arranque del listener. Se sigue verificando a mano.
- Tests de integración con micrófono, `xdotool`, `notify-send`, teclado global o sesión X reales.
- Un ciclo de dictado completo con modelo real (más allá del smoke test de `Transcriber`).
- Cobertura mínima exigida (`pytest-cov`), CI (GitHub Actions), `tox`/`nox`, `pre-commit`, linters y comprobación de tipos.
- Tests de `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.
- Corregir en `src/` los fallos que los tests descubran: se anotan en `TODO.md` y el test queda como `xfail(strict=True)`.
- Cambios en `src/speechflow/` y en `scripts/`.
- Refactor de `PushToTalk` para inyectar dependencias.

## Modelo de datos

Esta spec no introduce estructuras de datos de la aplicación. Añade configuración de `pytest` y una carpeta de tests.

```toml
# pyproject.toml (secciones nuevas)
[project.optional-dependencies]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not gpu'"
markers = ["gpu: usa la GPU y el modelo real; se excluye por defecto, ejecutar con `pytest -m gpu`"]
```

```
tests/
  conftest.py              # aislamiento autouse, dobles de sounddevice/Recorder/Transcriber, teclas centinela
  test_config.py
  test_audio.py
  test_log.py
  test_notifier.py
  test_inserter.py
  test_transcriber.py      # WhisperModel falseado
  test_transcriber_gpu.py  # @pytest.mark.gpu, modelo real
  test_app_helpers.py      # parse_key, describe_device, load_transcriber, resolve_config
  test_push_to_talk.py     # clases: TestDictation, TestSwitchAndWatch, TestIdleAndReload, TestShutdown
```

Convenciones:

- Los nombres de test siguen el patrón `test_<comportamiento>` en español y sin tildes (`test_descarta_grabacion_corta`); los docstrings también van en español.
- Los tests de `PushToTalk` usan teclas centinela (`keyboard.KeyCode.from_char("r")` y `"f"`), válidas con el backend `dummy`, y `idle_timeout`, `min_seconds` y `max_seconds` de decenas de milisegundos.
- Los hilos y temporizadores se sincronizan con `threading.Event` y `join(timeout)`; ningún test usa `time.sleep` de más de 0,2 s ni espera más de 2 s por una condición.
- Los dobles de `Transcriber` bloquean en un `Event` cuando el test necesita una transcripción "en curso" y lo liberan en el `finally` del test para no dejar hilos vivos.
- El doble de `subprocess.run` registra `(args, kwargs)`; `notifier` e `inserter` se prueban contra él, no contra los ejecutables.
- Los tests no escriben en el repo, en el `HOME` real ni en las rutas XDG reales.
- Los mensajes del log se comprueban con `caplog` sobre el logger `speechflow`, con el texto exacto de las SPEC anteriores.

## Plan de implementación

1. Añadir a `pyproject.toml` el extra `dev`, el marcador `gpu` y `[tool.pytest.ini_options]`; poner `- -e .[dev]` en `environment.yml`; añadir `.pytest_cache/` a `.gitignore`; crear `tests/conftest.py` con el aislamiento autouse y `tests/test_config.py`. Verificar: `pip install -e .[dev]` en el entorno `speechflow` termina sin error y `pytest` pasa y no crea archivos fuera de `tmp_path`.
2. Añadir el doble de `sounddevice` a `conftest.py` y `tests/test_audio.py`. Verificar: `pytest tests/test_audio.py` pasa sin ningún dispositivo de audio real (por ejemplo, con la tarjeta de sonido deshabilitada o en un contenedor).
3. Añadir `test_log.py`, `test_notifier.py`, `test_inserter.py`, `test_transcriber.py` y `test_transcriber_gpu.py`. Verificar: `pytest` los salta o deselecciona según corresponda (el `gpu` aparece como `deselected`) y `pytest -m gpu` carga `medium`, transcribe el silencio y termina sin error.
4. Añadir `test_app_helpers.py`. Verificar: `pytest` pasa con `DISPLAY` definido y, con `env -u DISPLAY pytest`, `parse_key` se salta y el resto pasa.
5. Crear `tests/test_push_to_talk.py` con los dobles y `TestDictation`. Verificar: `pytest tests/test_push_to_talk.py` pasa y dura menos de 5 s.
6. Añadir `TestSwitchAndWatch` y `TestIdleAndReload`. Verificar: ídem, sin hilos vivos al terminar la sesión.
7. Añadir `TestShutdown`. Verificar: ídem; dejar `xfail(strict=True)` y una línea en `TODO.md` por cada fallo real de `src/` que aparezca.
8. Actualizar `README.md` (instalación con el extra `dev`, `pytest`, `pytest -m gpu`, `env -u DISPLAY`) y `TODO.md` (marcar la SPEC 16 y "Tests con `pytest`"). Verificar: el README explica cómo ejecutar la suite normal y la de GPU.

## Criterios de aceptación

- [ ] `pip install -e .[dev]` en el entorno `speechflow` termina sin error y `environment.yml` instala el extra `dev`.
- [ ] `pytest` sin argumentos termina con código 0 y muestra los tests `gpu` como `deselected`.
- [ ] `pytest -m gpu` carga el modelo `medium` en la GPU, transcribe un segundo de silencio y termina con código 0.
- [ ] `env -u DISPLAY pytest` termina con código 0 (solo los tests de `parse_key` se saltan).
- [ ] `pytest` sin argumentos dura menos de 30 s.
- [ ] Tres ejecuciones consecutivas de `pytest` dan el mismo resultado, sin tests intermitentes.
- [ ] Ningún test abre un `InputStream` real, ejecuta `xdotool` o `notify-send`, ni carga un modelo salvo los marcados `gpu`.
- [ ] Tras ejecutar la suite, `git status` queda limpio salvo los archivos de la spec y `~/.config/speechflow` y `~/.local/state/speechflow` no han cambiado.
- [ ] `git diff main -- src scripts` está vacío.
- [ ] Hay al menos un test por cada función pública de `config.py`, `audio.py`, `log.py`, `notifier.py` e `inserter.py`, y por `Transcriber.transcribe` y `Transcriber.close`.
- [ ] Hay tests de `parse_key`, `describe_device`, `load_transcriber` y `resolve_config` (los cuatro caminos: archivo válido, inválido, ausente y `--config` inexistente).
- [ ] Cada bloque de `PushToTalk` descrito en el alcance tiene al menos un test por comportamiento listado.
- [ ] Un test comprueba que `shutdown(timeout)` con una transcripción bloqueada devuelve `False`, registra el `WARNING` del tope y no llama a `close()`.
- [ ] Al terminar la sesión de `pytest` no queda ningún hilo no daemon vivo.
- [ ] `import speechflow.app` sigue sin efectos secundarios con los dobles activos (ningún test lo contradice).
- [ ] `README.md` documenta cómo instalar el extra `dev`, ejecutar la suite por defecto y ejecutar `pytest -m gpu`.
- [ ] `.gitignore` incluye `.pytest_cache/`.

## Decisiones

- **Sí:** cubrir todo el paquete salvo `main()`, por elección del usuario. Los módulos pequeños (`log`, `notifier`, `inserter`) cuestan pocos tests y fijan formatos que la Fase 3 va a tocar.
- **No:** probar `main()`. Mezcla argparse, señales, listener y GPU; los dobles necesarios replicarían el orden de arranque y se romperían con cada cambio. Su comportamiento ya está en los criterios de las SPEC 10, 14 y 15 y se verifica a mano.
- **Sí:** `monkeypatch` sin tocar `src/`, por elección del usuario. La suite no cambia el comportamiento de producción y es la red de seguridad para refactorizar después.
- **No:** inyección de dependencias en `PushToTalk`. Obligaría a modificar `app.py` en una spec de solo tests; si más adelante conviene, va en su propia spec.
- **Sí:** un smoke test `gpu` con el modelo por defecto `medium`, por elección del usuario. Verifica lo que usa la app y ya está en la caché de Hugging Face; el coste es tiempo y VRAM, por eso se excluye por defecto.
- **No:** `tiny` para el smoke test. Es más rápido pero no ejercita la carga con el modelo y el `compute_type` reales.
- **Sí:** marcador `gpu` excluido con `addopts = "-m 'not gpu'"`. `pytest -m gpu` en la línea de órdenes tiene prioridad sobre `addopts`, así que no hace falta otro archivo ni variable.
- **Sí:** `pytest` en el extra `dev` de `pyproject.toml` y `environment.yml` con `-e .[dev]`, por elección del usuario. Una sola fuente de dependencias de desarrollo.
- **Sí:** `PYNPUT_BACKEND=dummy` si no hay `DISPLAY`, por elección del usuario. `import speechflow.app` falla sin X y el backend `dummy` permite correr la suite en una terminal o contenedor sin servidor gráfico.
- **No:** exigir X siempre. Impediría ejecutar la suite en entornos sin pantalla.
- **Sí:** saltar solo los tests de `parse_key` sin `DISPLAY`. Con el backend `dummy` todas las teclas valen `Key.alt`, así que no son verificables.
- **Sí:** teclas centinela (`KeyCode.from_char`) en los tests de `PushToTalk`. Funcionan con cualquier backend y evitan depender de `Key.ctrl_r`.
- **Sí:** aislamiento autouse de `HOME` y `XDG_*` hacia `tmp_path`. Sin él, `write_emergency` y `save_state_device` escribirían en la configuración real del usuario.
- **Sí:** los fallos reales de `src/` que salgan se registran como `xfail(strict=True)` y en `TODO.md`. Mantiene la spec acotada a tests y evita que un test rojo bloquee la suite.
- **Sí:** nombres de test y docstrings en español, igual que el resto del repo.
- **No:** `pytest-cov`, CI ni linters. Son decisiones de proceso independientes de tener tests.
- **No:** sincronizar hilos con `time.sleep` largos. Los `Event` hacen la suite rápida y evitan tests intermitentes.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `import speechflow.app` importa `pynput` y falla sin servidor X | `conftest.py` fija `PYNPUT_BACKEND=dummy` antes de la importación si no hay `DISPLAY`; se comprueba con `env -u DISPLAY pytest`. |
| El backend `dummy` cambia el comportamiento de `keyboard.Key` (todas las teclas iguales) | Los tests de `PushToTalk` usan `KeyCode.from_char`; `parse_key` se salta sin `DISPLAY`. |
| Tests con hilos y temporizadores intermitentes | `Event` y `join(timeout)` en lugar de `sleep`; tiempos de decenas de ms y tope de 2 s por espera; tres ejecuciones seguidas como criterio. |
| Un doble que bloquea una transcripción deja un hilo vivo y cuelga `pytest` al salir | El hilo es `daemon` en la app y el doble se libera en un `finally`; criterio de aceptación sobre hilos vivos. |
| Parchear `speechflow.app.Recorder`, `notify` o `insert_text` ata los tests a los nombres importados | Aceptado por la decisión de no tocar `src/`; un cambio de nombres rompe los tests de forma visible. |
| Parchear `sounddevice` globalmente afecta a `audio.py` y `app.py` a la vez | Ambos usan el módulo `sd`; el parche se aplica con `monkeypatch` sobre el módulo y se deshace tras cada test. |
| Los tests descubren un fallo real de `src/` | Se anota en `TODO.md` y el test queda como `xfail(strict=True)`; se corrige en otra spec. |
| El smoke test `gpu` falla en una máquina sin CUDA o sin el modelo en caché | Está excluido por defecto; el README indica que requiere GPU y el modelo `medium` descargado. |
| `subprocess.run` sustituido globalmente oculta un uso no previsto de `xdotool` | El doble registra las llamadas y los tests de `inserter` y `notifier` comprueban los argumentos exactos. |
| La suite escribe en `~/.config/speechflow` si falla el aislamiento | El `autouse` cambia `HOME` y `XDG_*` antes de cada test; un criterio de aceptación comprueba que los archivos reales no cambian. |

## Lo que **no** está en esta spec

- Tests de `main()`, de la precedencia de la configuración en el arranque y de los manejadores de señales.
- Tests de integración con hardware, `xdotool`, `notify-send` o sesión X reales.
- Cobertura mínima, CI, `tox`/`nox`, `pre-commit`, linters y comprobación de tipos.
- Tests de `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.
- Un ciclo de dictado completo con modelo real.
- Correcciones en `src/` o refactor de `PushToTalk` para inyectar dependencias.
- Servicio `systemd`, archivo de log con rotación y bandeja del sistema (Fase 3).

Cada uno, si se aborda, va en su propia spec.
