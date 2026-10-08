# SPEC 15 — Cierre limpio ante `SIGTERM`/`SIGHUP`

> **Estado:** Implementado
> **Depende de:** SPEC 05, SPEC 06, SPEC 12, SPEC 13, SPEC 14
> **Fecha:** 2026-10-08
> **Objetivo:** Hacer que `SIGTERM`, `SIGHUP` y `SIGINT` cierren `speechflow` por la misma ruta limpia: descartar una grabación en curso, esperar (hasta 30 s) a la transcripción o recarga en curso, insertar su texto y liberar el modelo de la GPU.

## Por qué existe esta spec

Hoy solo `Ctrl+C` (`KeyboardInterrupt`) libera el modelo. `SIGTERM` (`kill`, `systemctl stop`) y `SIGHUP` (cierre de la terminal) matan el proceso sin llamar a `Transcriber.close()`, y ninguna salida espera a una transcripción en curso: `shutdown()` solo espera a la recarga del modelo, y el hilo de transcripción es `daemon`, así que el texto dictado se pierde. Es el último paso de la Fase 2 previo a los tests y requisito del servicio `systemd` de la Fase 3.

## Alcance

**Dentro:**

- Instalar manejadores para `SIGTERM`, `SIGHUP` y `SIGINT` en `main()`, después de crear `PushToTalk` y antes de entrar al listener.
- La primera señal inicia el cierre; el listener de `pynput` se detiene y `main()` ejecuta el cierre en el hilo principal.
- Grabación en curso al llegar la señal: se detiene el stream y el audio se descarta, sin transcribir.
- Transcripción en curso: se espera a que termine, se inserta su texto como siempre y después se libera el modelo.
- Recarga del modelo en curso: se espera, como ahora.
- Tope de espera fijo de 30 s (`SHUTDOWN_TIMEOUT` en `app.py`). Si se supera, se registra un `WARNING` y se sale sin llamar a `close()` (no es seguro cerrar el modelo mientras transcribe).
- Una segunda señal durante la espera fuerza la salida inmediata con código 0.
- Tras iniciarse el cierre, las teclas de grabar y de cambio de entrada se ignoran.
- Código de salida 0 en la salida limpia, igual que `Ctrl+C` hoy.
- Actualizar `README.md` y `TODO.md`.

**Fuera de alcance (para futuras specs):**

- Señales durante el arranque (validaciones y carga inicial del modelo): conservan el comportamiento actual.
- Tope de espera configurable en el TOML.
- Códigos de salida `128+señal`.
- `SIGUSR1`/`SIGUSR2`, recarga de configuración con `SIGHUP` y cualquier otra señal.
- Transcribir e insertar una grabación en curso al cerrar.
- Servicio `systemd`, daemon y bandeja del sistema (Fase 3).
- Tests con `pytest` (SPEC 16).
- Cambios en `audio.py`, `config.py`, `inserter.py`, `log.py`, `notifier.py` y `transcriber.py`.

## Modelo de datos

Esta spec no introduce estructuras de datos persistentes ni claves de configuración. Añade estado interno a `src/speechflow/app.py`:

```python
SHUTDOWN_TIMEOUT = 30.0     # segundos máximos de espera al cerrar

class PushToTalk:
    _closing: bool                          # True desde begin_shutdown(); on_press/on_release/switch_device lo ignoran
    _worker: threading.Thread | None        # hilo de transcripción en curso (antes era anónimo)

    def begin_shutdown(self) -> None: ...                           # marca _closing y descarta una grabación en curso
    def shutdown(self, timeout: float = SHUTDOWN_TIMEOUT) -> bool: ...   # espera con tope; True si liberó el modelo
```

Mensajes nuevos (el resto no cambia):

```
INFO    Señal SIGTERM recibida. Saliendo.             # SIGTERM y SIGHUP; con Ctrl+C sigue siendo solo "Saliendo."
INFO    Grabación descartada por cierre.
INFO    Esperando a la transcripción en curso (máximo 30 s)...
WARNING La transcripción no terminó en 30 s; se sale sin liberar el modelo.
WARNING Segunda señal recibida; salida inmediata.
```

Convenciones:

- Los manejadores solo marcan un evento y detienen el listener; el log y el cierre ocurren en el hilo principal, fuera del manejador.
- Los mensajes ya existentes (`Saliendo.`, `Modelo {modelo} liberado.`, notificación `Modelo liberado`) se conservan.
- La salida forzada usa `os._exit(0)` tras el `WARNING`.
- `import speechflow.app` sigue sin instalar manejadores ni tener efectos secundarios.

## Plan de implementación

1. En `PushToTalk`, guardar el hilo de transcripción en `_worker`, añadir `_closing` y `begin_shutdown()` (descarta la grabación en curso con `Grabación descartada por cierre.`, cancela el temporizador de máxima duración y deja el estado en `IDLE`), y hacer que `on_press`, `on_release` y `switch_device` salgan si `_closing`. Verificar: el arranque, un dictado y `f8` funcionan igual y `Ctrl+C` sigue liberando el modelo.
2. Cambiar `shutdown()` para aceptar `timeout`: esperar a `_worker` y a la recarga con un plazo común; si la transcripción sigue viva al vencer, `WARNING` y devolver `False` sin llamar a `close()`. Registrar `Esperando a la transcripción en curso (máximo 30 s)...` solo si había una. Verificar: `Ctrl+C` durante una transcripción espera, inserta el texto y libera el modelo.
3. En `main()`, sustituir `except KeyboardInterrupt` por manejadores de `SIGTERM`, `SIGHUP` y `SIGINT` que marcan un evento y llaman a `listener.stop()`; la segunda señal registra el `WARNING` y llama a `os._exit(0)`. Tras salir del listener: `Saliendo.` (con el nombre de la señal salvo `SIGINT`), `stop_watcher()`, `begin_shutdown()` y `shutdown()`. Verificar: `kill -TERM <pid>` y `kill -HUP <pid>` en reposo liberan el modelo y terminan con código 0.
4. Prueba manual de los casos límite con el modelo real: señal durante la grabación, durante la transcripción, durante una recarga tras descarga por inactividad, segunda señal durante la espera y vencimiento del tope (reduciendo `SHUTDOWN_TIMEOUT` temporalmente). Verificar: cada caso coincide con los criterios de aceptación.
5. Actualizar `README.md` (sección **Push-to-talk**, punto **Salida**) y `TODO.md` (marcar la SPEC 15 y las dos ideas "Esperar a una transcripción en curso al salir" y "Liberar el modelo en señales distintas de `Ctrl+C`"). Verificar: el README no describe `Ctrl+C` como la única forma de cerrar.

## Criterios de aceptación

- [ ] `kill -TERM <pid>` en reposo registra `Señal SIGTERM recibida. Saliendo.` y `Modelo {modelo} liberado.`, envía la notificación `Modelo liberado` y el proceso termina con código 0.
- [ ] `kill -HUP <pid>` hace lo mismo con `SIGHUP`.
- [ ] `Ctrl+C` sigue mostrando `Saliendo.` y `Modelo {modelo} liberado.` y termina con código 0.
- [ ] Una señal con la tecla de grabar pulsada registra `Grabación descartada por cierre.`, no invoca al modelo, no inserta texto y libera el modelo.
- [ ] Una señal durante una transcripción registra `Esperando a la transcripción en curso (máximo 30 s)...`, inserta el texto en la ventana con foco y después libera el modelo.
- [ ] Una señal durante la recarga del modelo espera a que termine y libera el modelo; el audio en curso se descarta.
- [ ] Con el modelo ya descargado por inactividad, la señal solo muestra el mensaje de salida, sin `Modelo ... liberado.`.
- [ ] Tras la primera señal, pulsar la tecla de grabar o la de cambio de entrada no tiene efecto.
- [ ] Una segunda señal durante la espera registra `Segunda señal recibida; salida inmediata.` y termina el proceso con código 0 sin esperar.
- [ ] Si la transcripción dura más de 30 s tras la señal, se registra el `WARNING` del tope, no se llama a `Transcriber.close()` y el proceso termina con código 0.
- [ ] Ninguna señal deja un hilo vivo que mantenga el proceso abierto tras el cierre.
- [ ] `import speechflow.app` no instala manejadores de señales.
- [ ] El arranque, el dictado, el cambio de entrada, la vigilancia del micrófono y la descarga por inactividad producen los mismos mensajes y notificaciones que antes.
- [ ] `README.md` documenta `SIGTERM`, `SIGHUP`, el tope de 30 s y el descarte de la grabación en curso.

## Decisiones

- **Sí:** descartar la grabación en curso al cerrar, por elección del usuario. Cerrar es una orden explícita y escribir texto inesperado en una ventana que pudo cambiar sorprendería más que perder un dictado a medias.
- **No:** transcribir e insertar la grabación en curso. Alarga el cierre y escribe texto después de pedir salir.
- **Sí:** esperar a la transcripción en curso e insertar su texto, por elección del usuario. Lo ya dictado y enviado a transcribir no se pierde.
- **Sí:** tope fijo de 30 s, por elección del usuario. Con `medium` int8 un audio de 60 s tarda unos segundos, así que 30 s sobra y un cuelgue de CUDA no bloquea `systemctl stop` ni el cierre de sesión.
- **No:** tope configurable. Añade una clave al TOML, validación y documentación (SPEC 10) por un valor que casi nadie cambia.
- **No:** espera sin tope. Un cuelgue de CUDA impediría terminar el proceso con `SIGTERM`.
- **Sí:** segunda señal fuerza la salida con código 0, por elección del usuario. Es la salida de emergencia cuando la espera molesta, y conserva el código 0 que ya da `Ctrl+C`.
- **No:** código `128+señal` (143 y 129). Rompería el código 0 actual de `Ctrl+C` y no aporta nada a quien ya pidió el cierre.
- **No:** ignorar señales repetidas. Sin escape manual, el único recurso sería `SIGKILL`.
- **Sí:** `SIGINT` pasa por el mismo manejador que `SIGTERM` y `SIGHUP`. Una sola ruta de cierre evita que `Ctrl+C` se comporte distinto y le da también la espera a la transcripción y la segunda señal. Decisión del diseño, no preguntada al usuario.
- **Sí:** los manejadores solo marcan un evento y detienen el listener; el cierre corre en el hilo principal. Un manejador de señales no debe hacer E/S ni tomar locks que otro hilo pueda tener. Decisión del diseño, no preguntada al usuario.
- **Sí:** no llamar a `close()` si la transcripción sigue viva al vencer el tope. Cerrar el modelo mientras transcribe puede abortar el proceso con un fallo de CUDA; el sistema libera la VRAM al terminar el proceso.
- **No:** manejar señales durante el arranque. Es una ventana corta y el comportamiento actual (traza de `Ctrl+C` o muerte inmediata por `SIGTERM`) no pierde datos.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `listener.stop()` desde un manejador de señales no hace volver a `listener.join()` | Verificar en el paso 3; si falla, el manejador marca el evento y el hilo principal espera con `Event.wait()` en lugar de `listener.join()`. |
| La señal llega entre `on_release` y el arranque del hilo de transcripción y la grabación se descarta sin avisar | `begin_shutdown()` solo descarta con estado `RECORDING`; tras `on_release` el estado ya es `TRANSCRIBING` y se espera. |
| `SIGHUP` llega porque se cerró la terminal y `stdout`/`stderr` ya no existen, y el `logger` falla al escribir | Probar el cierre de una terminal real en el paso 4; si el log lanza `OSError`, capturarlo en el cierre para que no impida liberar el modelo. |
| `insert_text` tras la señal escribe en una ventana distinta de la prevista | Mismo comportamiento que sin señal (el texto va a la ventana con foco); ya documentado en **Foco**. |
| `os._exit(0)` en la segunda señal deja el modelo sin liberar y las notificaciones sin enviar | Solo ocurre por petición explícita; el sistema libera la VRAM al terminar el proceso. |
| PortAudio imprime por stderr al detener un stream durante la señal | Ya ocurre al desconectar el micrófono (SPEC 11); no se corrige aquí. |

## Lo que **no** está en esta spec

- Manejo de señales durante el arranque.
- Tope de espera configurable.
- Códigos de salida `128+señal`.
- Recarga de configuración con `SIGHUP` u otras señales.
- Transcribir e insertar la grabación en curso al cerrar.
- Servicio `systemd`, daemon, archivo de log y bandeja del sistema.
- Tests con `pytest` (SPEC 16).

Cada uno, si se aborda, va en su propia spec.
