# SPEC 30 — Suscripción a cambios de estado en el canal de control

> **Estado:** Aprobado
> **Depende de:** SPEC 29
> **Fecha:** 2026-10-20
> **Objetivo:** Añadir el comando `subscribe` al canal de control, que mantiene la conexión abierta y envía una línea JSON con el `status` completo al suscribirse y cada vez que cambia, más el subcomando `speechflow ctl watch` para verlo desde la terminal.

## Por qué existe esta spec

La bandeja de GNOME (SPEC 31) debe reflejar al instante si se está grabando, transcribiendo o en pausa. El canal de la SPEC 29 solo admite petición y respuesta, así que el cliente tendría que sondear `status` cada segundo. Se decidió añadir suscripciones en el servidor, y esta spec lo hace por separado de la extensión para poder verificarlo con `nc -U` y `speechflow ctl watch`, sin JavaScript.

El estado de `PushToTalk` cambia en unos quince puntos de `app.py` (`state`, `paused`, `transcriber`, `language`, `recorder.device`, `_device_missing`). En vez de añadir ganchos en cada uno, un hilo del servidor toma una muestra de `status` mientras haya suscriptores y envía solo lo que cambia. Con cero suscriptores no hay hilo ni coste. Esta spec **no** toca `app.py`.

## Alcance

**Dentro:**

- En `src/speechflow/control.py`:
  - Comando `subscribe` atendido por `ControlServer` (no por el `handler`): `{"cmd": "subscribe"}\n`. El servidor pide el estado con `handler({"cmd": "status"})`, responde con esa línea más `"event": "status"` y **no cierra la conexión**: la guarda como suscriptor y sigue atendiendo a los demás clientes.
  - Hilo publicador `control-publisher`: arranca con el primer suscriptor y termina cuando no queda ninguno. Cada `PUBLISH_INTERVAL` (0,25 s) llama a `handler({"cmd": "status"})` y, si el resultado difiere del último enviado, escribe la línea nueva a todos los suscriptores.
  - Un suscriptor que falla al escribir (`OSError`, o tiempo de espera de `SEND_TIMEOUT` = 1 s) se descarta. En cada tick también se descartan los que cerraron su extremo (`recv` no bloqueante que devuelve `b""`).
  - Límite de `MAX_SUBSCRIBERS` = 8. El noveno recibe `{"ok": false, "error": "demasiados suscriptores"}` y se cierra.
  - `ControlServer.close()` cierra todos los suscriptores y detiene el publicador antes de borrar el socket.
- Subcomando `speechflow ctl watch [--json]`: se suscribe e imprime una entrada por cada línea recibida (el resumen de `status` de la SPEC 29, separado por una línea en blanco, o el JSON crudo con `--json`). Termina con `Ctrl+C` (código 0), con 3 si no hay proceso escuchando y con 1 si el servidor cierra la conexión o responde `ok: false`.
- Tests en `tests/test_control.py` con un `handler` doble cuyo estado cambia desde el test.
- Documentación: `README.md` (sección **Canal de control**: comando `subscribe`, formato de las líneas, ejemplo con `socat`/`nc -U`, `ctl watch`) y `TODO.md` (anotar que los eventos y suscripciones de la SPEC 29 quedan cubiertos).

**Fuera de alcance (para futuras specs):**

- Eventos tipados o diferenciales (`{"event": "state", ...}`): solo la foto completa de `status`.
- Suscripciones filtradas por campo.
- Enviar texto transcrito, niveles de audio o entradas del historial por la suscripción.
- Cambios en `app.py` y ganchos de notificación en `PushToTalk`.
- Latido (heartbeat) periódico: el cierre del socket del servidor basta para avisar al cliente.
- Enviar comandos por la misma conexión de la suscripción; se usan conexiones aparte.
- Cambios en `audio.py`, `config.py`, `transcriber.py`, `inserter.py`, `log.py`, `notifier.py`, `history.py`, `punctuation.py`, `replacements.py`, `service.py` y `scripts/`.

## Modelo de datos

Esta spec no introduce estructuras persistentes ni claves de configuración. Añade constantes y el formato de las líneas de la suscripción.

```python
# src/speechflow/control.py
PUBLISH_INTERVAL = 0.25    # s entre muestras de status mientras haya suscriptores
SEND_TIMEOUT = 1.0         # s máximos para escribir a un suscriptor
MAX_SUBSCRIBERS = 8
```

Línea de la suscripción (la primera, al conectar, y una por cada cambio posterior):

```jsonc
{"ok": true, "event": "status", "pid": 1234, "state": "recording", "paused": false,
 "model": {"name": "large-v3-turbo", "status": "loaded", "compute_device": "cuda"},
 "language": "es", "mode": "hold",
 "device": {"index": 7, "name": "Blue Yeti", "connected": true}}
```

Convenciones:

- Mismo contenido que la respuesta de `status` de la SPEC 29 más el campo `event`. Los clientes ignoran los campos desconocidos.
- Una línea por mensaje, UTF-8, terminada en `\n`.
- Si el servidor cierra la conexión (apagado del proceso o `SIGKILL`), el cliente recibe EOF.
- Error al suscribirse: `{"ok": false, "error": "demasiados suscriptores"}` o el `error` que devuelva `status`, y el servidor cierra.
- El cambio se detecta comparando el `dict` de `status` con el último enviado; hasta 0,25 s de latencia.

## Plan de implementación

1. En `control.py`, que `ControlServer` reconozca `subscribe`: leer la línea, responder con la foto de `status` más `event` y guardar la conexión en una lista protegida por un `Lock` en vez de cerrarla. Tests: tras suscribirse llega una línea con `event: status`; mientras hay un suscriptor abierto, una petición normal (`status`) se atiende sin esperar. Verificar: `pytest tests/test_control.py` pasa.
2. Añadir el hilo publicador: arranque con el primer suscriptor, muestreo cada `PUBLISH_INTERVAL`, envío solo si cambió, descarte de suscriptores caídos o lentos y parada al quedar vacío. Tests con el `handler` doble: un cambio llega a dos suscriptores, sin cambios no se envía nada, el suscriptor que cierra se descarta y el hilo termina. Verificar: `pytest tests/test_control.py` pasa.
3. Añadir `MAX_SUBSCRIBERS` y el cierre de suscriptores en `close()`. Tests: el noveno recibe `demasiados suscriptores`; `close()` hace que los suscriptores reciban EOF y borra el socket. Verificar: `pytest tests/test_control.py` pasa.
4. Añadir `speechflow ctl watch [--json]` en `main()` de `control.py`, con los códigos de salida descritos y sin importar `sounddevice`, `pynput` ni `faster_whisper`. Tests con un servidor real sobre `XDG_RUNTIME_DIR` temporal. Verificar: `pytest` pasa y `speechflow ctl --help` lista `watch`.
5. Prueba manual con el sistema real y documentar en `README.md` y `TODO.md`. Verificar: los ejemplos del README son los ejecutados.

## Criterios de aceptación

- [ ] `printf '{"cmd":"subscribe"}\n' | socat - UNIX-CONNECT:$XDG_RUNTIME_DIR/speechflow/control.sock` imprime de inmediato una línea JSON con `"ok": true` y `"event": "status"` y no termina.
- [ ] Con una suscripción abierta, `speechflow ctl pause` hace que llegue una línea nueva con `"paused": true` en menos de 1 s, y `ctl resume` otra con `"paused": false`.
- [ ] Mantener el dictado pulsado produce una línea con `"state": "recording"` y al soltar otra con `"transcribing"` y otra con `"idle"`.
- [ ] Sin cambios de estado no llegan líneas nuevas.
- [ ] Con una suscripción abierta, `speechflow ctl status` responde igual de rápido que sin ella.
- [ ] Un suscriptor que no lee no bloquea a los demás ni a los comandos, y se descarta tras `SEND_TIMEOUT`.
- [ ] Un suscriptor que cierra su conexión deja de contar para el límite; con 0 suscriptores el hilo `control-publisher` no existe.
- [ ] El noveno suscriptor simultáneo recibe `demasiados suscriptores` y el proceso sigue funcionando.
- [ ] Al detener el servicio (`systemctl --user stop speechflow`, `SIGTERM` o `Ctrl+C`), los suscriptores reciben EOF y el archivo del socket se borra.
- [ ] `speechflow ctl watch` imprime el estado al conectar y en cada cambio; con `--json` imprime las líneas crudas; `Ctrl+C` sale con 0; sin proceso sale con 3 y el mensaje `SpeechFlow no está en ejecución`; si el servidor se detiene sale con 1.
- [ ] `import speechflow.control` sigue sin importar `sounddevice`, `pynput` ni `faster_whisper`.
- [ ] Los comandos de la SPEC 29 (`status`, `pause`, `resume`, `language`, `device`, `devices`) se comportan igual que antes.
- [ ] `pytest` pasa con código 0, sin GPU, sin micrófono, sin modelo real y sin tocar el socket real del usuario.
- [ ] `git diff main -- scripts src/speechflow/app.py src/speechflow/audio.py src/speechflow/config.py src/speechflow/transcriber.py src/speechflow/inserter.py src/speechflow/log.py src/speechflow/notifier.py src/speechflow/history.py src/speechflow/service.py` está vacío.
- [ ] `README.md` documenta `subscribe`, el formato de las líneas y `ctl watch`.

## Decisiones

- **Sí:** suscripción en el servidor, por elección del usuario. Evita sondeo desde cada cliente y deja el icono al instante.
- **No:** polling de `status` desde la extensión. Más simple, pero cada cliente repite el sondeo y la latencia es de hasta 1 s.
- **Sí:** foto completa de `status` en cada cambio, por elección del usuario. El cliente no mantiene estado ni combina diferencias, y el formato es el de `status`.
- **No:** eventos tipados por cambio. Menos bytes, pero el cliente debe reconstruir el estado y el protocolo crece.
- **Sí:** dividir en dos specs (servidor y extensión), por elección del usuario. Cada una se verifica por separado y el servidor se prueba sin JavaScript.
- **Sí:** muestreo de `status` en un hilo del servidor, sin ganchos en `app.py`. Decisión del diseño: el estado cambia en unos quince puntos y un gancho olvidado dejaría el icono desactualizado. El coste es hasta 0,25 s de latencia, y solo mientras haya suscriptores.
- **No:** ganchos `_notify_change()` en `PushToTalk`. Latencia nula, pero toca `app.py` en muchos sitios y es fácil olvidar uno.
- **Sí:** `subscribe` lo resuelve `ControlServer` y no el `handler`. Decisión del diseño: gestionar conexiones largas es cosa del transporte; el `handler` sigue siendo una función de petición y respuesta.
- **Sí:** descartar a los suscriptores lentos o cerrados. Decisión del diseño: un cliente colgado no puede retener el hilo publicador ni agotar el límite de 8.
- **Sí:** sin latido. Decisión del diseño: el cierre del socket del servidor llega al cliente como EOF, incluso con `SIGKILL`.
- **Sí:** los comandos van por conexiones aparte. Decisión del diseño: mantiene el servidor de petición y respuesta tal cual y evita mezclar respuestas con eventos en la misma línea.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `status` espera el `_lock` de `PushToTalk` mientras hay una operación larga | El publicador solo se retrasa; los suscriptores ven el estado anterior hasta que `status` responde. Los comandos no dependen del publicador. |
| Un suscriptor que no lee llena su búfer de envío | `sendall` con `SEND_TIMEOUT` de 1 s y descarte del suscriptor. |
| Conexiones suscritas olvidadas agotan el límite de 8 | En cada tick se detectan y descartan las conexiones cerradas por el cliente. |
| El hilo publicador queda vivo tras `close()` | `close()` lo detiene y espera su fin antes de borrar el socket. |
| Un `status` que lance una excepción mata el publicador | El tick captura la excepción, la registra en `DEBUG` y sigue con el siguiente. |

## Lo que **no** está en esta spec

- Eventos tipados, diferenciales o filtrados.
- Texto transcrito, niveles de audio o historial por la suscripción.
- Ganchos de notificación en `app.py`.
- Latido periódico y envío de comandos por la conexión suscrita.
- La extensión de GNOME Shell (SPEC 31).

Cada uno, si se aborda, va en su propia spec.
