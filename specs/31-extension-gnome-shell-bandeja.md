# SPEC 31 — Extensión de GNOME Shell para el panel

> **Estado:** Implementado
> **Depende de:** SPEC 28, SPEC 29, SPEC 30
> **Fecha:** 2026-10-20
> **Objetivo:** Añadir una extensión de GNOME Shell 48 (JavaScript) que muestre en el panel un icono con el estado de `speechflow` y un menú para pausar, cambiar el idioma y el micrófono, y abrir la configuración, más el subcomando `speechflow ext install|uninstall|status` que la instala.

## Por qué existe esta spec

El servicio `systemd` (SPEC 28) corre sin ventana y el canal de control (SPEC 29) solo se maneja desde una terminal. En GNOME 48 no hay bandeja clásica sin una extensión de terceros (AppIndicator), que no está instalada. Se eligió una extensión propia de GNOME Shell porque habla con el socket Unix directamente desde GJS, sin PyGObject, sin conda y sin depender de AppIndicator. A cambio, solo sirve para GNOME y hay que revisarla con cada versión mayor del Shell.

La extensión es un cliente más del protocolo: se suscribe con `subscribe` (SPEC 30) para el estado y envía los comandos de la SPEC 29 por conexiones aparte. No cambia el servidor.

## Alcance

**Dentro:**

- Extensión en `src/speechflow/shell_extension/`, con UUID `speechflow@local`:
  - `metadata.json`: `uuid`, `name`, `description`, `shell-version: ["48"]`, `version: 1`.
  - `extension.js`: módulo ESM de GNOME 48 (`Extension` de `resource:///org/gnome/shell/extensions/extension.js`) con un `PanelMenu.Button` en la barra superior.
  - `stylesheet.css`: clases de estado del icono.
- Comunicación con el socket `GLib.get_user_runtime_dir()/speechflow/control.sock` con `Gio.SocketClient`, siempre asíncrona (nunca bloquea el Shell):
  - Una conexión permanente con `{"cmd": "subscribe"}` que lee líneas con `Gio.DataInputStream.read_line_async`.
  - Una conexión nueva por cada comando (`pause`, `resume`, `language`, `device`, `devices`), con plazo de 10 s.
  - Sin conexión (sin socket, rechazo o EOF), reintento cada 3 s con `GLib.timeout_add_seconds`. Conectado no hay temporizadores de sondeo.
- Icono y estado (el primero que se cumpla, por prioridad):

  | Prioridad | Condición | Icono | Clase CSS | Texto de estado |
  | --- | --- | --- | --- | --- |
  | 1 | Sin conexión con el proceso | `audio-input-microphone-symbolic` | `speechflow-offline` | `SpeechFlow no está en ejecución` |
  | 2 | `paused` | `microphone-disabled-symbolic` | `speechflow-paused` | `En pausa` |
  | 3 | `state == "recording"` | `audio-input-microphone-symbolic` | `speechflow-recording` | `Grabando` |
  | 4 | `state == "transcribing"` | `audio-input-microphone-symbolic` | `speechflow-transcribing` | `Transcribiendo` |
  | 5 | `model.status == "loading"` | `audio-input-microphone-symbolic` | `speechflow-loading` | `Cargando el modelo…` |
  | 6 | `device.connected == false` | `audio-input-microphone-symbolic` | `speechflow-warning` | `Micrófono desconectado` |
  | 7 | resto | `audio-input-microphone-symbolic` | (ninguna) | `Listo` |

- Menú:
  - Línea de estado (no pulsable) con el texto de la tabla, y una línea de detalle `<modelo> · <compute_device> · <model.status>`.
  - `Pausar dictado` / `Reanudar dictado` según `paused` (`pause` / `resume`).
  - Submenú `Idioma` con `Español`, `Inglés` y `Automático` (`language` con `es`, `en`, `auto`) y el actual marcado.
  - Submenú `Micrófono` que pide `devices` al abrirse y lista `[índice] nombre` con el seleccionado marcado; al pulsar envía `device` con el índice.
  - Separador, `Abrir configuración` (`config.toml` con la aplicación por defecto, mediante `Gio.AppInfo.launch_default_for_uri`; desactivado si el archivo no existe) y `Abrir carpeta del historial` (la carpeta de `history.jsonl`, es decir `$XDG_STATE_HOME/speechflow` o `~/.local/state/speechflow`).
  - Sin conexión: solo `Iniciar servicio` (ejecuta `systemctl --user start speechflow` con `Gio.Subprocess`) y los dos elementos de abrir. Idioma, micrófono y pausa se ocultan.
  - Los comandos con `ok: false` se muestran con `Main.notify("SpeechFlow", <error>)`. Con la suscripción activa, el icono y el menú se actualizan solos por el evento siguiente, sin refrescar a mano.
- Subcomando `speechflow ext install|uninstall|status` en `src/speechflow/ext.py`, despachado en `main()` de `app.py` antes del `ArgumentParser`, igual que `service` y `ctl`:
  - `install`: copia los archivos de `speechflow/shell_extension/` a `$XDG_DATA_HOME/gnome-shell/extensions/speechflow@local/` (`~/.local/share/...` por defecto), reemplazando la versión anterior, e imprime los pasos siguientes: reiniciar el Shell (`Alt+F2`, `r`, `Enter` en X11) y `gnome-extensions enable speechflow@local`. Idempotente. No activa la extensión.
  - `uninstall`: ejecuta `gnome-extensions disable speechflow@local` si existe el comando y borra el directorio instalado. Idempotente.
  - `status`: indica si está instalada, si coincide con la del paquete y, si existe `gnome-extensions`, el resultado de `gnome-extensions info speechflow@local`.
  - Códigos de salida: 0 correcto, 1 error (por ejemplo, sin `HOME`), 2 uso incorrecto.
  - No importa `sounddevice`, `pynput` ni `faster_whisper`.
- Empaquetado en `pyproject.toml`: los archivos de `shell_extension/` se incluyen como datos del paquete (`[tool.setuptools.package-data]`) y `ext.py` los lee con `importlib.resources`.
- Tests en `tests/test_ext.py` con `XDG_DATA_HOME` temporal y `gnome-extensions` doblado.
- Documentación: `README.md` (sección **Icono en GNOME Shell**: requisitos, instalación, activación, tabla de estados, desinstalación y que solo es para GNOME 48) y `TODO.md` (marcar la bandeja del sistema y el menú gráfico de dispositivo).

**Fuera de alcance (para futuras specs):**

- Quick Settings (interruptor en el menú del sistema).
- Otros escritorios (KDE, XFCE, Cinnamon) y otro cliente basado en StatusNotifierItem.
- Otras versiones del Shell distintas de la 48.
- Publicación en extensions.gnome.org y empaquetado `.zip` con `gnome-extensions pack`.
- Ventana de preferencias (`prefs.js`), traducciones y atajos de teclado de la extensión.
- Ver, buscar o copiar entradas del historial desde el menú.
- Iconos propios, animaciones y sonidos.
- Comandos extra del servidor (`reload-config`, `quit`, cambio de modelo).
- Cambios en `control.py`, `audio.py`, `config.py`, `transcriber.py`, `inserter.py`, `log.py`, `notifier.py`, `history.py`, `punctuation.py`, `replacements.py`, `service.py` y `scripts/`.

## Modelo de datos

Esta spec no introduce estructuras persistentes ni claves de configuración. Estado de ejecución de la extensión (en memoria):

```js
// src/speechflow/shell_extension/extension.js
// Último "status" recibido por la suscripción, o null sin conexión.
let status = null;          // {state, paused, model, language, mode, device, pid} según la SPEC 29
// Recursos que disable() debe liberar:
//   _indicator (PanelMenu.Button), _cancellable (Gio.Cancellable),
//   _retrySource (id de GLib.timeout_add_seconds) y la conexión de la suscripción.
```

```python
# src/speechflow/ext.py
UUID = "speechflow@local"
def extension_dir() -> Path: ...    # $XDG_DATA_HOME/gnome-shell/extensions/speechflow@local
def install() -> int: ...
def uninstall() -> int: ...
def status() -> int: ...
def main(argv: list[str]) -> int: ...
```

Convenciones:

- Los textos del menú están en español.
- Toda E/S de la extensión es asíncrona y cancelable. `disable()` cancela el `Gio.Cancellable`, quita el temporizador de reintento, cierra la conexión y destruye el indicador.
- La extensión ignora los campos desconocidos del `status`.

## Plan de implementación

1. Crear `ext.py` (`install`, `uninstall`, `status`, `main`), el esqueleto de `shell_extension/` (`metadata.json`, un `extension.js` que solo muestra el icono de micrófono con un menú vacío, `stylesheet.css` vacío), el despacho en `main()` de `app.py` y el `package-data`. Tests en `tests/test_ext.py`: `install` copia los archivos e imprime los pasos, reinstalar reemplaza, `uninstall` borra y es idempotente, `status` detecta que difiere. Verificar: `pytest` pasa; `speechflow ext install`, reiniciar el Shell y `gnome-extensions enable speechflow@local` muestran el icono en el panel.
2. En `extension.js`, conectar con el socket, enviar `subscribe` y leer líneas; guardar `status` y reintentar cada 3 s sin conexión. Mostrar solo el icono y las clases de estado de la tabla. Verificar: con el servicio parado el icono sale atenuado y con `systemctl --user start speechflow` pasa a normal sin recargar nada.
3. Añadir la línea de estado y de detalle y el elemento `Pausar dictado`/`Reanudar dictado`, con el envío de comandos por conexiones aparte y las notificaciones de error. Verificar: pulsar el elemento pausa y reanuda; `ctl status` coincide y el icono cambia.
4. Añadir el submenú `Idioma` con el actual marcado. Verificar: elegir `Inglés` cambia `ctl status` a `en`; `ctl language auto` se refleja en el menú.
5. Añadir el submenú `Micrófono`, rellenado con `devices` al abrirse. Verificar: lista los mismos dispositivos que `ctl devices` y elegir uno lo aplica.
6. Añadir el estado sin conexión con `Iniciar servicio`, y `Abrir configuración` y `Abrir carpeta del historial`. Verificar: con el servicio parado, `Iniciar servicio` lo arranca; los dos elementos abren el archivo y la carpeta.
7. Revisar `disable()` y los reintentos: deshabilitar y habilitar la extensión varias veces no deja temporizadores, conexiones ni errores en `journalctl`. Documentar en `README.md` y `TODO.md`. Verificar: los pasos del README son los ejecutados.

## Criterios de aceptación

- [ ] `speechflow ext install` copia `metadata.json`, `extension.js` y `stylesheet.css` a `~/.local/share/gnome-shell/extensions/speechflow@local/`, imprime cómo reiniciar el Shell y activar la extensión, y sale con 0; repetirlo reemplaza los archivos sin error.
- [ ] `speechflow ext uninstall` borra el directorio y sale con 0 aunque no estuviera instalado.
- [ ] `speechflow ext status` indica si está instalada y si coincide con la del paquete.
- [ ] Tras reiniciar el Shell y `gnome-extensions enable speechflow@local`, `gnome-extensions info speechflow@local` muestra el estado `ACTIVE` (no `ERROR`).
- [ ] `journalctl --user -b _COMM=gnome-shell | grep speechflow` no muestra errores de la extensión durante el uso normal.
- [ ] Con el servicio parado, el icono aparece atenuado con el texto `SpeechFlow no está en ejecución` y el menú ofrece `Iniciar servicio`.
- [ ] Al arrancar el servicio, el icono pasa al estado normal en menos de 4 s sin intervención.
- [ ] Mantener pulsada la tecla de dictado pone el icono en rojo (`Grabando`) y al soltarla pasa a `Transcribiendo` y después a `Listo`, sin recargar la extensión.
- [ ] `Pausar dictado` pone el icono de micrófono deshabilitado y el texto `En pausa`; `Reanudar dictado` muestra `Cargando el modelo…` hasta que el modelo está `loaded` y vuelve a `Listo`. Lo mismo ocurre con `speechflow ctl pause` y `ctl resume`.
- [ ] El submenú `Idioma` marca el idioma actual y refleja los cambios hechos con `ctl language`.
- [ ] El submenú `Micrófono` lista los dispositivos de `ctl devices`, marca el seleccionado y elegir uno lo aplica (`ctl status` lo confirma).
- [ ] Pausar, cambiar de idioma o de micrófono durante `RECORDING` o `TRANSCRIBING` muestra una notificación con el error `ocupado: ...` y no altera la grabación.
- [ ] Con el micrófono desconectado, el icono muestra `Micrófono desconectado`.
- [ ] `Abrir configuración` abre `~/.config/speechflow/config.toml` y `Abrir carpeta del historial` abre `~/.local/state/speechflow`.
- [ ] Deshabilitar y habilitar la extensión diez veces no deja conexiones al socket abiertas (`ss -xp | grep control.sock` no crece) ni errores en el registro del Shell.
- [ ] El Shell no se bloquea ni se ralentiza con el servicio parado, reiniciándose o con el socket sin responder.
- [ ] `import speechflow.ext` no crea archivos ni importa `sounddevice`, `pynput` ni `faster_whisper`.
- [ ] `pytest` pasa con código 0, sin GPU, sin micrófono, sin modelo real y sin tocar el directorio de extensiones del usuario.
- [ ] `git diff main -- scripts src/speechflow/control.py src/speechflow/audio.py src/speechflow/config.py src/speechflow/transcriber.py src/speechflow/inserter.py src/speechflow/log.py src/speechflow/notifier.py src/speechflow/history.py src/speechflow/service.py` está vacío.
- [ ] `README.md` documenta la instalación, la activación, los estados del icono y la desinstalación.

## Decisiones

- **Sí:** extensión de GNOME Shell en JS, por elección del usuario. Integración nativa, sin AppIndicator, PyGObject ni conda; a cambio, solo GNOME y revisión en cada versión mayor del Shell.
- **No:** proceso Python con StatusNotifierItem. Portable y más estable, pero exige la extensión AppIndicator y PyGObject. Puede ser una spec futura para otros escritorios.
- **Sí:** botón de panel con menú, por elección del usuario. Visible siempre y más simple que Quick Settings.
- **No:** Quick Settings. Más moderno, pero oculto tras un clic y con una API más compleja.
- **Sí:** suscripción a los cambios (SPEC 30) en vez de sondeo, por elección del usuario. El icono refleja el estado al instante y no hay temporizadores mientras hay conexión.
- **Sí:** menú con estado y pausa, idioma, micrófono y abrir configuración e historial, por elección del usuario.
- **Sí:** sin conexión, icono atenuado con `Iniciar servicio`, por elección del usuario. El usuario ve que algo falta y puede arrancarlo sin terminal.
- **Sí:** `speechflow ext install|uninstall|status`, por elección del usuario. Mismo patrón que `service`, con pruebas y sin pasos manuales.
- **Sí:** `Abrir configuración` abre el archivo y el historial se abre como carpeta, por elección del usuario. No depende de qué aplicación tenga GNOME asociada a `.toml` o `.jsonl`.
- **Sí:** UUID `speechflow@local`. Decisión del diseño: el formato exige `nombre@dominio` y no se publica en extensions.gnome.org.
- **Sí:** iconos simbólicos del tema (`audio-input-microphone-symbolic`, `microphone-disabled-symbolic`) y color por clase CSS. Decisión del diseño: sin recursos gráficos propios que mantener.
- **Sí:** `install` copia los archivos en vez de enlazarlos y no activa la extensión. Decisión del diseño: el Shell no descubre extensiones nuevas hasta reiniciarse, así que activarla antes falla; la copia funciona también con una instalación no editable.
- **Sí:** reintento de conexión cada 3 s solo sin conexión. Decisión del diseño: es la única forma de saber que el servicio arrancó, a un coste despreciable.
- **Sí:** E/S siempre asíncrona y cancelable. Decisión del diseño: el código de una extensión corre dentro del proceso del Shell y un bloqueo congela el escritorio.
- **Sí:** los errores del servidor se muestran con `Main.notify`. Decisión del diseño: el menú se cierra al pulsar y el usuario necesita saber por qué no se aplicó el cambio.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Una actualización de GNOME Shell rompe la extensión | `shell-version` limita a 48; fuera de esa versión el Shell la marca como incompatible en vez de cargarla. Cada versión nueva se revisa en su spec. |
| Un error de JS deja la extensión en `ERROR` o afecta al Shell | Toda E/S va en callbacks con `try`/`catch` y registro en el Shell; la extensión no toca nada fuera de su indicador. |
| `disable()` deja recursos vivos (conexión, temporizador, indicador) | Un único lugar libera todo (cancelable, `GLib.source_remove`, `destroy()`) y un criterio lo comprueba con `ss -xp`. |
| El Shell no ve la extensión recién instalada | `ext install` imprime los pasos exactos; en X11 basta `Alt+F2`, `r`, `Enter`. |
| `systemctl --user start speechflow` falla si la unidad no está instalada | Se muestra la salida de error con `Main.notify` y el README remite a `speechflow service install`. |
| El servidor tarda en responder y el Shell espera | Todas las llamadas son asíncronas con plazo de 10 s; el menú nunca se bloquea. |
| GNOME 50 elimina X11 y el proyecto sigue en X11 | Fuera de esta spec; la extensión solo habla con el socket, así que no depende de la sesión. |

## Lo que **no** está en esta spec

- Quick Settings y otros escritorios (KDE, XFCE, Cinnamon).
- Versiones del Shell distintas de la 48 y publicación en extensions.gnome.org.
- Preferencias, traducciones y atajos de teclado.
- Ver o buscar el historial desde el menú.
- Iconos propios, animaciones y sonidos.
- Cambios en el servidor (`control.py`), que pertenecen a la SPEC 30.

Cada uno, si se aborda, va en su propia spec.
