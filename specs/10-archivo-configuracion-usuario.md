# SPEC 10 — Archivo de configuración del usuario

> **Estado:** Aprobado
> **Depende de:** SPEC 05, SPEC 06, SPEC 07, SPEC 08, SPEC 09
> **Fecha:** 2026-10-05
> **Objetivo:** Permitir fijar en un archivo TOML las opciones de `push_to_talk.py` (modelo, idioma, teclas, dispositivo, límites de grabación y notificaciones), con precedencia CLI > archivo > defectos, un archivo de emergencia cuando falta o falla, y persistencia del micrófono elegido con la tecla de cambio.

## Por qué existe esta spec

Hoy toda la configuración vive en argumentos de CLI y constantes del código: para usar siempre otro modelo, otras teclas o un micrófono concreto hay que repetir los argumentos en cada arranque o editar el script. Las SPEC 01, 05, 06 y 08 dejaron fuera "el archivo de configuración de usuario" y la persistencia del dispositivo; esta spec cubre ambas cosas. Al ser un proyecto de pruebas, el archivo por defecto vive en la raíz del repo, con la ruta estándar XDG como alternativa.

## Alcance

**Dentro:**

- Nuevo módulo `src/speechflow/config.py` que localiza, lee, valida y combina la configuración.
- Formato **TOML**, leído con `tomllib` (stdlib de Python 3.12); sin dependencias nuevas.
- Búsqueda del archivo, usando el primero que exista (no se fusionan):
  1. `--config RUTA` (opción nueva de `push_to_talk.py`).
  2. `speechflow.toml` en la raíz del repo (la carpeta que contiene `scripts/` y `src/`).
  3. `~/.config/speechflow/config.toml`.
- Claves admitidas (todas opcionales), con el defecto actual del código:
  - `[model]` `name` (`"medium"`), `language` (`"es"`).
  - `[keys]` `record` (`"ctrl_r"`), `switch` (`"f8"`).
  - `[audio]` `device` (entero o texto; igual que `--device`; sin defecto: el de `default_device()`).
  - `[recording]` `min_seconds` (`0.5`), `max_seconds` (`60.0`).
  - `[notifications]` `enabled` (`true`).
- Precedencia por valor: **CLI > estado guardado (solo el dispositivo) > archivo > defectos**. Un argumento de CLI solo cuenta si el usuario lo escribió.
- Archivo de emergencia `speechflow.emergency.toml` en la raíz del repo: cuando no se encuentra ningún archivo, o el encontrado no se puede leer o no es válido, se registra un `WARNING` con la causa y la ruta, se crea el archivo con todos los valores por defecto (sin sobrescribirlo si ya existe) y la ejecución continúa con los defectos del código. El archivo inválido del usuario no se toca.
- Persistencia del micrófono elegido con `--switch-key`: archivo de estado `.speechflow-state.toml` en la raíz del repo, con el **nombre** del dispositivo. Lo escribe `PushToTalk.switch_device()` tras un cambio efectivo y se lee al arrancar.
- Aplicar `[recording]` a `PushToTalk` (hoy usa las constantes `MIN_SECONDS` y `MAX_SECONDS`) y `[notifications]` a `notifier.py`.
- Línea `INFO` de arranque con el origen de la configuración.
- Añadir `speechflow.toml`, `speechflow.emergency.toml` y `.speechflow-state.toml` al `.gitignore`; versionar `speechflow.example.toml` con todas las claves comentadas.
- Actualizar `README.md` y el docstring de `push_to_talk.py`.

**Fuera de alcance (para futuras specs):**

- Fusionar varios archivos o capas de configuración.
- Recarga en caliente del archivo, o escribir en él desde el script (el script solo escribe el archivo de emergencia y el de estado).
- Configuración para `capture_mic.py` y `benchmark_stt.py`, y para `--list-devices`.
- Notificaciones por tipo, o configuración del formato del log o del banner.
- Variables de entorno (`SPEECHFLOW_*`), otros formatos (YAML, JSON) y subcomando `--init-config`.
- Cambiar de modelo, idioma o teclas en caliente.
- Versionar o migrar el esquema del archivo.
- Rutas por plataforma distintas de Linux/XDG.
- Persistir otra cosa que el dispositivo de entrada.

## Modelo de datos

Interfaz pública nueva:

```python
# src/speechflow/config.py
CONFIG_FILENAME = "speechflow.toml"
USER_CONFIG_PATH = Path("~/.config/speechflow/config.toml")   # se expande con expanduser()
EMERGENCY_FILENAME = "speechflow.emergency.toml"
STATE_FILENAME = ".speechflow-state.toml"

@dataclass(frozen=True)
class Config:
    model: str = DEFAULT_MODEL
    language: str = DEFAULT_LANGUAGE
    key: str = "ctrl_r"
    switch_key: str = "f8"
    device: int | str | None = None
    min_seconds: float = 0.5
    max_seconds: float = 60.0
    notifications: bool = True

class ConfigError(Exception): ...                              # archivo ilegible o inválido; el mensaje dice qué clave y por qué

def find_config(explicit: Path | None) -> Path | None: ...     # orden de búsqueda; None si no hay ninguno
def load_config(path: Path) -> Config: ...                     # lanza ConfigError
def write_emergency(directory: Path) -> Path: ...              # crea EMERGENCY_FILENAME con los defectos si no existe
def load_state_device() -> str | None: ...                     # nombre guardado, o None (ausente o ilegible)
def save_state_device(name: str) -> None: ...                  # escribe STATE_FILENAME
```

```toml
# speechflow.toml — todas las claves son opcionales
[model]
name = "medium"
language = "es"

[keys]
record = "ctrl_r"
switch = "f8"

[audio]
device = "Realtek"          # índice (entero) o parte del nombre

[recording]
min_seconds = 0.5
max_seconds = 60.0

[notifications]
enabled = true
```

```toml
# .speechflow-state.toml — lo escribe el script, no se edita a mano
device = "Realtek Audio USB: Audio (hw:3,0)"
```

Convenciones:

- Validación estricta: una clave desconocida, un tipo incorrecto, `min_seconds <= 0`, `max_seconds <= min_seconds` o una sección que no es una tabla lanzan `ConfigError`. Las teclas se siguen validando con `parse_key()` al arrancar, con los mensajes de la SPEC 08 (`Error con --key: ...`, `Error con --switch-key: ...`).
- `Config.device` viene del archivo; el valor efectivo se resuelve con la precedencia `--device` > nombre de `.speechflow-state.toml` > `[audio] device` > `default_device()`.
- Si el nombre guardado en el estado no resuelve a ningún dispositivo de entrada (micrófono desconectado), se registra un `WARNING` y se pasa al siguiente nivel de la precedencia; no es un error fatal. Un `--device` o un `[audio] device` inexistentes siguen siendo `ERROR` y código 1, como hoy.
- Un `.speechflow-state.toml` ilegible se ignora con `WARNING`; no genera archivo de emergencia.
- `--config RUTA` que no existe es `ERROR` y código 1. `--config RUTA` que existe pero es inválido sigue el camino de emergencia.
- La ruta `speechflow.toml` y los archivos de emergencia y de estado se calculan a partir de la raíz del repo (`Path(__file__).resolve().parents[2]`), no del directorio de trabajo.
- El archivo de emergencia es una plantilla con los defectos; el script no lo lee en búsquedas posteriores. El usuario lo copia o renombra a `speechflow.toml`.
- Mensajes de consola:
  - `INFO` `Configuración: {ruta}` o `Configuración: valores por defecto`.
  - `WARNING` `Configuración inválida en {ruta}: {motivo}. Se usan los valores por defecto; plantilla en {ruta emergencia}.`
  - `WARNING` `No se encontró speechflow.toml ni {ruta XDG}. Se usan los valores por defecto; plantilla en {ruta emergencia}.`
  - `ERROR` `No existe el archivo de configuración {ruta}.` (solo con `--config`).
  - `WARNING` `El dispositivo guardado {nombre!r} no está disponible; se usa {siguiente nivel}.`
  - `INFO` `Entrada de audio guardada en .speechflow-state.toml.` no se registra; el cambio ya se informa con `Entrada de audio cambiada: ...`.
- `notifier.py` expone `set_enabled(enabled: bool)`; con `False`, `notify()` no hace nada. El aviso de falta de `notify-send` no se emite con las notificaciones desactivadas.

## Plan de implementación

1. Crear `src/speechflow/config.py` con `Config`, `ConfigError`, `find_config()`, `load_config()` y la validación estricta. Verificar: con un TOML de prueba en el directorio temporal, `load_config()` devuelve los valores del archivo y los defectos para lo omitido; una clave desconocida, `max_seconds = 0.1` y `device = true` lanzan `ConfigError` con la clave en el mensaje.
2. Añadir `write_emergency()`, `load_state_device()` y `save_state_device()`. Verificar: `write_emergency()` crea el archivo y una segunda llamada no lo modifica; `save_state_device("x")` seguido de `load_state_device()` devuelve `"x"`; un estado con TOML roto devuelve `None` sin lanzar excepción.
3. Añadir `set_enabled()` a `src/speechflow/notifier.py`. Verificar: con `set_enabled(False)`, `notify("a", "b")` no ejecuta `notify-send`; por defecto sigue notificando.
4. En `scripts/push_to_talk.py`, añadir `--config`, cargar la configuración tras `setup_logging()` y aplicar la precedencia a `--model`, `--language`, `--key`, `--switch-key` y `--device` (los argumentos pasan a tener defecto `None` para saber si se escribieron; el texto de ayuda sigue mostrando el defecto). Registrar la línea `Configuración: ...` y las advertencias y el archivo de emergencia. Verificar: sin ningún archivo, el arranque imprime el `WARNING` y crea `speechflow.emergency.toml`, y el comportamiento es el de antes; con un `speechflow.toml` que fija `[keys] record = "f9"`, el banner muestra `'f9'`; con `--key ctrl_r` sigue ganando la CLI.
5. Pasar `min_seconds`, `max_seconds` a `PushToTalk` en lugar de las constantes, y llamar a `set_enabled()` con `[notifications] enabled`. Verificar: con `max_seconds = 3` la grabación se corta a los 3 s; con `enabled = false` no aparece ninguna notificación en un ciclo completo.
6. Persistir el dispositivo: llamar a `save_state_device()` desde `switch_device()` tras un cambio efectivo y leer `load_state_device()` al arrancar con la precedencia indicada. Verificar: tras un cambio con la tecla, reiniciar usa ese micrófono; `--device 6` sigue mandando; con el micrófono guardado desconectado aparece el `WARNING` y el script arranca con el siguiente nivel.
7. Crear `speechflow.example.toml`, actualizar `.gitignore`, `README.md` (sección de configuración, opción `--config`, precedencia, archivo de emergencia y de estado) y el docstring del script, y marcar en `TODO.md` los ítems de archivo de configuración, persistencia del dispositivo y opciones de notificaciones. Verificar: el ejemplo del README coincide con la salida real, y `git status` no muestra los tres archivos ignorados tras generarlos.

## Criterios de aceptación

- [ ] `src/speechflow/config.py` expone `Config`, `ConfigError`, `find_config()`, `load_config()`, `write_emergency()`, `load_state_device()` y `save_state_device()`.
- [ ] `push_to_talk.py --help` muestra `--config`.
- [ ] Sin ningún archivo de configuración, el arranque registra el `WARNING` indicado, crea `speechflow.emergency.toml` con los valores por defecto y funciona como antes de esta spec.
- [ ] Con `speechflow.toml` en la raíz del repo, se usan sus valores y se registra `Configuración: {ruta}`.
- [ ] Sin `speechflow.toml` pero con `~/.config/speechflow/config.toml`, se usa el segundo.
- [ ] Con ambos, `speechflow.toml` gana y el otro se ignora por completo.
- [ ] `--config RUTA` gana sobre ambos; `--config` con una ruta inexistente termina con `ERROR` y código 1.
- [ ] Un argumento de CLI gana sobre el mismo valor del archivo.
- [ ] Un archivo con una clave desconocida, un tipo incorrecto o `max_seconds <= min_seconds` registra `WARNING` con la causa, crea el archivo de emergencia, no modifica el archivo inválido y arranca con los defectos.
- [ ] Si `speechflow.emergency.toml` ya existe, no se sobrescribe.
- [ ] Un `[keys] record` o `switch` inválido o repetido termina con código 1 y los mensajes `ERROR` de la SPEC 08.
- [ ] `[recording] max_seconds` y `min_seconds` sustituyen a las constantes en el comportamiento de la grabación.
- [ ] Con `[notifications] enabled = false` ningún evento (carga, cambio de entrada, error) envía notificación y no se emite el aviso de falta de `notify-send`.
- [ ] Un cambio efectivo de dispositivo escribe `.speechflow-state.toml` con el nombre del dispositivo; un cambio sin efecto (único dispositivo) o rechazado no lo escribe.
- [ ] Al reiniciar, se usa el dispositivo guardado; `--device` lo sustituye y `[audio] device` queda por debajo de él.
- [ ] Un dispositivo guardado que ya no existe registra `WARNING` y el arranque continúa con el siguiente nivel de precedencia.
- [ ] `--list-devices` no lee ni crea ningún archivo de configuración.
- [ ] `capture_mic.py` y `benchmark_stt.py` producen la misma salida que antes.
- [ ] `speechflow.toml`, `speechflow.emergency.toml` y `.speechflow-state.toml` están en `.gitignore`; `speechflow.example.toml` está versionado.
- [ ] `README.md` documenta la búsqueda, la precedencia, las claves y los archivos de emergencia y de estado.

## Decisiones

- **Sí:** TOML con `tomllib`, por elección del usuario entre las opciones del formato. Es la stdlib de Python 3.12, admite comentarios y no añade dependencias; YAML habría exigido PyYAML.
- **No:** YAML y JSON. YAML añade una dependencia; JSON no admite comentarios.
- **Sí:** `speechflow.toml` en la raíz del repo como ubicación por defecto y `~/.config/speechflow/config.toml` como alternativa, por elección del usuario (proyecto de pruebas). Es fácil de encontrar y editar mientras el proyecto no está empaquetado.
- **Sí:** `--config RUTA` por delante de ambas ubicaciones. Permite probar archivos sin tocar los de uso diario; un `--config` inexistente es error porque lo pidió el usuario explícitamente.
- **No:** fusionar los dos archivos. Complica saber de dónde viene cada valor.
- **Sí:** CLI > archivo > defectos, por elección del usuario. Un argumento puntual manda sobre la configuración guardada.
- **Sí:** ruta del repo calculada desde `__file__`, no desde el directorio de trabajo. El script se lanza desde cualquier carpeta y debe encontrar siempre el mismo archivo.
- **Sí:** opciones de `push_to_talk.py`, constantes de grabación y notificaciones, por elección del usuario. Cubre todo lo que hoy se fija por CLI o por constante.
- **Sí:** un único interruptor `[notifications] enabled`. Cubre lo pedido sin ampliar `notifier.py` ni `push_to_talk.py` con configuración por tipo.
- **No:** notificaciones por tipo. Más claves y más código para un caso que nadie ha pedido.
- **Sí:** archivo de emergencia con los valores por defecto, por elección del usuario, cuando falta el archivo o es inválido. El `WARNING` nombra la causa y la plantilla; la ejecución no se bloquea por un typo.
- **Sí:** el archivo inválido del usuario no se toca y el de emergencia no se sobrescribe. Ninguna ejecución destruye ediciones manuales.
- **No:** abortar con `ERROR` ante un archivo inválido (la opción coherente con `--key`). El usuario eligió tolerancia con aviso y plantilla; las teclas y el dispositivo, ya con valor combinado, siguen validándose con `ERROR`.
- **Sí:** validación estricta de claves desconocidas. Con la tolerancia de arriba, es lo que impide que un typo (`modle`) se ignore sin aviso.
- **Sí:** persistir el micrófono en un archivo de estado aparte, por nombre, por elección del usuario. `tomllib` no escribe TOML; un archivo con una sola clave generada por el script no pone en riesgo los comentarios de la configuración del usuario. Los índices cambian entre arranques (SPEC 08), el nombre no.
- **No:** reescribir la clave `device` de `speechflow.toml`, ni añadir `tomli_w`. Pierde comentarios o añade una dependencia.
- **Sí:** el dispositivo guardado que ya no existe degrada con `WARNING` al siguiente nivel. Un micrófono USB desenchufado no debe impedir arrancar; `--device` y `[audio] device` siguen siendo errores porque son una orden explícita.
- **Sí:** el estado guardado queda por debajo de `--device` y por encima de `[audio] device`. El último micrófono elegido a mano gana a la configuración estática; la CLI gana a todo.
- **Sí:** esta spec amplía la regla de notificaciones de las SPEC 06 y 08 con un interruptor global; los eventos notificados no cambian.
- **Sí:** esta spec cubre persistencia del dispositivo y opciones de notificaciones, ítems del `TODO.md`. Se tachan al terminar.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Un archivo roto pasa casi inadvertido porque el script arranca igualmente con los defectos | `WARNING` por stderr con la causa, la ruta y la plantilla, y la línea `Configuración: valores por defecto`; el archivo de emergencia lo deja en disco. |
| El usuario edita `speechflow.emergency.toml` esperando que se use | El `WARNING` y el README indican que es solo una plantilla y que debe copiarse a `speechflow.toml`. |
| Con argumentos de CLI con defecto `None` se pierde el texto de ayuda con el defecto | `help=` se escribe a mano con el defecto actual de `Config`. |
| El nombre guardado coincide con varios dispositivos (substring) | Se usa la misma resolución por nombre que `--device` (primera coincidencia con entradas); si no hay ninguna, se degrada con `WARNING`. |
| Dos instancias del script escriben el archivo de estado a la vez | Se escribe en un archivo temporal y se renombra (`os.replace`); la última escritura gana, sin archivo a medias. |
| Un `speechflow.toml` personal acaba en git | Está en `.gitignore`; solo se versiona `speechflow.example.toml`. |
| `~` no se expande o no hay `HOME` | Se usa `Path.expanduser()`; si falla, se trata como "no existe" y se sigue con los demás niveles. |

## Lo que **no** está en esta spec

- Fusión de archivos, recarga en caliente y escritura de la configuración del usuario por el script.
- Configuración de `capture_mic.py`, `benchmark_stt.py` y `--list-devices`.
- Notificaciones por tipo, formato del log y del banner.
- Variables de entorno, YAML, JSON y `--init-config`.
- Cambio en caliente de modelo, idioma o teclas.
- Versionado o migración del esquema.
- Persistir algo distinto del dispositivo de entrada.

Cada uno, si se aborda, va en su propia spec.
