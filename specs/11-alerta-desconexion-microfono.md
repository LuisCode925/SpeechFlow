# SPEC 11 — Alerta de desconexión del micrófono

> **Estado:** Implementado
> **Depende de:** SPEC 05, SPEC 06, SPEC 07, SPEC 08, SPEC 10
> **Fecha:** 2026-10-05
> **Objetivo:** Avisar por log y notificación de escritorio cuando el micrófono seleccionado de `push_to_talk.py` se desconecta (o se reconecta), mediante un hilo vigilante que comprueba el dispositivo cada `[audio] watch_interval` segundos.

## Por qué existe esta spec

Hoy, si el micrófono USB se desenchufa, el script no se entera: el siguiente dictado falla al abrir el stream (`Error al abrir el micrófono`) o, peor, el índice guardado en `recorder.device` apunta a otro dispositivo tras reinicializar PortAudio y se graba con un micrófono distinto sin avisar. Al dictar en otra ventana la consola no se ve, así que el aviso tiene que llegar por notificación de escritorio, en el momento de la desconexión y no al intentar dictar.

## Alcance

**Dentro:**

- Un hilo vigilante `daemon` en `scripts/push_to_talk.py` que cada `watch_interval` segundos comprueba si el micrófono seleccionado sigue presente.
- Identidad del micrófono **por nombre** (el del dispositivo efectivo al arrancar; con `None`, el del sistema). Cada cambio efectivo con la tecla de cambio actualiza el nombre vigilado.
- Comprobación en `IDLE`: bajo `self._lock`, `refresh_devices()` y búsqueda del nombre exacto entre los dispositivos de entrada.
- Comprobación en `RECORDING`: sin reinicializar PortAudio, el hilo mira si el `InputStream` sigue activo. Si cayó: aviso, se detiene la grabación y se transcribe lo capturado (con el mínimo `min_seconds` de siempre).
- Sin comprobación en `TRANSCRIBING`; el hilo espera al siguiente ciclo.
- Alerta solo en la transición presente → ausente: `WARNING` en consola y notificación de escritorio. No se repite mientras siga ausente.
- Aviso de reconexión: cuando el mismo nombre vuelve a estar presente, `INFO` y notificación; además se reasigna `recorder.device` al índice nuevo, de modo que el siguiente dictado funciona sin pulsar la tecla de cambio.
- Con el micrófono ausente, pulsar la tecla de grabar no graba: registra un `WARNING` (evita grabar con otro dispositivo por un índice obsoleto).
- Alerta también al arrancar: si el dispositivo guardado en `.speechflow-state.toml` no está disponible, además del `WARNING` actual de la SPEC 10 se envía una notificación de escritorio.
- Clave nueva `[audio] watch_interval` en la configuración (SPEC 10), defecto `3.0` s.
- En `src/speechflow/audio.py`: `device_name()`, `input_device_by_name()` y `Recorder.active`; `Recorder.stop()` tolera un stream caído.
- Actualizar `speechflow.example.toml`, la plantilla de emergencia, `README.md`, el docstring del script y `TODO.md` si procede.

**Fuera de alcance (para futuras specs):**

- Cambio automático al siguiente micrófono al desconectarse (sigue pendiente de la SPEC 08).
- Comprobación pasiva al pulsar la tecla de grabar (descartada a favor del hilo vigilante).
- Detección por eventos del sistema (`udev`, `pyudev`, `/proc/asound/cards`).
- Sonido u otro tipo de alerta además de log y notificación.
- Alerta por un `--device` o `[audio] device` inexistentes al arrancar (siguen siendo `ERROR` y código 1, SPEC 10).
- Notificaciones por tipo o claves para silenciar solo estas alertas (rige el interruptor `[notifications] enabled`).
- Cambios en `Transcriber`, `inserter.py`, `notifier.py`, `log.py`, `capture_mic.py` y `benchmark_stt.py`.
- Vigilar otros dispositivos que no sean el seleccionado.

## Modelo de datos

Interfaz pública nueva:

```python
# src/speechflow/audio.py
def device_name(device: int | str | None) -> str | None: ...        # nombre del dispositivo de entrada; None si no se resuelve
def input_device_by_name(name: str) -> int | None: ...              # índice del primer dispositivo de entrada con ese nombre exacto

class Recorder:
    @property
    def active(self) -> bool: ...                                    # True si hay un InputStream abierto y activo
```

```python
# src/speechflow/config.py
@dataclass(frozen=True)
class Config:
    ...
    watch_interval: float = 3.0     # [audio] watch_interval, en segundos
```

```python
# scripts/push_to_talk.py
class PushToTalk:
    _watched_name: str | None       # nombre del micrófono vigilado
    _device_missing: bool           # True entre la alerta de desconexión y la reconexión
    _stop_watcher: threading.Event
    def start_watcher(self, interval: float) -> None: ...
    def stop_watcher(self) -> None: ...
    def _watch(self, interval: float) -> None: ...
```

```toml
[audio]
# watch_interval = 3.0   # segundos entre comprobaciones del micrófono; mínimo 1.0
```

Convenciones:

- `Recorder.active` es `self._stream is not None and self._stream.active`.
- `Recorder.stop()` captura `sd.PortAudioError` al parar y cerrar el stream; devuelve el audio capturado hasta ese momento.
- `_watched_name` y `_device_missing` se leen y escriben solo bajo `self._lock`.
- El hilo usa `self._stop_watcher.wait(interval)` como pausa; `stop_watcher()` activa el evento al salir con `Ctrl+C`.
- La comprobación en `IDLE` toma `self._lock` durante `refresh_devices()`; una pulsación de tecla puede esperar ese tiempo.
- Un fallo de `refresh_devices()` en el hilo se registra como `ERROR` una sola vez hasta que un ciclo vuelva a funcionar, y el hilo sigue vivo.
- Validación de la clave: `watch_interval` debe ser número (entero o decimal, no `bool`) y mayor o igual que `1.0`; si no, `ConfigError` con `audio.watch_interval` en el mensaje.
- Mensajes de consola:
  - `WARNING` `El micrófono seleccionado se desconectó: {nombre}.`
  - `WARNING` `El micrófono seleccionado se desconectó durante la grabación: {nombre}.`
  - `INFO` `Micrófono reconectado: [N] {nombre} | {tasa} Hz nativos a 16000 Hz mono` (salida de `describe_device()`).
  - `WARNING` `El micrófono seleccionado no está conectado ({nombre}); reconéctalo o pulsa la tecla de cambio para elegir otro.` (al pulsar la tecla de grabar con el micrófono ausente).
  - `ERROR` `Error al comprobar el micrófono: {error}`.
  - Se mantiene el `WARNING` de la SPEC 10 `El dispositivo guardado {nombre!r} no está disponible; ...`.
- Notificaciones de escritorio, título `SpeechFlow`:
  - `Micrófono desconectado: {nombre}`
  - `Micrófono reconectado: {nombre}`
  - `Micrófono guardado no disponible: {nombre}` (solo al arrancar)
  - No se envía notificación al pulsar la tecla de grabar con el micrófono ausente.
- Con `[notifications] enabled = false` ninguna de estas notificaciones se envía; los mensajes de consola se mantienen.
- Con la tecla de cambio y un cambio efectivo, `_watched_name` pasa al nombre del dispositivo nuevo y `_device_missing` a `False`.

## Plan de implementación

1. En `src/speechflow/audio.py`, añadir `device_name()`, `input_device_by_name()`, `Recorder.active` y hacer tolerante `Recorder.stop()` a `sd.PortAudioError`. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.audio import *; i = input_devices()[0]; n = device_name(i); print(n, input_device_by_name(n) == i, input_device_by_name('no existe'), Recorder().active)"` imprime el nombre, `True`, `None` y `False`.
2. En `src/speechflow/config.py`, añadir `Config.watch_interval`, su entrada en `_SCHEMA` (`audio.watch_interval`), la validación (mínimo `1.0`) y la línea correspondiente en la plantilla de emergencia; documentar la clave en `speechflow.example.toml`. Verificar: un TOML con `watch_interval = 5` devuelve `5.0`; `0.5` y `"3"` lanzan `ConfigError` con `audio.watch_interval`; `speechflow.emergency.toml` generado incluye la clave.
3. En `scripts/push_to_talk.py`, añadir `_watched_name`, `_device_missing`, `start_watcher()`, `stop_watcher()` y `_watch()` con la comprobación en `IDLE`: alerta de desconexión (`WARNING` + notificación) solo en la transición, sin repeticiones. Arrancar el hilo en `main()` tras cargar el modelo, con `config.watch_interval`, y detenerlo al salir. Verificar: con el micrófono USB seleccionado, desenchufarlo produce una sola línea `WARNING` y una notificación en menos de `watch_interval` s; seguir desenchufado no repite el aviso.
4. Añadir el aviso de reconexión: al volver el nombre, `INFO` + notificación y reasignación de `recorder.device` al índice nuevo; actualizar `_watched_name` y `_device_missing` en `switch_device()`; bloquear con `WARNING` la pulsación de la tecla de grabar mientras `_device_missing`. Verificar: al reenchufar aparece `Micrófono reconectado: ...` y un dictado posterior se graba con ese micrófono sin pulsar `f8`; con el micrófono ausente, la tecla de grabar solo muestra el `WARNING`; pulsar `f8` con el micrófono ausente pasa a otro dispositivo y se reanuda la vigilancia sobre él.
5. Añadir la comprobación en `RECORDING`: si `recorder.active` es `False`, `WARNING` + notificación, `_device_missing = True` y `_stop_recording(False)` fuera del lock. Verificar: desenchufar el micrófono a mitad de un dictado largo registra `El micrófono seleccionado se desconectó durante la grabación: ...`, no lanza excepciones y transcribe lo capturado (o lo descarta si es menor que `min_seconds`).
6. En `main()`, enviar la notificación `Micrófono guardado no disponible: {nombre}` junto al `WARNING` existente cuando el dispositivo guardado no está. Verificar: con un `.speechflow-state.toml` que nombra un micrófono desconectado, al arrancar aparecen el `WARNING` y la notificación; con `[notifications] enabled = false`, solo el `WARNING`.
7. Actualizar `README.md` (vigilante, clave `watch_interval`, mensajes y notificaciones nuevas, funciones nuevas de `audio.py`) y el docstring del script. Verificar: la salida de ejemplo del README coincide con la real.

## Criterios de aceptación

- [ ] `src/speechflow/audio.py` expone `device_name()`, `input_device_by_name()` y `Recorder.active`.
- [ ] `Recorder.stop()` no lanza excepción si el stream cayó y devuelve el audio capturado.
- [ ] `[audio] watch_interval` acepta números mayores o iguales que `1.0` y el defecto es `3.0`; `0.5`, un texto o un booleano terminan en el camino de configuración inválida de la SPEC 10 con `audio.watch_interval` en la causa.
- [ ] `speechflow.example.toml` y la plantilla de emergencia incluyen `watch_interval`.
- [ ] Desconectar el micrófono seleccionado en `IDLE` registra `El micrófono seleccionado se desconectó: {nombre}.` a nivel `WARNING` y envía la notificación `Micrófono desconectado: {nombre}`, en un máximo de `watch_interval` s más lo que tarde `refresh_devices()`.
- [ ] Mientras siga desconectado, el aviso no se repite.
- [ ] Reconectarlo registra `Micrófono reconectado: ...` a nivel `INFO` y envía la notificación `Micrófono reconectado: {nombre}`.
- [ ] Tras la reconexión, el siguiente dictado se graba con ese micrófono sin pulsar la tecla de cambio, aunque su índice haya cambiado.
- [ ] Con el micrófono ausente, pulsar la tecla de grabar registra el `WARNING` indicado, no abre ningún stream, no envía notificación y no cambia el estado.
- [ ] Con el micrófono ausente, la tecla de cambio pasa a otro dispositivo, y a partir de ahí se vigila ese.
- [ ] Un cambio efectivo con la tecla de cambio hace que el hilo vigile el dispositivo nuevo; desconectar el anterior no genera alerta.
- [ ] Desconectar el micrófono durante una grabación registra `El micrófono seleccionado se desconectó durante la grabación: {nombre}.`, envía la notificación, detiene la grabación y transcribe lo capturado si dura al menos `min_seconds`.
- [ ] El hilo no llama a `refresh_devices()` con el estado `RECORDING` ni `TRANSCRIBING`.
- [ ] Un fallo de `refresh_devices()` en el hilo se registra una sola vez como `ERROR` y el hilo sigue funcionando.
- [ ] Con `[notifications] enabled = false`, ninguna de las notificaciones nuevas se envía y los mensajes de consola siguen apareciendo.
- [ ] Con un dispositivo guardado inexistente, el arranque registra el `WARNING` de la SPEC 10 y envía la notificación `Micrófono guardado no disponible: {nombre}`.
- [ ] `Ctrl+C` termina el script sin colgarse por el hilo vigilante.
- [ ] El modelo no se recarga (no aparece `Cargando` ni cambia el uso de VRAM).
- [ ] `--list-devices`, `capture_mic.py` y `benchmark_stt.py` producen la misma salida que antes.
- [ ] `README.md` documenta `watch_interval`, el vigilante y los mensajes y notificaciones nuevos.

## Decisiones

- **Sí:** hilo vigilante activo, por elección del usuario. Es lo único que avisa en el momento de la desconexión aunque no se esté dictando.
- **No:** comprobación pasiva al pulsar la tecla de grabar. Obligaba a elegir entre `refresh_devices()` en la pulsación (retraso al empezar a grabar y palabras perdidas) o depender del fallo de `start()` (error crudo de PortAudio). Con el hilo activo no aporta nada.
- **Sí:** `refresh_devices()` cada `watch_interval` s, solo en `IDLE` y bajo `self._lock`, por elección del usuario. Reutiliza la API de la SPEC 08 y respeta su regla de no reinicializar PortAudio con un stream abierto.
- **No:** leer `/proc/asound/cards` o usar `udev`. Más ligero, pero casar la tarjeta ALSA con el nombre de `sounddevice` es frágil; queda como mejora futura.
- **Sí:** alerta con `WARNING` en consola y notificación de escritorio, por elección del usuario. Al dictar en otra ventana la consola no se ve. Amplía la regla de notificaciones de las SPEC 06 y 08 con tres eventos más.
- **Sí:** solo avisar y mantener el dispositivo seleccionado, por elección del usuario. El cambio automático sigue fuera de alcance (SPEC 08): sorprendería al usuario cambiando de micrófono sin pedirlo.
- **Sí:** identificar el micrófono por nombre exacto y reasignar el índice al reconectar, por elección del usuario. Los índices cambian con cada `refresh_devices()` (SPEC 08); el nombre no.
- **Sí:** aviso de reconexión, por elección del usuario. Cierra el ciclo del aviso y confirma que el dictado vuelve a funcionar.
- **Sí:** bloquear la tecla de grabar con un `WARNING` mientras el micrófono está ausente. Consecuencia del índice obsoleto: tras `refresh_devices()` ese índice puede apuntar a otro dispositivo y se grabaría con un micrófono no elegido. Decisión del diseño, no elegida explícitamente por el usuario; se puede revertir si se prefiere el comportamiento anterior (intentar abrir y mostrar el error de PortAudio).
- **Sí:** vigilar `Recorder.active` durante `RECORDING` y transcribir lo capturado, por elección del usuario. No requiere reinicializar PortAudio. Si el stream no se marca como inactivo al desenchufar, la desconexión se detecta al volver a `IDLE` (ver Riesgos).
- **No:** descartar la grabación parcial. El usuario eligió aprovechar lo dicho hasta el corte.
- **Sí:** `[audio] watch_interval` configurable con defecto `3.0` y mínimo `1.0`, por elección del usuario. Amplía la SPEC 10 con una clave; el mínimo evita reinicializar PortAudio de forma continua (ruido de ALSA y contención del lock). El mínimo y el defecto los fija esta spec.
- **Sí:** alerta con notificación también al arrancar si falta el dispositivo guardado, por elección del usuario. Un `--device` o `[audio] device` inexistentes siguen siendo `ERROR` con salida, que ya es visible.
- **Sí:** alertar solo en las transiciones, con un indicador `_device_missing`. Evita una notificación cada `watch_interval` s.
- **Sí:** `Recorder` cambia (propiedad `active` y `stop()` tolerante), a diferencia de la SPEC 08. Es la forma mínima de detectar y sobrevivir a un stream caído.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `refresh_devices()` cada pocos segundos retrasa una pulsación de tecla (el hilo tiene el lock) o genera ruido de ALSA | Mínimo de `watch_interval` de `1.0` s y defecto de `3.0` s; el paso 3 mide el tiempo de `refresh_devices()` con el hardware real y, si es inaceptable, se ajusta el defecto. |
| Al desenchufar a mitad de grabación, el `InputStream` sigue marcado como activo y no se detecta | El hilo detecta la ausencia al volver a `IDLE` en el siguiente ciclo; el error de `start()` y de `Recorder.stop()` (ahora tolerante) sigue siendo la red de seguridad. El paso 5 comprueba con hardware real si `active` cambia. |
| `Recorder.stop()` lanza excepción con el stream caído y deja el estado en `RECORDING` | `stop()` captura `sd.PortAudioError`; el criterio de aceptación exige que no lance. |
| Dos micrófonos con el mismo nombre exacto | Se usa el primero con ese nombre; la desconexión de uno de ellos puede no detectarse. Aceptado: caso poco habitual. |
| Deadlock por llamar a `_stop_recording()` con el lock tomado | El hilo evalúa la condición bajo el lock y llama a `_stop_recording(False)` después de soltarlo; `_stop_recording()` ya ignora el caso en que el estado ya no sea `RECORDING`. |
| El nombre vigilado queda obsoleto tras un cambio con la tecla de cambio | `switch_device()` actualiza `_watched_name` y `_device_missing` bajo el lock. |
| Un hilo que no termina bloquea la salida | Hilo `daemon` y pausa con `Event.wait()`; `stop_watcher()` se llama al salir. |
| Otros procesos reinicializan o modifican dispositivos (PulseAudio/PipeWire renombra) | El nombre exacto puede variar; se trata como desconexión y el usuario ve el aviso y pulsa la tecla de cambio. |

## Lo que **no** está en esta spec

- Cambio automático de micrófono al desconectarse.
- Comprobación pasiva al pulsar la tecla de grabar.
- Detección por eventos del sistema (`udev`, `/proc/asound/cards`).
- Sonido u otra alerta además de log y notificación.
- Alertas por `--device` o `[audio] device` inexistentes al arrancar (siguen siendo `ERROR`).
- Silenciar solo estas notificaciones (rige `[notifications] enabled`).
- Vigilar dispositivos distintos del seleccionado.

Cada uno, si se aborda, va en su propia spec.
