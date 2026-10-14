# SPEC 29 — Canal de control por socket Unix

> **Estado:** Implementado
> **Depende de:** SPEC 08, SPEC 10, SPEC 12, SPEC 15, SPEC 19, SPEC 22, SPEC 28
> **Fecha:** 2026-10-13
> **Objetivo:** Añadir un socket Unix de control (JSON de una línea) y el subcomando `speechflow ctl` para consultar el estado, pausar y reanudar el dictado (la pausa libera el modelo), cambiar el idioma y cambiar o listar los dispositivos de entrada de un proceso `speechflow` en ejecución.

## Por qué existe esta spec

Hoy el proceso solo se controla con teclas globales y señales de cierre. Con el servicio `systemd` de la SPEC 28 corre sin terminal, así que no hay forma de saber en qué estado está, de pausarlo ni de elegir un micrófono concreto sin estar delante del teclado. La futura GUI o bandeja (elemento 9 de `TODO.md`) será un cliente de este canal, por eso el protocolo se define ahora, con JSON y con respuestas estructuradas, y se prueba desde la terminal con `speechflow ctl`.

Esta spec **no** cambia la arquitectura interna del proceso: el canal es un hilo más que llama a métodos de `PushToTalk`, con las mismas reglas que las teclas (los cambios solo en `IDLE`, bajo el `_lock` existente).

## Alcance

**Dentro:**

- Módulo nuevo `src/speechflow/control.py` con:
  - `socket_path() -> Path`: `$XDG_RUNTIME_DIR/speechflow/control.sock`. `RuntimeError` si `XDG_RUNTIME_DIR` no está definida (no hay alternativa en `/tmp`: la ruta debe ser privada del usuario).
  - `ControlServer(handler, path)`: crea el directorio (`0700`) y el socket (`0600`), acepta conexiones en un hilo daemon, lee una línea JSON, llama a `handler(request) -> dict` y escribe una línea JSON de respuesta. `start()`, `close()` (cierra el socket y borra el archivo).
  - `send_request(request: dict, timeout: float = 10.0) -> dict`: cliente. Lanza `ControlUnavailable` si no existe el socket o rechaza la conexión.
  - `main(argv: list[str]) -> int`: cuerpo de `speechflow ctl`.
- Protocolo (una petición por conexión; el servidor cierra tras responder):
  - Petición: `{"cmd": "<comando>", "value": <opcional>}\n`, máximo 4096 bytes; el servidor espera la línea como mucho 2 s.
  - Respuesta correcta: `{"ok": true, ...campos del comando}\n`. Error: `{"ok": false, "error": "<mensaje en español>"}\n`.
  - Comandos: `status`, `pause`, `resume`, `language` (`value`: `"es"`, `"en"` o `"auto"`), `device` (`value`: `"next"`, un índice entero o un nombre/subcadena) y `devices`.
  - Comando desconocido, JSON inválido o `value` ausente o inválido: `ok: false` con la causa; el canal nunca cierra el proceso ni lo deja bloqueado.
- Subcomando en `src/speechflow/app.py`: si `sys.argv[1:2] == ["ctl"]`, `main()` delega en `control.main(sys.argv[2:])` y termina con su código, **antes** de construir el `ArgumentParser` actual (mismo patrón que `service`). El `epilog` de la ayuda menciona `speechflow ctl --help`.
- `speechflow ctl status|pause|resume|language <es|en|auto>|device <next|índice|nombre>|devices [--json]`:
  - Sin `--json`, imprime un resumen legible (`status` en varias líneas, el resto una línea); con `--json`, la respuesta cruda del servidor.
  - Código de salida: 0 si `ok`, 1 si el servidor respondió `ok: false`, 2 por uso incorrecto (comando desconocido o falta el argumento), 3 si no hay proceso escuchando (`SpeechFlow no está en ejecución: no hay socket en <ruta>.`).
  - No importa `sounddevice`, `pynput` ni `faster_whisper`: `ctl` debe arrancar en milisegundos.
- Servidor en `main()` de `app.py`: se crea tras construir `PushToTalk` y antes de `listener.start()`; se cierra en la secuencia de salida de la SPEC 15, antes de `begin_shutdown()`. Siempre activo, sin clave en el TOML.
  - Sin `XDG_RUNTIME_DIR`, con un error al crear el socket o con otra instancia ya escuchando en él: `WARNING` con la causa y el proceso sigue sin canal. Nunca se borra el socket de una instancia viva.
  - Socket huérfano (el archivo existe pero nadie acepta conexiones): se borra y se vuelve a crear.
- Métodos nuevos en `PushToTalk` (`app.py`), usados por el canal y con las mismas reglas que las teclas:
  - `pause()`: solo en `IDLE` y sin recarga del modelo en curso; marca `paused`, cancela el temporizador de inactividad y libera el modelo (`transcriber.close()`, igual que `_unload_model`). Idempotente.
  - `resume()`: desmarca `paused` y lanza la recarga en segundo plano con el hilo `_load_model` existente; responde sin esperar. Idempotente.
  - `control_status() -> dict`, `control_set_language(value)`, `control_set_device(value)` y `control_devices()`, que reutilizan la lógica de `switch_language`, `toggle_auto` y `switch_device` pero devuelven el resultado o lanzan `ControlError(mensaje)` en vez de solo registrar.
  - En pausa, la tecla de dictado no graba: `WARNING` `Dictado en pausa; reanúdalo con: speechflow ctl resume.` Las teclas de idioma y de cambio de entrada siguen funcionando.
- Tests nuevos en `tests/test_control.py` y actualizados en `tests/test_push_to_talk.py` y en el archivo que pruebe `main()`, con dobles (sin GPU, micrófono ni modelo real).
- Documentación: `README.md` (sección **Canal de control**: comandos, protocolo JSON con ejemplos, `nc -U`/`socat`, códigos de salida, uso con el servicio de la SPEC 28), `speechflow.example.toml` no cambia, y `TODO.md` (marcar el elemento 10 y anotar en "Audio y captura" que el cambio de dispositivo por otros medios queda cubierto por el socket).

**Fuera de alcance (para futuras specs):**

- GUI y bandeja del sistema (cliente del canal).
- D-Bus y señales (`SIGUSR1/2`) como transporte alternativo.
- Autenticación más allá de los permisos del sistema de archivos (`0700`/`0600`).
- Eventos y suscripciones (`subscribe`, notificar cambios al cliente); solo petición y respuesta.
- Pausa diferida (aceptar `pause` en `RECORDING`/`TRANSCRIBING` y aplicarla al volver a `IDLE`); hoy se rechaza.
- Comandos extra: `start`/`stop` de grabación remotos, `reload-config`, `quit`, ver el historial, cambiar modelo o `compute_device`.
- Persistir la pausa entre arranques: el proceso siempre arranca activo.
- Elegir otra ruta del socket por CLI o TOML.
- Sustituir por el socket las teclas actuales de idioma y dispositivo; siguen igual.
- Cambios en `audio.py`, `config.py`, `transcriber.py`, `inserter.py`, `log.py`, `notifier.py`, `history.py`, `punctuation.py`, `replacements.py`, `service.py` y `scripts/`.

## Modelo de datos

Esta spec no introduce estructuras persistentes ni claves de configuración. Añade el protocolo y el estado de ejecución `paused`.

```python
# src/speechflow/control.py
def socket_path() -> Path: ...                       # $XDG_RUNTIME_DIR/speechflow/control.sock
class ControlUnavailable(Exception): ...             # sin socket o conexión rechazada
class ControlServer:
    def __init__(self, handler: Callable[[dict], dict], path: Path) -> None: ...
    def start(self) -> None: ...                     # OSError si no puede crearse
    def close(self) -> None: ...
def send_request(request: dict, timeout: float = 10.0) -> dict: ...
def main(argv: list[str]) -> int: ...

# src/speechflow/app.py
class ControlError(Exception): ...                   # el mensaje va a "error" en la respuesta
# PushToTalk.paused: bool = False                    # no se persiste
```

Respuestas (campos además de `ok`):

```jsonc
// status
{"ok": true, "pid": 1234, "state": "idle",            // idle | recording | transcribing
 "paused": false,
 "model": {"name": "large-v3-turbo", "status": "loaded", "compute_device": "cuda"},  // loaded | loading | unloaded
 "language": "es",                                   // es | en | auto
 "mode": "hold",                                     // hold | toggle
 "device": {"index": 7, "name": "Blue Yeti", "connected": true}}
// pause / resume
{"ok": true, "paused": true}
// language
{"ok": true, "language": "en"}
// device
{"ok": true, "device": {"index": 3, "name": "USB Audio"}}
// devices
{"ok": true, "devices": [{"index": 3, "name": "USB Audio", "selected": false}]}
// error
{"ok": false, "error": "ocupado: grabando"}
```

Convenciones:

- Cada línea JSON termina en `\n` y se codifica en UTF-8. Los campos desconocidos de una petición se ignoran; los clientes deben ignorar los campos desconocidos de una respuesta.
- `model.status` es `unloaded` con `transcriber is None` y sin hilo de carga vivo, `loading` con el hilo `_loader` vivo y `loaded` en el resto.
- Mensajes de error fijos: `ocupado: grabando`, `ocupado: transcribiendo`, `ocupado: cargando el modelo`, `cierre en curso`, `idioma no válido: <valor>`, `dispositivo no válido: <causa>`, `comando desconocido: <cmd>`, `petición inválida: <causa>`.
- `device` con índice o nombre valida con `sd.query_devices(valor, "input")` antes de aplicarlo y, si es correcto, hace lo mismo que `switch_device`: registra, notifica, guarda en `state.toml` y actualiza el micrófono vigilado. Un nombre ambiguo es `dispositivo no válido`.
- `pause` y `resume` registran por log (`INFO`) y notifican (`Dictado en pausa` / `Dictado reanudado`).
- `pause` con el modelo ya descargado por inactividad solo marca `paused`. `resume` tras un fallo de recarga deja el error en el log; la siguiente pulsación de la tecla reintenta, como en la SPEC 12.
- El canal no registra el contenido de las peticiones por encima de `DEBUG`.
- Un cliente lento o que no envía línea no bloquea a los demás: el servidor atiende una conexión cada vez con un plazo de 2 s para leer.
- El socket se crea en el directorio `speechflow` de `$XDG_RUNTIME_DIR` (limitado a 108 bytes de ruta por el sistema operativo; si la ruta es más larga, es el mismo `WARNING` de «no se pudo crear»).

## Plan de implementación

1. Crear `control.py` con `socket_path`, `ControlUnavailable`, `ControlServer` y `send_request`, con un `handler` doble. Tests en `tests/test_control.py` con `XDG_RUNTIME_DIR` en un directorio temporal corto: ida y vuelta de una petición, permisos `0700`/`0600`, `close()` borra el archivo, JSON inválido y línea de más de 4096 bytes dan `ok: false`, un cliente que no envía nada no bloquea al siguiente, socket huérfano se reemplaza, socket de una instancia viva no se borra y `start()` falla, `send_request` sin socket lanza `ControlUnavailable`. Verificar: `pytest tests/test_control.py` pasa.
2. Añadir a `control.py` `main(argv)` (`ctl`) con `status|pause|resume|language|device|devices` y `--json`, los códigos 0/1/2/3 y los resúmenes legibles, con `send_request` doblado. Verificar: `pytest tests/test_control.py` pasa; `python -c "import speechflow.control"` no importa `sounddevice`, `pynput` ni `faster_whisper`.
3. En `app.py`, añadir `ControlError`, `PushToTalk.paused`, `pause()`, `resume()` y que `on_press` ignore la tecla de dictado en pausa. Tests en `tests/test_push_to_talk.py` con modelo doble: `pause` en `IDLE` libera el modelo y cancela el temporizador de inactividad; en `RECORDING`/`TRANSCRIBING` o con la recarga en curso lanza `ControlError` con el mensaje fijo; es idempotente; `resume` lanza la recarga y no espera; en pausa la tecla no graba y avisa; las teclas de idioma y dispositivo siguen activas. Verificar: `pytest` pasa.
4. Añadir `control_status`, `control_set_language`, `control_set_device`, `control_devices` y el despachador `handle_control(request) -> dict` que convierte `ControlError` y errores de validación en `ok: false`. Tests: cada comando con sus campos, idioma inválido, índice inexistente, nombre ambiguo, rechazo fuera de `IDLE`, `device next` equivale a la tecla, el cambio guarda en `state.toml` y el idioma `auto` conserva el último fijo. Verificar: `pytest` pasa.
5. Conectar en `main()`: subcomando `ctl` antes del `ArgumentParser`, `epilog`, creación del servidor tras `PushToTalk` (con los `WARNING` de degradación) y cierre en la secuencia de salida antes de `begin_shutdown()`. Tests: `main()` con `sys.argv = ["speechflow", "ctl", "status"]` llama a `control.main(["status"])` sin cargar configuración ni modelo; el arranque sin `XDG_RUNTIME_DIR` registra el `WARNING` y sigue. Verificar: `speechflow --help` menciona `ctl` y `speechflow --list-devices` sigue funcionando.
6. Prueba manual con el sistema real (ver criterios), a mano y como servicio de la SPEC 28. Verificar: cada caso coincide con los criterios de aceptación.
7. Documentar en `README.md` y marcar el elemento 10 y la línea de dispositivo en `TODO.md`. Verificar: los ejemplos del README son los ejecutados en el paso 6.

## Criterios de aceptación

- [ ] `socket_path()` es `$XDG_RUNTIME_DIR/speechflow/control.sock`; sin `XDG_RUNTIME_DIR` lanza `RuntimeError`.
- [ ] Con el proceso en marcha, el directorio del socket tiene permisos `0700` y el socket `0600`.
- [ ] `speechflow ctl status` imprime estado, pausa, modelo (nombre, estado y dispositivo de cómputo), idioma, modo y micrófono, y sale con 0; con `--json` imprime el JSON del servidor.
- [ ] `speechflow ctl pause` en reposo libera el modelo (`ctl status` muestra `unloaded` y `paused: true`) y la tecla de dictado no graba, sino que avisa con `Dictado en pausa`.
- [ ] `speechflow ctl resume` responde de inmediato, `ctl status` pasa por `loading` a `loaded` y la tecla de dictado vuelve a funcionar.
- [ ] `pause` y `resume` repetidos no fallan y devuelven `ok: true`.
- [ ] `pause`, `language` y `device` durante `RECORDING` o `TRANSCRIBING` devuelven `ok: false` con `ocupado: grabando` / `ocupado: transcribiendo` y salida 1, y no alteran la grabación.
- [ ] `speechflow ctl language en` fija el idioma, notifica y lo guarda en `state.toml`; `language auto` activa la detección automática; `language fr` devuelve `idioma no válido: fr`.
- [ ] `speechflow ctl devices` lista los dispositivos de entrada con `index`, `name` y `selected`; `ctl device next` equivale a pulsar la tecla de cambio; `ctl device <índice>` y `ctl device <nombre>` eligen ese micrófono, lo guardan en `state.toml` y lo notifican; un índice inexistente o un nombre ambiguo devuelve `dispositivo no válido`.
- [ ] En pausa, las teclas de idioma y de cambio de entrada siguen funcionando.
- [ ] Una petición con JSON inválido, comando desconocido o de más de 4096 bytes devuelve `ok: false` y el proceso sigue funcionando.
- [ ] Un cliente que se conecta y no envía nada no impide que el siguiente sea atendido tras 2 s.
- [ ] `speechflow ctl` sin proceso en marcha sale con código 3 y el mensaje `SpeechFlow no está en ejecución`; sin subcomando o con uno desconocido sale con 2 y muestra la ayuda.
- [ ] Sin `XDG_RUNTIME_DIR`, o con otra instancia escuchando, el arranque registra un `WARNING` y el dictado funciona sin canal; el socket de la otra instancia sigue intacto.
- [ ] Un socket huérfano de un arranque anterior que murió con `SIGKILL` se reemplaza al arrancar.
- [ ] Al salir (`Ctrl+C`, `SIGTERM`, `systemctl --user stop speechflow`) el archivo del socket se borra.
- [ ] `import speechflow.control` no crea archivos ni importa `sounddevice`, `pynput` ni `faster_whisper`.
- [ ] `speechflow --list-devices` y el resto de opciones existentes se comportan igual que en la SPEC 28.
- [ ] Prueba manual: con el servicio de la SPEC 28 activo, `ctl status`, `ctl pause`, `ctl resume`, `ctl language en` y `ctl device next` funcionan desde otra terminal y aparecen en `journalctl --user -u speechflow`.
- [ ] Prueba manual: tras `ctl pause`, `nvidia-smi` muestra la VRAM liberada; tras `ctl resume`, vuelve a usarse.
- [ ] `pytest` pasa con código 0, sin GPU, sin micrófono, sin modelo real y sin tocar el socket real del usuario.
- [ ] `git diff main -- scripts src/speechflow/audio.py src/speechflow/config.py src/speechflow/transcriber.py src/speechflow/inserter.py src/speechflow/log.py src/speechflow/notifier.py src/speechflow/history.py src/speechflow/service.py` está vacío.
- [ ] `README.md` documenta los comandos de `speechflow ctl`, el protocolo JSON con ejemplos, los códigos de salida y la ruta del socket.

## Decisiones

- **Sí:** socket Unix, por elección del usuario. Permite petición y respuesta, argumentos y consultar el estado, que las señales no cubren, y es la dependencia real de la GUI.
- **No:** señales (`SIGUSR1/2`). Sin argumentos ni respuesta; no sirven para `status` ni para elegir idioma o dispositivo.
- **No:** D-Bus. Añade dependencia y complejidad; se evalúa cuando exista la GUI.
- **Sí:** subcomando `speechflow ctl`, por elección del usuario. Mismo patrón que `service`, sin dependencias nuevas y probable con dobles.
- **No:** solo el socket sin cliente (`nc -U`). Incómodo y sin forma sencilla de probarlo.
- **No:** ejecutable aparte `speechflowctl`. Duplica el entry point y el empaquetado.
- **Sí:** JSON de una línea y una petición por conexión, por elección del usuario. `status` y `devices` devuelven datos compuestos, el formato es extensible y la GUI lo consume sin analizador propio; la incomodidad de teclearlo a mano la cubre `ctl`.
- **No:** texto plano. Obliga a inventar un formato de respuesta y reglas de entrecomillado para nombres con espacios.
- **Sí:** canal siempre activo y sin clave en el TOML, por elección del usuario. Menos superficie de configuración; si no se puede crear, solo un `WARNING`.
- **No:** `[control] enabled`. Más claves y validación sin que nadie lo pida.
- **Sí:** `pause` libera el modelo, por elección del usuario. Libera VRAM mientras no se dicta, a costa de unos segundos al reanudar.
- **No:** pausar solo ignorando la tecla. Más rápido de reanudar, pero no libera la GPU.
- **Sí:** `resume` recarga inmediatamente y en segundo plano, por elección del usuario. El modelo está listo al primer dictado y `status` muestra `loading`; reutiliza el hilo `_load_model` de la SPEC 12.
- **No:** recarga perezosa al pulsar la tecla. El estado seguiría `unloaded` tras `resume`, lo que confunde a un cliente.
- **Sí:** rechazar `pause`, `language` y `device` fuera de `IDLE`, por elección del usuario. Coherente con las teclas actuales y sin estado intermedio `pausing`.
- **No:** pausa diferida. Más cómoda, pero añade un estado y casos de prueba.
- **Sí:** comandos `language <es|en|auto>`, `device <next|índice|nombre>` y `devices`, por elección del usuario. Fijar explícitamente evita alternar a ciegas y listar permite que un cliente elija.
- **Sí:** las teclas de idioma y de cambio de entrada siguen activas en pausa. Decisión del diseño: no necesitan el modelo y la pausa solo afecta al dictado.
- **Sí:** `XDG_RUNTIME_DIR` y sin alternativa en `/tmp`. Decisión del diseño: es el directorio privado de la sesión (`0700`) y un socket en `/tmp` sería accesible o suplantable por otros usuarios.
- **Sí:** no borrar nunca el socket de una instancia viva; solo el huérfano. Decisión del diseño: evita que una segunda instancia (a mano) deje sin canal a la del servicio.
- **Sí:** un hilo que atiende una conexión cada vez, con plazo de lectura de 2 s. Decisión del diseño: los comandos son raros y breves, y un servidor concurrente no justifica su complejidad.
- **Sí:** la pausa no se persiste. Decisión del diseño: arrancar pausado tras reiniciar sería confuso; el idioma y el dispositivo sí se guardan, como ya hacen las teclas.
- **Sí:** `control.py` sin importar `sounddevice`, `pynput` ni `faster_whisper`. Decisión del diseño: `ctl` debe responder al instante y funcionar aunque no haya GPU ni entorno de audio.
- **Sí:** métodos `control_*` que lanzan `ControlError` en vez de reutilizar `switch_*` tal cual. Decisión del diseño: las teclas solo registran en el log, pero el cliente necesita saber si el cambio se aplicó.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Un comando llega mientras el hilo del listener tiene el `_lock` (p. ej. `refresh_devices`) | El canal usa el mismo `_lock` que las teclas; el cliente espera hasta 10 s y el servidor atiende de uno en uno, así que no hay interbloqueo. |
| Se pausa en medio de una recarga y el modelo se libera a medias | `pause` se rechaza con `ocupado: cargando el modelo` si el hilo `_loader` está vivo. |
| Segunda instancia a mano compite con el servicio por el socket | No se borra el socket vivo; la segunda registra el `WARNING` y sigue sin canal (la SPEC 28 ya advierte de no ejecutar dos). |
| Socket huérfano tras `SIGKILL` impide arrancar | Al arrancar se comprueba si alguien acepta conexiones; si no, se borra y se recrea. |
| Ruta del socket mayor de 108 bytes | `bind` falla, `WARNING` y el proceso sigue sin canal; en la práctica `/run/user/<uid>/speechflow/control.sock` es corta. |
| Otro proceso del mismo usuario manda órdenes | Aceptado: es el modelo de confianza de una sesión de usuario; los permisos `0700`/`0600` bloquean a los demás usuarios. |
| `resume` falla al recargar (GPU ocupada, VRAM insuficiente) | Se deja el error en el log y se notifica; `status` muestra `unloaded` y la siguiente pulsación reintenta, igual que en la SPEC 12. |
| Un cambio futuro del protocolo rompe a la GUI | Campos desconocidos ignorados por ambos lados y respuestas aditivas; el protocolo queda documentado en el README. |

## Lo que **no** está en esta spec

- GUI y bandeja del sistema.
- D-Bus, señales de control y cualquier otro transporte.
- Autenticación más allá de permisos de archivo.
- Eventos, suscripciones y notificaciones al cliente.
- Pausa diferida y persistencia de la pausa.
- Comandos de grabación remota, recarga de configuración, salida, historial o cambio de modelo.
- Ruta del socket configurable.
- Cambios en `audio.py`, `config.py`, `transcriber.py`, `inserter.py`, `log.py`, `notifier.py`, `history.py`, `punctuation.py`, `replacements.py`, `service.py` y `scripts/`.

Cada uno, si se aborda, va en su propia spec.
