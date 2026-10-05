# SPEC 09 — Banner ASCII de arranque en el log

> **Estado:** Implementado
> **Depende de:** SPEC 07
> **Fecha:** 2026-10-05
> **Objetivo:** Imprimir al principio del log de `push_to_talk.py` un banner con el arte ASCII de SpeechFlow, su nombre, su versión y la versión de `faster-whisper`, justo antes de la línea `Cargando ...`.

## Por qué existe esta spec

El banner de la SPEC 07 solo lista datos (`Modelo: ...`, `Dispositivo de audio: ...`) y aparece tras cargar el modelo. Al revisar una terminal que lleva horas abierta no hay una marca visual que separe una ejecución de otra ni diga qué versión de SpeechFlow corre. El usuario aportó un banner al estilo `banner.txt` de Spring Boot, con placeholders (`${application.title}`, `${application.version}`, `${spring-boot.version}`). Spring Boot no existe en este proyecto, así que los placeholders se sustituyen por valores reales de SpeechFlow.

## Alcance

**Dentro:**

- Añadir `log_banner()` a `src/speechflow/log.py`, que imprime el banner por stdout **sin** el formato de log (sin fecha ni nivel), para no deformar el arte ASCII.
- Contenido del banner, en este orden:
  1. El arte ASCII de `SpeechFlow` (constante `BANNER_ART`, ver Modelo de datos), sin espacios finales.
  2. `SpeechFlow {version}`, con `speechflow.__version__` (hoy `0.1.0`).
  3. `Powered by faster-whisper {version}`, con la versión instalada.
- Llamar a `log_banner()` en `scripts/push_to_talk.py` justo antes de `logger.info(f"Cargando {args.model} ...")`, es decir, tras validar `xdotool`, la sesión, `notify-send`, `--key`, `--switch-key` y el dispositivo.
- No imprimirlo con `--list-devices` ni cuando el arranque termina antes por un error de validación.
- Conservar sin cambios las líneas `INFO` del banner de datos de la SPEC 07 (`Modelo: ...`, `Dispositivo de audio: ...`, etc.).
- Actualizar `README.md` (salida de ejemplo de la sección Push-to-talk y la descripción de `log.py`) y el docstring del script si procede.

**Fuera de alcance (para futuras specs):**

- Archivo `banner.txt` externo, personalización del arte o desactivarlo con una opción (`--no-banner`).
- Colores ANSI en el banner.
- Mostrar el banner en `capture_mic.py` o `benchmark_stt.py`.
- Tomar la versión de `pyproject.toml` o de `git describe`; se usa `__version__` de `src/speechflow/__init__.py`.
- Versión de CUDA, VRAM o del driver en el banner.
- Mover o reformatear el banner de datos de la SPEC 07.
- Un módulo `banner.py` propio.

## Modelo de datos

No hay estructuras de datos persistentes nuevas. Interfaz pública nueva:

```python
# src/speechflow/log.py
BANNER_ART = r"""
________                       ______ _______________
__  ___/__________________________  /____  ____/__  /________      __
_____ \___  __ \  _ \  _ \  ___/_  __ \_  /_   __  /_  __ \_ | /| / /
____/ /__  /_/ /  __/  __/ /__ _  / / /  __/   _  / / /_/ /_ |/ |/ /
/____/ _  .___/\___/\___/\___/ /_/ /_//_/      /_/  \____/____/|__/
       /_/
"""

def log_banner() -> None: ...   # imprime BANNER_ART + 2 líneas por stdout, sin formato de log
```

Convenciones:

- Salida esperada, con la versión real en lugar de los ejemplos:

  ```text
  <arte ASCII, 6 líneas>
  SpeechFlow 0.1.0
  Powered by faster-whisper 1.2.0
  ```

- Se imprime con `print(..., flush=True)` a `sys.stdout`; no pasa por el logger. Una línea en blanco separa el banner de la primera línea con formato (`Cargando ...`).
- La versión de `faster-whisper` se obtiene con `importlib.metadata.version("faster-whisper")`. Si el paquete no tiene metadatos, la línea `Powered by` se imprime sin versión (`Powered by faster-whisper`), sin lanzar excepción.
- `log.py` importa `__version__` desde `speechflow`; no se duplica el número de versión.
- Los espacios finales del arte original se eliminan; el arte no cambia por lo demás.

## Plan de implementación

1. En `src/speechflow/log.py`, añadir `BANNER_ART` y `log_banner()` con la versión de `speechflow.__version__` y la de `faster-whisper`. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.log import log_banner; log_banner()"` imprime el arte, `SpeechFlow 0.1.0` y `Powered by faster-whisper <versión>`, sin fecha ni nivel.
2. En `scripts/push_to_talk.py`, llamar a `log_banner()` justo antes de `Cargando ...`. Verificar: arrancar el script muestra el banner antes de `Cargando`, y `--key tecla_falsa` y `--list-devices` no lo muestran.
3. Actualizar `README.md` y el docstring con la salida de ejemplo nueva. Verificar: el ejemplo del README coincide con la salida real del arranque.

## Criterios de aceptación

- [ ] `src/speechflow/log.py` expone `BANNER_ART` y `log_banner()`.
- [ ] `log_banner()` imprime el arte ASCII de SpeechFlow, `SpeechFlow {version}` y `Powered by faster-whisper {version}`.
- [ ] Ninguna línea del banner lleva fecha, hora ni nivel.
- [ ] El banner sale por stdout, no por stderr.
- [ ] La versión mostrada coincide con `speechflow.__version__` y con `importlib.metadata.version("faster-whisper")`.
- [ ] No aparece el texto `Spring Boot` ni ningún `${...}` sin resolver.
- [ ] El arranque normal imprime el banner justo antes de `Cargando ...` y antes de `Modelo: ...`.
- [ ] `--list-devices` no imprime el banner.
- [ ] `--key tecla_falsa`, `--switch-key tecla_falsa`, un `--device` inexistente y la falta de `xdotool` terminan con código 1 sin imprimir el banner.
- [ ] Las líneas `INFO` del banner de datos de la SPEC 07 se mantienen con el mismo texto.
- [ ] `capture_mic.py` y `benchmark_stt.py` producen la misma salida que antes.
- [ ] `README.md` muestra el banner en la salida de ejemplo.

## Decisiones

- **Sí:** sustituir los placeholders de Spring Boot por valores propios (`SpeechFlow`, `__version__`, versión de `faster-whisper`), por elección del usuario. Spring Boot no forma parte del stack; una línea `Powered by` útil nombra el motor real.
- **No:** imprimir los placeholders literales ni `Powered by Spring Boot`. Mostrarían texto falso y `${...}` sin resolver.
- **Sí:** banner sin prefijo de log, por stdout, por elección del usuario. El prefijo de fecha y nivel desalinearía el arte y lo alargaría unas 30 columnas.
- **No:** pasar el banner por el logger. Rompe el arte ASCII y mezcla un adorno con eventos.
- **Sí:** mostrarlo justo antes de `Cargando ...`, por elección del usuario. Los errores de validación no lo imprimen y las ejecuciones con un error de arranque no dejan un banner huérfano.
- **No:** mostrarlo como primera salida de `main()`. Se descartó para no imprimirlo cuando el script va a salir con error.
- **Sí:** `log_banner()` en `src/speechflow/log.py` y versión de `speechflow.__version__`, por elección del usuario. Reutiliza el módulo de salida de consola y una única fuente de versión. Esto amplía a `log.py` con una función nueva sin cambiar `setup_logging()` ni el formato de la SPEC 07.
- **No:** `banner.py` propio ni `banner.txt` externo. Más archivos para una constante de seis líneas.
- **Sí:** conservar el banner de datos de la SPEC 07 intacto. El nuevo es identidad visual; el existente es información de la ejecución.
- **Sí:** línea `Powered by` degradada sin versión si faltan metadatos. El arranque no debe fallar por un adorno.
- **Sí:** sin colores ni `--no-banner`. La verbosidad fija es el criterio de la SPEC 07.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El arte ASCII se corrompe al copiarlo (barras invertidas, espacios finales) | `BANNER_ART` es una cadena cruda (`r"""..."""`) y un criterio de aceptación exige que se imprima el arte; el paso 1 se revisa a ojo contra el original. |
| `importlib.metadata` no encuentra `faster-whisper` (nombre de distribución distinto) | Se captura `PackageNotFoundError` y se imprime `Powered by faster-whisper` sin versión. |
| El banner se entrelaza con líneas de stderr por el búfer de stdout | `print(..., flush=True)`; el banner se imprime antes de cualquier `logger.info`. |
| El banner de la SPEC 07 y el nuevo se confunden | El nuevo es el arte con nombre y versión; el de datos conserva el prefijo con marca de tiempo. La README los distingue. |

## Lo que **no** está en esta spec

- `banner.txt` externo, `--no-banner` y colores.
- Banner en `capture_mic.py` y `benchmark_stt.py`.
- Versión de CUDA, VRAM o driver en el banner.
- Cambios en el banner de datos, el formato de log o las notificaciones.
- Versionado desde `pyproject.toml` o `git describe`.

Cada uno, si se aborda, va en su propia spec.
