# SPEC 24 — Opciones `--quiet` / `--verbose` y niveles de log configurables

> **Estado:** Aprobado
> **Depende de:** SPEC 07, SPEC 09, SPEC 10, SPEC 16, SPEC 17
> **Fecha:** 2026-10-12
> **Objetivo:** Permitir elegir el nivel de log de la consola con `--quiet`, `--verbose` y `--log-level` (o `[log] level`) y el del archivo con `[log] file_level`, sin cambiar el comportamiento por defecto.

## Por qué existe esta spec

La SPEC 07 dejó la verbosidad fija en `INFO` y la SPEC 17 añadió el archivo con el mismo nivel. Quien ejecuta `speechflow` como servicio, o solo quiere ver avisos y errores en la terminal, no puede silenciar los mensajes `INFO`; y quien depura no tiene un nivel `DEBUG`. Esta spec añade la infraestructura de niveles (opciones, claves de TOML y reajuste tras leer la configuración). No añade mensajes `DEBUG` nuevos salvo uno de comprobación.

## Alcance

**Dentro:**

- Opciones de CLI en `src/speechflow/app.py`, mutuamente excluyentes (grupo exclusivo de `argparse`):
  - `--quiet`: consola en `warning`.
  - `--verbose`: consola en `debug`.
  - `--log-level {debug,info,warning,error}`: consola en ese nivel.
- Claves `[log]` en `src/speechflow/config.py` (campos `Config.log_level` y `Config.log_file_level`, esquema `_SCHEMA["log"]` y líneas en la plantilla de `write_emergency`):
  - `[log] level` (`str`, defecto `"info"`): nivel de la consola.
  - `[log] file_level` (`str`, defecto `"info"`): nivel del archivo de la SPEC 17.
  - Valores válidos: `"debug"`, `"info"`, `"warning"`, `"error"` (en minúsculas). Otro valor hace inválido el archivo con un mensaje que nombra `log.level` o `log.file_level`.
- Precedencia del nivel de consola: `--quiet` / `--verbose` / `--log-level` > `[log] level` > `info`.
- El nivel del archivo solo lo fija `[log] file_level`; **las opciones de CLI no lo tocan**, así que `--quiet` deja el archivo registrando igual que hoy.
- `setup_logging(console_level: str = "info")` en `src/speechflow/log.py` acepta el nivel inicial de la consola y fija el logger en `DEBUG` (el filtrado pasa a los manejadores). Nueva función `apply_log_levels(console_level: str, file_level: str) -> None` que reajusta los manejadores ya instalados.
- Reglas de la consola con el nivel `L`:
  - el manejador de `stdout` emite los registros con nivel `L` ≤ nivel < `WARNING` (si `L` ≥ `WARNING`, no emite nada);
  - el manejador de `stderr` emite `WARNING` y `ERROR` si `L` ≤ `WARNING`; con `L = error` solo `ERROR`.
- Orden de arranque en `main()`:
  1. `setup_logging(nivel_cli)` con el nivel de las opciones de CLI si se dio alguna, si no `info`.
  2. `resolve_config()` (sus líneas `INFO` salen según el nivel inicial).
  3. `apply_log_levels(nivel_consola_final, config.log_file_level)`.
  4. `log_banner()` solo si el nivel final de consola es `debug` o `info`.
  5. El resto del arranque.
- El banner ASCII pasa a imprimirse **después** de `resolve_config()` (antes iba antes). La línea `Configuración: ...` queda por encima del banner.
- Un mensaje `DEBUG` de comprobación, emitido justo después de `apply_log_levels`: `Niveles de log: consola=debug, archivo=info`. Es el único mensaje `DEBUG` de esta spec.
- Las notificaciones de escritorio (SPEC 06) no dependen del nivel y no cambian.
- Actualizar `tests/test_log.py`, `tests/test_config.py` y `tests/test_app_helpers.py` y la documentación (`speechflow.example.toml`, `README.md`, `TODO.md`).

**Fuera de alcance (para futuras specs):**

- Más mensajes `DEBUG` (VAD, segmentos de Whisper, rutas, tiempos internos).
- Cambiar el nivel de forma distinta del arranque: en caliente con una tecla o señal.
- Que `--quiet` / `--verbose` afecten al archivo, o una opción de CLI para `file_level`.
- Otros niveles (`critical`, `trace`) y mayúsculas (`INFO`).
- Formato JSON, colores y zona horaria (siguen en `TODO.md`).
- Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py`.
- Ruta, tamaño o número de copias del archivo configurables.
- Variable de entorno para el nivel.
- Cambios en las notificaciones de escritorio, `notifier.py`, `transcriber.py`, `inserter.py` y `scripts/`.

## Modelo de datos

```python
# src/speechflow/config.py
LOG_LEVELS = ("debug", "info", "warning", "error")

@dataclass(frozen=True)
class Config:
    ...
    log_level: str = "info"        # [log] level; nivel de la consola
    log_file_level: str = "info"   # [log] file_level; nivel del archivo de log

_SCHEMA["log"] = {
    "level": ((str,), "log_level"),
    "file_level": ((str,), "log_file_level"),
}
```

```toml
[log]
# level = "info"        # nivel de la consola: "debug", "info", "warning" o "error"; --quiet, --verbose y --log-level ganan
# file_level = "info"   # nivel del archivo speechflow.log: mismos valores; las opciones de CLI no lo cambian
```

```python
# src/speechflow/log.py
def setup_logging(console_level: str = "info") -> logging.Logger: ...
def apply_log_levels(console_level: str, file_level: str) -> None: ...
```

Convenciones:

- `LOG_LEVELS` vive en `config.py` (como `COMPUTE_DEVICES`); `log.py` ya importa de `config.py`, así que no hay ciclo.
- Los nombres de nivel se traducen a constantes de `logging` en `log.py` (`debug` → `logging.DEBUG`, etc.).
- `setup_logging()` sigue siendo idempotente: una segunda llamada no añade manejadores ni cambia los niveles.
- `--quiet`, `--verbose` y `--log-level` solo cuentan si se escribieron (defecto `None`), como el resto de opciones.
- `--list-devices` no llama a `setup_logging()` y no se ve afectado.
- Los niveles se leen solo al arrancar; cambiarlos exige reiniciar.
- Los `ERROR` (por ejemplo, el archivo de configuración inexistente o `xdotool` ausente) salen con cualquier nivel.

## Plan de implementación

1. En `config.py`, añadir `LOG_LEVELS`, `Config.log_level`, `Config.log_file_level`, `_SCHEMA["log"]`, la validación (cada valor en `LOG_LEVELS`, con mensaje que nombra `log.level` o `log.file_level`) y las líneas `[log]` de la plantilla de `write_emergency`. Tests en `tests/test_config.py` (defectos `"info"`, valores válidos, `"INFO"` y `"trace"` inválidos con la clave en el mensaje, tipo incorrecto, clave desconocida en `[log]`, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. En `log.py`, fijar el logger en `DEBUG`, dar a `setup_logging()` el parámetro `console_level` y añadir `apply_log_levels()` con las reglas de `stdout` / `stderr` del alcance y el nivel del manejador de archivo. Tests en `tests/test_log.py` (por cada nivel de consola, qué líneas salen por `stdout` y `stderr`; `file_level` independiente de la consola; idempotencia; `DEBUG` solo llega al archivo con `file_level = "debug"`). Verificar: `pytest tests/test_log.py` pasa y el comportamiento por defecto no cambia.
3. En `app.py`, añadir el grupo exclusivo `--quiet` / `--verbose` / `--log-level`, resolver el nivel inicial y el final, reordenar el arranque (`setup_logging` → `resolve_config` → `apply_log_levels` → banner condicional) y emitir el `DEBUG` `Niveles de log: ...`. Tests en `tests/test_app_helpers.py` (precedencia CLI > TOML > `info`, exclusión mutua, banner omitido con `warning` y `error`, orden de arranque). Verificar: `pytest` pasa y `speechflow --quiet` solo muestra `WARNING` y `ERROR`.
4. Documentar en `speechflow.example.toml` (sección `[log]`) y `README.md` (opciones de CLI, claves `[log]`, qué niveles muestra cada uno, `--quiet` no cambia el archivo, el banner se omite con `warning` o más) y marcar en `TODO.md` los dos elementos de `--quiet` / `--verbose`. Verificar: el README coincide con el comportamiento real.

## Criterios de aceptación

- [ ] `Config()` tiene `log_level == "info"` y `log_file_level == "info"`.
- [ ] `[log] level` y `[log] file_level` aceptan `"debug"`, `"info"`, `"warning"` y `"error"`.
- [ ] `[log] level = "trace"` y `[log] level = "INFO"` hacen inválido el archivo con un mensaje que nombra `log.level`.
- [ ] `[log] file_level = "trace"` hace inválido el archivo con un mensaje que nombra `log.file_level`.
- [ ] Una clave desconocida en `[log]` se rechaza como en las demás secciones.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] Sin opciones ni claves, la consola y el archivo se comportan igual que antes (salvo el orden banner / `Configuración:`).
- [ ] `speechflow --quiet` no muestra líneas `INFO` ni el banner; sí muestra `WARNING` y `ERROR`.
- [ ] `speechflow --verbose` muestra el banner y la línea `DEBUG` `Niveles de log: consola=debug, archivo=info`.
- [ ] `speechflow --log-level error` solo muestra `ERROR` y omite el banner.
- [ ] Con `--log-level warning`, un `WARNING` sale por `stderr` y ninguna línea sale por `stdout`.
- [ ] `--quiet --verbose` (y cualquier combinación de las tres opciones) termina con el error de uso de `argparse`.
- [ ] `--quiet` gana sobre `[log] level = "debug"`; `[log] level = "warning"` sin opciones de CLI da una consola en `warning`.
- [ ] Con `--quiet`, el archivo `speechflow.log` sigue recibiendo las líneas `INFO` (incluido `Insertado (...)`).
- [ ] Con `[log] file_level = "warning"`, el archivo no recibe líneas `INFO` posteriores a leer la configuración.
- [ ] Con `[log] file_level = "debug"`, el archivo recibe la línea `DEBUG` `Niveles de log: ...`.
- [ ] Con nivel de consola `warning` o `error`, las notificaciones de escritorio siguen siendo las de la SPEC 06.
- [ ] Los `ERROR` de arranque (`xdotool` ausente, configuración inexistente) salen con `--log-level error`.
- [ ] `setup_logging()` llamada dos veces no duplica manejadores ni líneas.
- [ ] `speechflow --list-devices` sale igual que antes y no crea el archivo de log.
- [ ] `pytest` pasa con código 0 y no escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts src/speechflow/transcriber.py src/speechflow/notifier.py` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[log] level`, `[log] file_level`, `--quiet`, `--verbose` y `--log-level`.

## Decisiones

- **Sí:** `--quiet` y `--verbose` solo cambian la consola, por elección del usuario. El archivo es el registro de diagnóstico y debe seguir completo aunque la terminal esté en silencio.
- **No:** que las opciones de CLI cambien también el archivo. Un `--quiet` dejaría sin registro justo cuando se usa como servicio sin terminal.
- **Sí:** claves `[log] level` y `[log] file_level` en el TOML, por elección del usuario. Permiten consola silenciosa con archivo en `debug` y persisten sin repetir opciones en cada arranque.
- **No:** una sola clave de nivel para ambos destinos. No permitiría esa combinación.
- **Sí:** `--quiet`, `--verbose` y `--log-level`, mutuamente excluyentes, por elección del usuario. Los atajos cubren el uso común y `--log-level` cubre `error` sin editar el TOML.
- **Sí:** el archivo mantiene `INFO` por defecto e independiente de la CLI, por elección del usuario. No cambia el comportamiento actual de la SPEC 17.
- **Sí:** solo infraestructura de niveles, por elección del usuario; los mensajes `DEBUG` concretos van en una spec posterior. Evita mezclar esta spec con decidir qué diagnóstico merece registrarse.
- **Sí:** un único `DEBUG` de comprobación (`Niveles de log: ...`). Decisión del diseño: sin él no se puede verificar que `--verbose` y `file_level = "debug"` funcionan.
- **Sí:** `--quiet` y `--verbose` omiten el banner solo en `warning` o más, por elección del usuario. El banner es salida informativa, igual que las líneas `INFO`; las notificaciones no dependen del log y no cambian.
- **Sí:** reajustar los niveles tras `resolve_config()`, por elección del usuario. El nivel del TOML no se conoce antes de leer el archivo, y así `setup_logging()` sigue al inicio de `main()` como en la SPEC 17.
- **No:** leer `[log]` antes de instalar el logger. Obliga a parsear el TOML dos veces o a perder los mensajes de `resolve_config()`.
- **Sí:** mover el banner después de `resolve_config()`. Decisión del diseño: es la única forma de decidir si se imprime con el nivel final. Efecto visible: `Configuración: ...` aparece antes del banner.
- **Sí:** el logger se fija en `DEBUG` y filtran los manejadores. Decisión del diseño: así consola y archivo pueden tener niveles distintos sin que el logger descarte registros.
- **Sí:** nombres de nivel en minúsculas y solo cuatro valores. Decisión del diseño: coincide con el estilo de `device` y `mode`; `critical` no se usa en el código.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El `INFO` `Configuración: ...` y los avisos de `resolve_config()` salen con el nivel inicial, no con el del TOML | Es el comportamiento acordado; con `--quiet` o `--log-level` la CLI ya los cubre. Se documenta en el README. |
| Mover el banner cambia el orden de la salida y los criterios de la SPEC 09 ("antes de `Cargando ...`") | Sigue yendo antes de `Cargando ...`; solo cambia su posición respecto a `Configuración:`. Los tests lo fijan. |
| Un `[log] level = "error"` oculta avisos que el usuario necesita (por ejemplo, la caída a CPU) | El archivo sigue en `info` por defecto y las notificaciones no cambian. |
| Manejadores con filtros mal combinados duplican o pierden líneas entre `stdout` y `stderr` | Tests por cada nivel de consola que cuentan líneas en cada flujo. |
| El archivo con `file_level = "warning"` oculta el texto dictado (`Insertado`) | Es una ventaja de privacidad, no un fallo; se documenta. |
| `--verbose` no muestra casi nada nuevo y parece no hacer nada | El `DEBUG` de comprobación lo evidencia; la spec lo declara y los mensajes `DEBUG` quedan para otra spec. |

## Lo que **no** está en esta spec

- Más mensajes `DEBUG` en el código.
- Cambiar el nivel en caliente.
- Opciones de CLI que cambien el archivo, o variable de entorno para el nivel.
- Formato JSON, colores y zona horaria.
- Log en los scripts y en `audio.py`.
- Ruta, tamaño y copias del archivo configurables.

Cada uno, si se aborda, va en su propia spec.
