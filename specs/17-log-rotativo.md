# SPEC 17 — Log rotativo en archivo

> **Estado:** Aprobado
> **Depende de:** SPEC 07, SPEC 09, SPEC 14, SPEC 15, SPEC 16
> **Fecha:** 2026-10-09
> **Objetivo:** Escribir las mismas líneas `INFO`, `WARNING` y `ERROR` de la consola en `$XDG_STATE_HOME/speechflow/speechflow.log` con rotación por tamaño (1 MB y 3 copias), sin que un fallo del archivo impida arrancar.

## Por qué existe esta spec

Hoy el log solo existe en la terminal: al cerrarla, o al ejecutar `speechflow` como servicio `systemd` de la Fase 3, los mensajes (desconexiones del micrófono, errores de transcripción, avisos de configuración) se pierden. Un archivo con rotación los conserva sin crecer sin límite. Es el primer paso de la Fase 3 y lo necesita el servicio `systemd`, que no tiene terminal.

## Alcance

**Dentro:**

- Añadir `log_path()` a `src/speechflow/config.py`: `state_dir() / "speechflow.log"` (junto a `state_path()`).
- Ampliar `setup_logging()` en `src/speechflow/log.py` con un tercer manejador: `RotatingFileHandler` con `maxBytes = 1_048_576`, `backupCount = 3`, codificación `utf-8`, nivel `INFO`, mismo formato y hora local que la consola.
- Archivos resultantes: `speechflow.log`, `speechflow.log.1`, `speechflow.log.2`, `speechflow.log.3` (como máximo unos 4 MB).
- Crear la carpeta `state_dir()` si no existe al abrir el archivo.
- El archivo se crea con permisos `0600`, también tras cada rotación, porque el log incluye el texto dictado (`Insertado (...): {texto}`).
- Se escriben las mismas líneas que van a la consola, incluidas las anteriores a leer la configuración (el manejador se añade en `setup_logging()`, al principio de `main()`).
- No se escribe el banner ASCII (se imprime con `print`, no con el logger).
- Si el archivo no se puede abrir (`OSError`, o `RuntimeError` por falta de `HOME`), registrar un `WARNING` por consola y seguir solo con consola. Los errores de escritura posteriores los gestiona `logging` y no tumban la aplicación.
- Siempre activo: sin clave en el TOML ni opción de CLI.
- Actualizar `tests/test_log.py` y `tests/test_config.py` para el nuevo manejador y `log_path()`.
- Actualizar `README.md` (secciones del módulo `log.py`, rutas de **Configuración** y privacidad del log) y `TODO.md` (marcar "Archivo de log, rotación y carpeta `logs/`" y el elemento correspondiente de la Fase 3).

**Fuera de alcance (para futuras specs):**

- Claves `[log]` en el TOML (`enabled`, `max_bytes`, `backup_count`, `path`) y opciones de CLI para ruta o rotación.
- Niveles configurables, `--quiet`, `--verbose` y mensajes `DEBUG` (siguen en `TODO.md`).
- Formato JSON, colores y zona horaria distinta de la local.
- Rotación por tiempo, compresión de las copias y limpieza de logs antiguos.
- Seguridad entre procesos: dos instancias escribiendo a la vez (ya está desaconsejado en el README, "Una sola instancia").
- Marca de inicio de sesión, banner o versión dentro del archivo.
- Redactar u ocultar el texto dictado en el log.
- Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py`.
- Servicio `systemd` y bandeja del sistema (Fase 3).
- Cambios en `app.py` (salvo que la implementación demuestre que son imprescindibles).

## Modelo de datos

Esta spec no introduce estructuras de datos persistentes ni claves de configuración. Añade una ruta, constantes de rotación y un manejador:

```python
# src/speechflow/config.py
def log_path() -> Path:
    return state_dir() / "speechflow.log"      # ~/.local/state/speechflow/speechflow.log

# src/speechflow/log.py
LOG_MAX_BYTES = 1_048_576      # 1 MB por archivo
LOG_BACKUP_COUNT = 3           # speechflow.log.1 .. speechflow.log.3

class _PrivateRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler que crea cada archivo (también tras rotar) con permisos 0600."""
```

Mensaje nuevo (el resto no cambia):

```
WARNING No se puede escribir el log en {ruta}: {error}. Solo habrá log por consola.
```

Convenciones:

- `setup_logging()` sigue siendo idempotente: una segunda llamada no añade manejadores (el criterio actual `if logger.handlers` se conserva).
- El manejador de archivo se crea al final de `setup_logging()`, con los de consola ya instalados, para que el `WARNING` de fallo salga por `stderr`.
- Si `log_path()` lanza `RuntimeError` (sin `HOME`), se trata igual que un `OSError`.
- `log.py` importa `log_path` de `config.py`; `config.py` no importa `log.py`, así que no hay ciclo.
- `import speechflow.log` y `import speechflow.app` siguen sin abrir archivos ni crear carpetas; solo lo hace `setup_logging()`.
- `--list-devices` no llama a `setup_logging()` y no crea el archivo.

## Plan de implementación

1. Añadir `log_path()` a `config.py` y su test en `tests/test_config.py` (variable XDG ausente, vacía, relativa y absoluta, como el resto de rutas). Verificar: `pytest tests/test_config.py` pasa.
2. En `log.py`, añadir `_PrivateRotatingFileHandler` (abre con `os.open(..., 0o600)`) y las constantes `LOG_MAX_BYTES` y `LOG_BACKUP_COUNT`. Todavía sin usarlo en `setup_logging()`. Verificar: `python -c "import speechflow.log"` no crea ningún archivo.
3. Conectar el manejador al final de `setup_logging()`: crear `state_dir()`, abrir el archivo y, ante `OSError` o `RuntimeError`, registrar el `WARNING` y continuar. Verificar: `speechflow` arranca, las líneas de la consola aparecen también en `~/.local/state/speechflow/speechflow.log` con el mismo formato y el archivo tiene modo `600`.
4. Actualizar `tests/test_log.py` (el número de manejadores pasa de 2 a 3; el archivo recibe `INFO`, `WARNING` y `ERROR` y no `DEBUG`; no hay banner; rotación con valores reducidos; permisos `0600` tras rotar; carpeta no escribible y `HOME` ausente dan el `WARNING` y la consola sigue funcionando; `setup_logging()` dos veces no duplica el manejador de archivo). Verificar: `pytest` pasa y no escribe fuera de `tmp_path`.
5. Actualizar `README.md` (descripción de `log.py`, tabla de rutas, aviso de que el log contiene el texto dictado y cómo borrarlo) y `TODO.md` (marcar la spec y las ideas de archivo de log y rotación). Verificar: el README indica la ruta, el tamaño máximo y el contenido del log.

## Criterios de aceptación

- [ ] Al arrancar `speechflow` se crea `~/.local/state/speechflow/speechflow.log` (o `$XDG_STATE_HOME/speechflow/speechflow.log`) y contiene las líneas `INFO`, `WARNING` y `ERROR` que salen por consola, con el mismo formato.
- [ ] Las líneas de `resolve_config` (por ejemplo, `Configuración: valores por defecto`) también aparecen en el archivo.
- [ ] El archivo no contiene el banner ASCII, `SpeechFlow {versión}` ni `Powered by ...`.
- [ ] La salida por consola es idéntica a la anterior (mismos mensajes, flujos `stdout`/`stderr` y formato).
- [ ] Un dictado añade al archivo la línea `Insertado (...): {texto}` o `Sin texto reconocido (...)`.
- [ ] Al superar 1 MB, `speechflow.log` rota a `speechflow.log.1`, y nunca existe `speechflow.log.4`.
- [ ] Tras una rotación, el `speechflow.log` nuevo y las copias tienen modo `600`.
- [ ] `speechflow.log` se crea con modo `600`.
- [ ] Con `state_dir()` sin permisos de escritura, la app arranca, registra `No se puede escribir el log en ...` por `stderr` y sigue dictando.
- [ ] Sin `HOME` ni `XDG_STATE_HOME`, `setup_logging()` registra el mismo `WARNING` y no lanza excepciones.
- [ ] `setup_logging()` llamada dos veces deja exactamente un manejador de archivo.
- [ ] `speechflow --list-devices` no crea el archivo.
- [ ] `import speechflow.log` y `import speechflow.app` no crean archivos ni carpetas.
- [ ] Tras un cierre por `SIGTERM`, `SIGHUP` o `Ctrl+C`, el archivo contiene `Saliendo.` y `Modelo {modelo} liberado.`.
- [ ] `pytest` pasa con código 0 y `~/.local/state/speechflow` no cambia al ejecutarlo.
- [ ] `git diff main -- src/speechflow/app.py scripts` está vacío.
- [ ] `README.md` documenta la ruta, la rotación (1 MB x 3 copias) y que el log incluye el texto dictado.

## Decisiones

- **Sí:** `state_dir()/speechflow.log`, por elección del usuario. XDG reserva `STATE` para los logs, `state_dir()` ya existe (SPEC 14) y es donde escribirá el servicio `systemd`.
- **No:** carpeta `logs/` dentro de `state_dir()`. Añade un nivel para un único archivo.
- **No:** ruta configurable. Exige validar rutas y permisos y repartir una clave más por la SPEC 10.
- **Sí:** rotación por tamaño, 1 MB x 3 copias, por elección del usuario. Acota el uso de disco (unos 4 MB) sin hilos ni temporizadores, y un dictado genera pocas líneas, así que 1 MB cubre meses.
- **No:** rotación diaria. Un día con muchos dictados crece sin cota y los días sin uso dejan archivos vacíos.
- **No:** valores de rotación configurables. Añade claves, validación y documentación por valores que casi nadie cambia.
- **Sí:** mismas líneas `INFO`+ que la consola y siempre activo, por elección del usuario. Sin opciones nuevas y sin tocar el comportamiento de la consola.
- **No:** `[log] enabled`. Se puede añadir después sin romper nada; hoy no hay un caso que lo pida.
- **No:** nivel `DEBUG` en el archivo. No existen mensajes `DEBUG` ni `--verbose`; es otra spec.
- **Sí:** si el archivo no se puede abrir, `WARNING` y seguir con la consola, por elección del usuario. El dictado no debe depender del log; un disco lleno no puede impedir escribir.
- **No:** salir con código 1. Es lo que se hace con los errores de configuración inalcanzable, pero aquí el archivo es accesorio.
- **Sí:** añadir el manejador de archivo dentro de `setup_logging()`, no en `main()`. Así cubre los mensajes anteriores a `resolve_config` y `app.py` no cambia. Decisión del diseño, no preguntada al usuario.
- **Sí:** permisos `0600` mediante un manejador propio. El log guarda el texto dictado, que puede ser privado, y un `RotatingFileHandler` normal crea el archivo nuevo con el `umask` tras cada rotación. Decisión del diseño, no preguntada al usuario.
- **No:** ocultar el texto dictado en el log. Es útil para diagnosticar y el log ya lo mostraba en consola; se documenta en el README y se protege con permisos.
- **No:** banner en el archivo. Se imprime con `print` y repetiría ocho líneas en cada arranque.
- **Sí:** `log_path()` en `config.py` junto a `state_path()`. Concentra las rutas XDG en un solo módulo.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Dos instancias escriben a la vez y la rotación pierde líneas o falla al renombrar | Ya está desaconsejado ("Una sola instancia"); `logging` no tumba la app ante un error de rotación. |
| El log guarda texto dictado que puede ser sensible | Permisos `0600`, aviso en el README y rotación que acota cuánto se conserva; redactarlo queda fuera de alcance. |
| Un manejador propio para `0600` se desvía de `RotatingFileHandler` en futuras versiones de Python | El test de permisos tras rotar lo detecta; la subclase solo sobrescribe `_open`. |
| `SIGHUP` por cierre de terminal hace fallar la escritura en consola y el archivo queda como único registro | El archivo no depende de la terminal; `logging` descarta los errores de emisión. |
| `os._exit(0)` en la segunda señal pierde la última línea | El manejador vacía el búfer tras cada registro (`StreamHandler.flush`), así que el `WARNING` ya está en disco. |
| El nuevo manejador cambia `len(logger.handlers)` y rompe los tests existentes de la SPEC 16 | El paso 4 actualiza `tests/test_log.py`; `conftest.py` ya aísla `XDG_STATE_HOME` en `tmp_path`. |
| Disco lleno durante la escritura | `logging` imprime el error en `stderr` sin lanzar excepción; la app sigue. |

## Lo que **no** está en esta spec

- Claves `[log]` en el TOML u opciones de CLI para el archivo, la ruta o la rotación.
- `--quiet`, `--verbose`, niveles configurables y mensajes `DEBUG`.
- Formato JSON, colores y zona horaria.
- Rotación por tiempo, compresión y limpieza de logs antiguos.
- Redacción del texto dictado.
- Log en los scripts y en `audio.py`.
- Servicio `systemd`, daemon y bandeja del sistema (Fase 3).

Cada uno, si se aborda, va en su propia spec.
