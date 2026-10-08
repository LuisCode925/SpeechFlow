# SPEC 14 — Empaquetado, comando `speechflow` y rutas XDG

> **Estado:** Implementado
> **Depende de:** SPEC 10, SPEC 13
> **Fecha:** 2026-10-07
> **Objetivo:** Hacer el proyecto instalable con `pyproject.toml`, arrancable con el comando `speechflow` y con `python -m speechflow`, y mover la configuración, el estado y la plantilla de emergencia de la raíz del repo a las rutas XDG del usuario.

## Por qué existe esta spec

Tras la SPEC 13 la lógica vive en `src/speechflow/app.py`, pero sigue sin poder arrancarse sin `scripts/push_to_talk.py` y su `sys.path.insert`. Además, `config.py` calcula `REPO_ROOT` desde `__file__` (`parents[2]`): un paquete instalado (`site-packages`) escribiría el estado y la plantilla de emergencia en un sitio incorrecto. Es el segundo paso de la Fase 2 (SPEC 13–16): los tests (15) y el cierre limpio (16) necesitan un paquete instalable y rutas que no dependan del repo. Sustituye las rutas de la SPEC 10 (`speechflow.toml`, `speechflow.emergency.toml` y `.speechflow-state.toml` en la raíz del repo).

## Alcance

**Dentro:**

- Crear `pyproject.toml` en la raíz: backend `setuptools`, layout `src/`, `requires-python = ">=3.12"`, versión tomada de `speechflow.__version__` y dependencias `faster-whisper`, `av<17`, `pynput`, `sounddevice` y `scipy`.
- Declarar el comando `speechflow` (`[project.scripts]` → `speechflow.app:main`).
- Crear `src/speechflow/__main__.py` para `python -m speechflow`, que llama a `main()`.
- Fijar `prog="speechflow"` en el `ArgumentParser` para que `--help` muestre el mismo nombre con el comando y con `python -m`.
- Mover las rutas de usuario a XDG:
  - Configuración: `$XDG_CONFIG_HOME/speechflow/config.toml` (defecto `~/.config/speechflow/config.toml`).
  - Plantilla de emergencia: `config.emergency.toml` en esa misma carpeta.
  - Estado: `$XDG_STATE_HOME/speechflow/state.toml` (defecto `~/.local/state/speechflow/state.toml`).
- Eliminar `REPO_ROOT`, el nivel `speechflow.toml` en la raíz del repo y los nombres `CONFIG_FILENAME`, `USER_CONFIG_PATH`, `EMERGENCY_FILENAME` y `STATE_FILENAME` actuales, sustituidos por funciones que calculan las rutas XDG.
- Crear las carpetas necesarias al escribir la plantilla de emergencia o el estado.
- Mantener `--config RUTA` como primer nivel de búsqueda.
- Eliminar `scripts/push_to_talk.py`.
- Quitar el `sys.path.insert` de `scripts/capture_mic.py`: pasa a requerir el paquete instalado.
- Actualizar `environment.yml` para instalar el paquete (`pip install -e .`) en lugar de listar las librerías pip.
- Actualizar `.gitignore` (quitar las tres entradas que ya no aplican y añadir `*.egg-info/`), `README.md` y `TODO.md`, y mover la mención de `speechflow.example.toml` a la nueva ubicación del archivo de usuario.

**Fuera de alcance (para futuras specs):**

- Publicar en PyPI, ruedas distribuidas o `pipx`.
- Migrar automáticamente los archivos existentes en la raíz del repo, o avisar de que existen.
- Rutas distintas de Linux/XDG (macOS, Windows).
- Cambiar el formato, las claves o la precedencia de la configuración (SPEC 10).
- Cambiar `benchmark_stt.py`, `audio.py`, `inserter.py`, `log.py`, `notifier.py` y `transcriber.py`.
- Tests (SPEC 15) y cierre ante `SIGTERM`/`SIGHUP` (SPEC 16).
- Servicio `systemd`, archivo de log y bandeja (Fase 3).

## Modelo de datos

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "speechflow"
dynamic = ["version"]
description = "Dictado por voz push-to-talk con faster-whisper"
requires-python = ">=3.12"
dependencies = [
    "faster-whisper",
    "av<17",
    "pynput",
    "sounddevice",
    "scipy",
]

[project.scripts]
speechflow = "speechflow.app:main"

[tool.setuptools.dynamic]
version = { attr = "speechflow.__version__" }

[tool.setuptools.packages.find]
where = ["src"]
```

```python
# src/speechflow/__main__.py
from speechflow.app import main

main()
```

```python
# src/speechflow/config.py — sustituye a REPO_ROOT y a las constantes de nombre de archivo
def config_dir() -> Path: ...                  # $XDG_CONFIG_HOME/speechflow, o ~/.config/speechflow
def state_dir() -> Path: ...                   # $XDG_STATE_HOME/speechflow, o ~/.local/state/speechflow
def user_config_path() -> Path: ...            # config_dir() / "config.toml"
def emergency_path() -> Path: ...              # config_dir() / "config.emergency.toml"
def state_path() -> Path: ...                  # state_dir() / "state.toml"

def find_config(explicit: Path | None) -> Path | None: ...   # --config, o user_config_path(); None si no hay
def write_emergency() -> Path: ...                           # sin argumento: escribe en emergency_path()
```

```toml
# environment.yml (sección pip)
  - pip:
      - -e .
```

Convenciones:

- Una variable `XDG_*` vacía o con ruta relativa se ignora y se usa el defecto, como indica la especificación XDG.
- Si no se puede resolver `HOME`, las funciones de ruta lanzan `RuntimeError`; `find_config()` ya lo trata como "no existe" y `write_emergency()` y `save_state_device()` propagan `OSError`/`RuntimeError`, que `app.py` registra como `WARNING` sin abortar, igual que hoy.
- `load_config()`, `load_state_device()`, `save_state_device()`, el formato de los archivos y los mensajes de la SPEC 10 no cambian, salvo las rutas que nombran.
- El mensaje sin archivo pasa a `No se encontró {user_config_path()}.`; la línea `Configuración: {ruta}` y el resto de mensajes conservan su texto.
- `--help` conserva el texto actual; solo cambia el defecto de `--config` (`{user_config_path()}`) y el nombre de programa (`speechflow`).
- `save_state_device()` conserva la escritura atómica (archivo temporal + `os.replace`) y crea `state_dir()` si no existe.
- El archivo de estado y la plantilla se escriben con los mismos permisos por defecto que hoy; no se fuerza ningún `chmod`.

## Plan de implementación

1. Añadir `pyproject.toml` y `src/speechflow/__main__.py`, y fijar `prog="speechflow"` en `app.py`. Verificar: `pip install -e .` en el entorno `speechflow` termina sin error; `speechflow --help` y `python -m speechflow --help` muestran el mismo texto y `scripts/push_to_talk.py --help` sigue funcionando (aún no se elimina).
2. Sustituir en `config.py` `REPO_ROOT` y las constantes de nombre por `config_dir()`, `state_dir()`, `user_config_path()`, `emergency_path()` y `state_path()`, y adaptar `find_config()`, `write_emergency()`, `load_state_device()` y `save_state_device()` (con creación de carpetas). Verificar: con `XDG_CONFIG_HOME` y `XDG_STATE_HOME` apuntando a una carpeta temporal, las funciones devuelven rutas dentro de ella; con ambas sin definir o vacías, devuelven las del `HOME`; una segunda llamada a `write_emergency()` no modifica el archivo.
3. Adaptar `app.py` a las nuevas funciones: `resolve_config()` (mensaje sin archivo, plantilla de emergencia), el aviso de `STATE_FILENAME` al guardar el dispositivo y el `help` de `--config`. Verificar: `grep -rn "REPO_ROOT\|CONFIG_FILENAME\|STATE_FILENAME\|EMERGENCY_FILENAME\|USER_CONFIG_PATH" src scripts` no devuelve nada.
4. Eliminar `scripts/push_to_talk.py` y quitar el `sys.path.insert` de `scripts/capture_mic.py`. Verificar: `python scripts/capture_mic.py --list-devices` funciona con el paquete instalado; `grep -rn "push_to_talk" scripts src README.md` solo encuentra referencias históricas a documentar.
5. Actualizar `environment.yml` (`- -e .`), `.gitignore` (quitar las tres entradas, añadir `*.egg-info/`), `README.md` (instalación, comando `speechflow`, `python -m speechflow`, nuevas rutas, `--config`, archivo de emergencia y de estado) y `TODO.md` (marcar SPEC 14 y "Empaquetado y `python -m speechflow`"). Verificar: crear un entorno limpio con `conda env create -f environment.yml` deja el comando `speechflow` disponible; el README no menciona rutas obsoletas.
6. Prueba manual completa con el modelo real y `XDG_CONFIG_HOME`/`XDG_STATE_HOME` apuntando a carpetas temporales: sin config (WARNING y plantilla creada), con `config.toml` válido e inválido, `--config` inexistente, un dictado, cambio de entrada con `f8` (estado escrito), reinicio con el micrófono guardado y `Ctrl+C`. Verificar: el log coincide con el ejemplo del README actualizado y no se crea ningún archivo en la raíz del repo.

## Criterios de aceptación

- [ ] `pyproject.toml` existe y `pip install -e .` en el entorno `speechflow` termina sin error.
- [ ] `speechflow --help` y `python -m speechflow --help` muestran el mismo texto, con `usage: speechflow`.
- [ ] `speechflow --list-devices` y `python -m speechflow --list-devices` listan los dispositivos y no leen ni crean ningún archivo de configuración.
- [ ] `scripts/push_to_talk.py` no existe y ningún archivo del repo lo ejecuta ni lo documenta como forma de arranque.
- [ ] `scripts/capture_mic.py` no contiene `sys.path.insert` y funciona con el paquete instalado.
- [ ] `scripts/benchmark_stt.py` no cambia y produce la misma salida que antes.
- [ ] `config.py` no contiene `REPO_ROOT`; las rutas salen de las funciones XDG y respetan `XDG_CONFIG_HOME` y `XDG_STATE_HOME` cuando son absolutas.
- [ ] Sin ningún archivo, el arranque registra el `WARNING` con la nueva ruta, crea `config.emergency.toml` en `config_dir()` (y la carpeta si falta) y arranca con los defectos.
- [ ] Con `config.toml` en `config_dir()` se usan sus valores y se registra `Configuración: {ruta}`; `--config RUTA` gana, y una ruta inexistente termina con `ERROR` y código 1.
- [ ] Un cambio efectivo de dispositivo escribe `state.toml` en `state_dir()`; al reiniciar se usa ese micrófono, con la precedencia de la SPEC 10.
- [ ] Un `speechflow.toml`, `speechflow.emergency.toml` o `.speechflow-state.toml` en la raíz del repo se ignora y no se modifica.
- [ ] Ejecutar `speechflow` desde cualquier directorio de trabajo usa los mismos archivos.
- [ ] `import speechflow.app` y `import speechflow.config` siguen sin efectos secundarios (no crean carpetas ni archivos).
- [ ] El arranque, el dictado, el cambio de entrada, la vigilancia del micrófono, la descarga por inactividad y la salida con `Ctrl+C` producen los mismos mensajes y notificaciones que antes, salvo las rutas.
- [ ] `environment.yml` instala el paquete en un entorno nuevo y `speechflow` queda en el `PATH` del entorno.
- [ ] `.gitignore` ignora `*.egg-info/` y ya no lista los tres archivos de la raíz; `git status` queda limpio tras instalar y ejecutar.
- [ ] `README.md` documenta la instalación, el comando, `python -m speechflow`, las rutas XDG y que los archivos antiguos de la raíz no se migran.

## Decisiones

- **Sí:** rutas XDG estándar (`~/.config/speechflow/`, `~/.local/state/speechflow/`), por elección del usuario. Separa configuración de estado, funciona con el paquete instalado y respeta `XDG_CONFIG_HOME` y `XDG_STATE_HOME`.
- **No:** conservar `speechflow.toml` en la raíz del repo como nivel de búsqueda. Dos ubicaciones obligan a saber dónde está la raíz del repo, que un paquete instalado no tiene.
- **No:** guardar todo en `~/.config/speechflow`. Mezclaría un archivo que el usuario edita con uno que escribe el script.
- **Sí:** no migrar los archivos antiguos, ni avisar de su existencia, por elección del usuario (proyecto de pruebas). El usuario los mueve a mano y el README documenta las nuevas rutas.
- **No:** migración automática. Más código y riesgo de pisar archivos en un proyecto con un único usuario.
- **Sí:** el nombre del archivo de usuario pasa a ser `config.toml` y la plantilla `config.emergency.toml`, junto a él. Evita repetir `speechflow` dentro de la carpeta `speechflow/` y deja la plantilla a la vista de quien edita la configuración.
- **Sí:** `setuptools` con layout `src/` y versión dinámica desde `speechflow.__version__`. Es lo que ya trae el entorno conda y evita una segunda fuente de versión.
- **Sí:** declarar las dependencias en `pyproject.toml` y que `environment.yml` ejecute `pip install -e .`, por elección del usuario. Una sola lista para pip; conda sigue aportando CUDA, cuDNN, PortAudio y las librerías ya resueltas (`sounddevice`, `scipy`).
- **Sí:** `faster-whisper` y `av<17` se declaran sin tope superior para `faster-whisper`; el tope de `av` conserva el que ya usa `environment.yml`.
- **No:** `pyproject.toml` mínimo sin dependencias. `pip` no podría validar el entorno.
- **Sí:** eliminar `scripts/push_to_talk.py`, por elección del usuario. Mantener dos formas de arrancar duplica la documentación; el comando y `python -m` lo sustituyen.
- **Sí:** quitar el `sys.path.insert` de `capture_mic.py`. Instalar el paquete es el requisito único; `benchmark_stt.py` no importa el paquete y no cambia.
- **Sí:** `prog="speechflow"` fijo. Con `python -m speechflow` argparse mostraría `__main__.py`.
- **Sí:** esta spec invalida las rutas de la SPEC 10; formato, claves, precedencia y mensajes se conservan.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Con el paquete instalado en modo editable, `pip` reconstruye `speechflow.egg-info/` y ensucia el árbol | `*.egg-info/` en `.gitignore`. |
| El entorno actual tiene `faster-whisper` y compañía instalados por `environment.yml` y `pip install -e .` los reinstala o cambia versiones | Las dependencias no llevan topes nuevos; `pip` respeta lo ya instalado que cumple. Verificar con `pip check` tras instalar. |
| `sounddevice` y `scipy` vienen de conda y pip los considera ausentes | Ambos están instalados en el entorno con metadatos de conda; `pip` los acepta como satisfechos. Si no, se quitan de `dependencies` y se documenta. |
| El usuario pierde su `speechflow.toml` y su micrófono guardado al actualizar sin darse cuenta | El README lo documenta en la sección de rutas; el arranque sin configuración muestra el `WARNING` con la nueva ruta. |
| `XDG_STATE_HOME` apunta a una carpeta sin permisos de escritura | `save_state_device()` falla con `OSError`; `app.py` ya lo registra como `WARNING` sin abortar. |
| `speechflow` en el `PATH` sin activar el entorno conda | El comando solo existe con el entorno activo; el README lo indica. |
| `python -m speechflow` ejecuta `main()` al importar `__main__` desde otra herramienta (tests, `pydoc`) | `__main__.py` solo se ejecuta como módulo principal; no se importa desde el código. |

## Lo que **no** está en esta spec

- Publicación en PyPI, `pipx` o ruedas distribuidas.
- Migración o aviso de los archivos antiguos de la raíz del repo.
- Rutas para otras plataformas distintas de Linux/XDG.
- Cambios en el formato, las claves o la precedencia de la configuración.
- Tests con `pytest`.
- Cierre ante `SIGTERM`/`SIGHUP` y espera a la transcripción en curso.
- Servicio `systemd`, archivo de log con rotación y bandeja del sistema.

Cada uno, si se aborda, va en su propia spec.
