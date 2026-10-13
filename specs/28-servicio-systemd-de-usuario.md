# SPEC 28 — Servicio `systemd` de usuario

> **Estado:** Aprobado
> **Depende de:** SPEC 14, SPEC 15, SPEC 17, SPEC 22
> **Fecha:** 2026-10-13
> **Objetivo:** Añadir el subcomando `speechflow service install|uninstall|status` que registra `speechflow` como servicio de `systemd --user`, arrancado con la sesión gráfica, reiniciado si falla y con su salida en `journalctl --user`.

## Por qué existe esta spec

Hoy `speechflow` se lanza a mano desde una terminal con el entorno conda activado. Para que la futura GUI o bandeja sea un cliente (elemento 9 de `TODO.md`), el proceso tiene que vivir por su cuenta: arrancar al iniciar sesión, reiniciarse si cae y no depender de una terminal abierta. La SPEC 15 ya dejó el cierre limpio ante `SIGTERM` (lo que `systemctl stop` envía) y la SPEC 22 el fallback a CPU, que evita que el servicio muera al arrancar sin GPU. Falta la unidad de `systemd` y una forma fiable de instalarla.

El proceso ya es en la práctica un daemon (no tiene interfaz y se controla con teclas y señales). Esta spec **no** cambia su arquitectura interna ni añade canal de control; eso es el elemento 10 y es la dependencia real de la GUI.

## Alcance

**Dentro:**

- Módulo nuevo `src/speechflow/service.py` con:
  - `render_unit(python: str, prefix: str) -> str`: devuelve el texto de la unidad (ver Modelo de datos). Lanza `ValueError` si `python` o `prefix` contienen espacios, tabuladores, saltos de línea o `%` (caracteres con significado en una unidad).
  - `unit_path() -> Path`: `$XDG_CONFIG_HOME/systemd/user/speechflow.service` (por defecto `~/.config/systemd/user/speechflow.service`), derivado de `config_dir().parent`. `RuntimeError` sin `HOME`, igual que `config.py`.
  - `install()`: escribe la unidad con `sys.executable` y `sys.prefix` del intérprete que ejecuta el comando, y ejecuta `systemctl --user daemon-reload` y `systemctl --user enable --now speechflow.service`.
  - `uninstall()`: ejecuta `systemctl --user disable --now speechflow.service`, borra el archivo de la unidad y ejecuta `daemon-reload`.
  - `status()`: ejecuta `systemctl --user status speechflow.service --no-pager` y devuelve su código de salida.
  - `main(argv: list[str]) -> int`: analiza `install`, `uninstall` y `status`, y devuelve el código de salida.
- Subcomando en `src/speechflow/app.py`: si `sys.argv[1:2] == ["service"]`, `main()` delega en `service.main(sys.argv[2:])` y termina con su código, **antes** de construir el `ArgumentParser` actual. Las opciones existentes (`--device`, `--model`, `--config`...) no cambian. El `epilog` de la ayuda menciona `speechflow service --help`.
- Comportamiento de `install`:
  - Idempotente: si la unidad existe, la reescribe y vuelve a ejecutar `daemon-reload` y `enable --now`. **No** reinicia un servicio ya activo; el mensaje final indica `systemctl --user restart speechflow` para aplicar una unidad cambiada.
  - El servicio usa el Python del entorno conda desde el que se ejecutó `install`, por lo que el entorno no necesita estar activado en tiempo de ejecución.
  - Termina con código 1 y un mensaje claro si falta `systemctl`, si `systemctl` falla (se muestra su salida de error) o si no hay `HOME`.
- Comportamiento de `uninstall`: si la unidad no existe, informa `El servicio no está instalado.` y termina con código 0.
- `systemctl` se invoca siempre como lista de argumentos con `subprocess.run`, sin shell.
- Salida de los subcomandos por el logger del paquete a consola (`setup_logging`), sin archivo de log.
- Tests nuevos en `tests/test_service.py` y actualizados en `tests/test_app_helpers.py` (o el archivo donde viva la prueba de `main()`), con `subprocess.run` doblado.
- Documentación: `README.md` (sección **Servicio de usuario**: instalar, ver estado, logs con `journalctl`, desinstalar, requisito de sesión gráfica, no ejecutar dos instancias) y `TODO.md` (marcar el elemento 9 y la línea "Daemon, arranque automático y `systemd`").

**Fuera de alcance (para futuras specs):**

- Canal de control (socket Unix o D-Bus), consulta de estado y cualquier IPC (elemento 10 de `TODO.md`).
- GUI y bandeja del sistema.
- Arranque en el encendido sin sesión gráfica (`loginctl enable-linger`): el micrófono, X11 y las notificaciones exigen sesión.
- Sesiones que no activan `graphical-session.target` (gestores de ventanas simples): el usuario usa GNOME.
- Pasar opciones de la CLI (`--config`, `--device`...) al servicio; se configura con el TOML de la SPEC 10.
- Comandos `start`, `stop`, `restart` y `logs` propios; se usa `systemctl --user` y `journalctl --user` directamente.
- Detectar o impedir una segunda instancia ejecutándose a mano.
- Unidades de sistema (`/etc/systemd/system`) y otras distribuciones.
- Cambios en `audio.py`, `config.py`, `transcriber.py`, `inserter.py`, `log.py`, `notifier.py`, `history.py`, `punctuation.py`, `replacements.py` y `scripts/`.

## Modelo de datos

Esta spec no introduce estructuras de datos persistentes ni claves de configuración. Añade un archivo de unidad generado:

```ini
# ~/.config/systemd/user/speechflow.service
[Unit]
Description=SpeechFlow, dictado por voz push-to-talk
PartOf=graphical-session.target
After=graphical-session.target
StartLimitIntervalSec=60
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/home/code925/miniconda3/envs/speechflow/bin/python -m speechflow
Environment=LD_LIBRARY_PATH=/home/code925/miniconda3/envs/speechflow/lib
Restart=on-failure
RestartSec=3
TimeoutStopSec=40

[Install]
WantedBy=graphical-session.target
```

```python
# src/speechflow/service.py
UNIT_NAME = "speechflow.service"

def render_unit(python: str, prefix: str) -> str: ...   # ValueError con espacios o '%'
def unit_path() -> Path: ...
def install() -> int: ...
def uninstall() -> int: ...
def status() -> int: ...
def main(argv: list[str]) -> int: ...
```

Convenciones:

- `ExecStart` usa `python -m speechflow` (no el comando `speechflow`) porque el entorno conda no está activado y no hay garantía de que el comando esté en el `PATH` del servicio.
- `LD_LIBRARY_PATH` apunta a `<sys.prefix>/lib` para que `ctranslate2` encuentre cuBLAS y cuDNN del entorno sin activarlo; sin ellas el modelo caería a CPU por la SPEC 22.
- `TimeoutStopSec=40` supera el `SHUTDOWN_TIMEOUT` de 30 s de la SPEC 15, para que `systemd` no mate el proceso mientras espera una transcripción en curso.
- `Restart=on-failure` no reinicia tras una salida con código 0 (`SIGTERM`, `SIGHUP`, `SIGINT` de la SPEC 15), por lo que `systemctl stop` y el cierre de sesión paran el servicio de verdad; sí reinicia ante una muerte por `SIGKILL` o un `sys.exit(1)` de arranque (falta `xdotool`, tecla inválida...).
- `StartLimitBurst=5` en 60 s evita un bucle de reinicios infinito si el arranque falla siempre.
- `DISPLAY`, `XAUTHORITY` y `DBUS_SESSION_BUS_ADDRESS` ya están en el entorno de `systemd --user` en GNOME; la unidad no los define.
- La salida estándar del proceso llega a `journalctl --user -u speechflow`; el log rotativo de la SPEC 17 sigue escribiéndose igual.
- `import speechflow.service` no ejecuta `systemctl` ni escribe nada.

## Plan de implementación

1. Crear `service.py` con `UNIT_NAME`, `render_unit` y `unit_path`. Tests en `tests/test_service.py`: el texto contiene `ExecStart=<python> -m speechflow`, `LD_LIBRARY_PATH=<prefix>/lib`, `Restart=on-failure`, `WantedBy=graphical-session.target`; rutas con espacio o `%` lanzan `ValueError`; `unit_path` respeta `XDG_CONFIG_HOME` y su valor por defecto. Verificar: `pytest tests/test_service.py` pasa.
2. Añadir `install`, `uninstall`, `status` y `main(argv)` con `subprocess.run` y los códigos de salida. Tests con `subprocess.run` doblado y `XDG_CONFIG_HOME` en un directorio temporal: `install` escribe el archivo y llama a `daemon-reload` y `enable --now` en ese orden; es idempotente; falla con código 1 si falta `systemctl` o este devuelve error; `uninstall` desactiva, borra y recarga, y con unidad ausente devuelve 0 sin llamar a `systemctl`; `status` devuelve el código de `systemctl`; argumento desconocido o ausente imprime la ayuda y devuelve 2. Verificar: `pytest` pasa.
3. Conectar el subcomando en `app.main()` y el `epilog` de la ayuda. Test: `main()` con `sys.argv = ["speechflow", "service", "status"]` llama a `service.main(["status"])` y sale con su código, sin construir la configuración ni cargar el modelo. Verificar: `speechflow --help` menciona el subcomando y `speechflow --list-devices` sigue funcionando.
4. Prueba manual con el sistema real (ver criterios): instalar, comprobar que arranca, dictar, matar con `SIGKILL` y ver el reinicio, parar con `systemctl --user stop`, reiniciar la sesión y desinstalar. Verificar: cada caso coincide con los criterios de aceptación.
5. Documentar en `README.md` y marcar el elemento 9 y la línea de "Ejecución en segundo plano" en `TODO.md`. Verificar: el README describe los comandos tal como se ejecutan en el paso 4.

## Criterios de aceptación

- [ ] `render_unit("/ruta/python", "/ruta")` contiene `ExecStart=/ruta/python -m speechflow` y `Environment=LD_LIBRARY_PATH=/ruta/lib`.
- [ ] `render_unit` lanza `ValueError` si `python` o `prefix` contienen un espacio o `%`.
- [ ] `unit_path()` es `~/.config/systemd/user/speechflow.service` y respeta `XDG_CONFIG_HOME`.
- [ ] `speechflow service install` escribe la unidad y ejecuta `daemon-reload` y `enable --now`, en ese orden, con código de salida 0.
- [ ] Ejecutar `install` dos veces seguidas no falla y deja un único archivo de unidad.
- [ ] `install` termina con código 1 y un mensaje si `systemctl` no existe o devuelve error.
- [ ] `speechflow service uninstall` desactiva y para el servicio, borra la unidad y ejecuta `daemon-reload`; con la unidad ausente informa y devuelve 0.
- [ ] `speechflow service status` devuelve el código de salida de `systemctl --user status`.
- [ ] `speechflow service` sin subcomando o con uno desconocido devuelve el código 2 y muestra la ayuda.
- [ ] `speechflow --list-devices` y el resto de opciones existentes se comportan igual que en la SPEC 27.
- [ ] `import speechflow.service` no ejecuta `systemctl` ni crea archivos.
- [ ] Prueba manual: tras `speechflow service install`, `systemctl --user is-active speechflow` imprime `active` y `journalctl --user -u speechflow` muestra el arranque con el dispositivo de cómputo `cuda`.
- [ ] Prueba manual: con el servicio activo, un dictado con la tecla configurada inserta el texto y aparecen las notificaciones de escritorio.
- [ ] Prueba manual: `systemctl --user kill -s KILL speechflow` hace que el servicio vuelva a `active` en unos segundos; `systemctl --user stop speechflow` lo deja `inactive` y no se reinicia.
- [ ] Prueba manual: `systemctl --user stop speechflow` durante una transcripción espera a que termine, inserta el texto y libera el modelo sin que `systemd` envíe `SIGKILL`.
- [ ] Prueba manual: tras cerrar sesión y volver a entrar, el servicio arranca solo.
- [ ] `speechflow service uninstall` deja `systemctl --user status speechflow` sin la unidad cargada (`could not be found`).
- [ ] `pytest` pasa con código 0, sin GPU, sin modelo real y sin ejecutar `systemctl`.
- [ ] `git diff main -- scripts src/speechflow/audio.py src/speechflow/config.py src/speechflow/transcriber.py src/speechflow/inserter.py src/speechflow/log.py src/speechflow/notifier.py src/speechflow/history.py` está vacío.
- [ ] `README.md` documenta `speechflow service install|uninstall|status`, `journalctl --user -u speechflow` y que no debe haber dos instancias a la vez.

## Decisiones

- **Sí:** solo servicio, sin IPC, por elección del usuario. El canal de control es el elemento 10 y es la dependencia real de la GUI; mezclarlos alarga la spec y dificulta verificarla.
- **No:** un socket de estado de solo lectura en esta spec. Habría que decidir protocolo y formato antes de saber qué necesita la GUI.
- **Sí:** subcomando `speechflow service install|uninstall|status`, por elección del usuario. Genera la unidad con la ruta real del Python y evita editar a mano la ruta del entorno conda.
- **No:** unidad fija en el repositorio con pasos manuales. Obliga a ajustar rutas a mano y se desactualiza.
- **No:** script `scripts/install-service.sh`. Queda fuera de la CLI y repite la lógica de rutas.
- **Sí:** `WantedBy=graphical-session.target`, por elección del usuario (GNOME). En GNOME ese target se activa al iniciar sesión y el entorno de `systemd --user` ya trae `DISPLAY` y `XAUTHORITY`, que necesitan `pynput`, `xdotool` y `xclip`.
- **No:** `default.target`. Arrancaría antes de que existan `DISPLAY` y el micrófono de la sesión.
- **Sí:** `PartOf=graphical-session.target`. Al cerrar la sesión gráfica el servicio se para limpiamente por `SIGTERM`.
- **Sí:** `Restart=on-failure` y salida a `journald`, por elección del usuario. No reinicia tras la salida limpia (código 0) de la SPEC 15, por lo que `systemctl stop` funciona, y sí tras un fallo.
- **No:** `Restart=always`. Pelearía con `systemctl stop` en las salidas con código 0 y con la propia señal de cierre de sesión.
- **No:** sin reinicio automático. Un fallo puntual dejaría el dictado muerto sin que el usuario se enterara.
- **Sí:** `StartLimitBurst=5` en 60 s con `RestartSec=3`. Decisión del diseño: un arranque que falla siempre (falta `xdotool`, configuración inválida) no debe reiniciarse sin fin.
- **Sí:** `ExecStart=<sys.executable> -m speechflow`. Decisión del diseño: el entorno conda no está activado bajo `systemd` y esa ruta es la única garantizada.
- **Sí:** `LD_LIBRARY_PATH=<sys.prefix>/lib`. Decisión del diseño: cuBLAS y cuDNN viven en el entorno conda y sin activarlo `ctranslate2` puede no encontrarlas, con lo que el servicio funcionaría en CPU sin avisar. Se verifica en la prueba manual.
- **Sí:** `TimeoutStopSec=40`. Decisión del diseño: debe superar el `SHUTDOWN_TIMEOUT` de 30 s de la SPEC 15.
- **Sí:** `install` idempotente y sin reiniciar. Decisión del diseño: reiniciar interrumpiría un dictado en curso; el mensaje indica cómo aplicar los cambios.
- **Sí:** rechazar rutas con espacios o `%` en vez de escaparlas. Decisión del diseño: el escape de `systemd` es fácil de hacer mal y la ruta del entorno conda no los lleva en la práctica.
- **No:** `loginctl enable-linger`. El servicio necesita sesión gráfica; con linger arrancaría sin X11 y fallaría.
- **No:** pasar opciones de la CLI a la unidad. La configuración vive en el TOML de la SPEC 10.
- **No:** subcomandos `start`/`stop`/`logs`. `systemctl --user` y `journalctl --user` ya los cubren.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El servicio no encuentra cuBLAS/cuDNN y corre en CPU sin que se note | `LD_LIBRARY_PATH` en la unidad; la prueba manual comprueba que el log muestra `cuda`. |
| Dos instancias (una a mano, otra del servicio) capturan la misma tecla y dictan dos veces | El README lo advierte y pide parar una antes de usar la otra; detectarlo queda fuera de alcance. |
| Mover o borrar el entorno conda deja la unidad apuntando a una ruta inexistente | `ExecStart` falla, `StartLimitBurst` frena el bucle y el README indica volver a ejecutar `speechflow service install`. |
| `DISPLAY`/`XAUTHORITY` ausentes del entorno de `systemd --user` en otra sesión | Con GNOME ya están; el README documenta `systemctl --user import-environment DISPLAY XAUTHORITY` como remedio. |
| Cambiar la unidad con el servicio activo no surte efecto hasta reiniciar | El mensaje de `install` indica `systemctl --user restart speechflow`. |
| Un cambio de `systemd` en el formato de la unidad | La unidad usa solo directivas básicas y estables; el test comprueba su contenido. |

## Lo que **no** está en esta spec

- Canal de control, socket Unix o D-Bus, y consulta de estado.
- GUI y bandeja del sistema.
- Arranque sin sesión gráfica (`linger`).
- Soporte de gestores de ventanas sin `graphical-session.target`.
- Opciones de la CLI pasadas al servicio.
- Subcomandos `start`, `stop`, `restart` y `logs`.
- Detección de instancias duplicadas.
- Unidades de sistema y otras distribuciones.
- Cambios en `audio.py`, `config.py`, `transcriber.py`, `inserter.py`, `log.py`, `notifier.py`, `history.py`, `punctuation.py`, `replacements.py` y `scripts/`.

Cada uno, si se aborda, va en su propia spec.
