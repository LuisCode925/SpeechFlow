# SPEC 08 — Cambio de entrada de audio en caliente

> **Estado:** Aprobado
> **Depende de:** SPEC 03, SPEC 05, SPEC 06, SPEC 07
> **Fecha:** 2026-10-05
> **Objetivo:** Permitir cambiar el dispositivo de entrada de audio de `push_to_talk.py` mientras corre, con una segunda tecla global que cicla entre los micrófonos disponibles y avisa por log y notificación de escritorio.

## Por qué existe esta spec

Hoy el micrófono se fija al arrancar con `--device` o con `default_device()`. Si el usuario conecta un micrófono USB, se pone unos auriculares o descubre que el elegido no capta, tiene que cerrar el script y volver a cargar el modelo (varios segundos y ~1.5 GB en GPU). El dispositivo solo se consulta en `Recorder.start()`, así que cambiarlo en caliente no exige tocar el modelo.

## Alcance

**Dentro:**

- Añadir la opción `--switch-key` a `scripts/push_to_talk.py`, con el mismo formato que `--key` (nombre de `pynput.keyboard.Key` o un carácter suelto) y defecto `f8`.
- Al pulsar la tecla de cambio, pasar al siguiente dispositivo con `max_input_channels > 0`, en orden de índice y con vuelta al principio.
- Releer la lista de dispositivos en cada cambio, reinicializando PortAudio (`sd._terminate()` / `sd._initialize()`) para detectar micrófonos conectados o desconectados con el script en marcha.
- Cambiar solo en estado `IDLE`. En `RECORDING` o `TRANSCRIBING` se registra un `WARNING` y el dispositivo no cambia.
- Informar de cada cambio por consola (`INFO`) y por notificación de escritorio.
- Filtrar las repeticiones automáticas de la tecla de cambio, como se hace con `--key`.
- Salir con `ERROR` y código 1 si `--switch-key` es inválida o igual a `--key`.
- Añadir al banner de arranque una línea con la tecla de cambio.
- En `src/speechflow/audio.py`, añadir `input_devices()`, `refresh_devices()`, `device_index()` y `next_input_device()`.
- Actualizar `README.md` (opción nueva, salida de ejemplo, módulo `audio.py`, notificaciones) y el docstring del script.

**Fuera de alcance (para futuras specs):**

- Recordar el dispositivo elegido entre ejecuciones (archivo de configuración).
- Cambio por stdin, señales (`SIGUSR1`), icono de bandeja o menú gráfico.
- Retroceder al dispositivo anterior (solo se avanza), elegir uno por índice o nombre en caliente.
- Lista de rotación configurable (`--devices 6,9`) o filtros por nombre.
- Cambio automático al conectar o desconectar un micrófono, o cuando el dispositivo actual falla.
- Diferir el cambio hasta volver a `IDLE`.
- Comprobar que el dispositivo se puede abrir al cambiar (un fallo se ve al dictar, como hoy).
- Cambios en `Transcriber`, `inserter.py`, `notifier.py` o `log.py`.
- Cambios en `capture_mic.py` y `benchmark_stt.py`.

## Modelo de datos

No hay estructuras de datos persistentes nuevas. Interfaz pública nueva:

```python
# src/speechflow/audio.py
def input_devices() -> list[int]: ...                     # índices con max_input_channels > 0, en orden
def refresh_devices() -> None: ...                        # sd._terminate(); sd._initialize()
def device_index(device: int | str | None) -> int | None: ...   # índice real; None si no se puede resolver
def next_input_device(current: int | str | None) -> int | None: ...   # siguiente de input_devices(); None si no hay ninguno
```

```python
# scripts/push_to_talk.py
DEFAULT_SWITCH_KEY = "f8"

class PushToTalk:
    switch_key: keyboard.Key | keyboard.KeyCode
    _switch_held: bool                  # filtra repeticiones de la tecla de cambio
    def switch_device(self) -> None: ...
```

Convenciones:

- `Recorder.device` ya se lee en cada `start()`; el cambio consiste en asignar `self.recorder.device` con el índice nuevo. `Recorder` no cambia.
- `next_input_device(current)` resuelve `current` con `device_index()`. Si `current` es `None` y el del sistema es resoluble, parte de ese. Si `current` ya no está en la lista (desconectado) o no se resuelve, devuelve el primero. Si es el último, devuelve el primero.
- `device_index()` contiene la lógica de índice que hoy vive en `describe_device()` (`info.get("index")`, el entero de `--device` o la posición por nombre); `describe_device()` pasa a usarla.
- `refresh_devices()` solo se llama con `state is IDLE`, bajo `self._lock` y sin `InputStream` abierto.
- Mensajes de consola (nivel `INFO` salvo que se indique):
  - `Entrada de audio cambiada: [9] Realtek Audio USB: Audio (hw:3,0) | 44100 Hz nativos a 16000 Hz mono`
  - `Solo hay un dispositivo de entrada: [9] Realtek Audio USB: Audio (hw:3,0) | 44100 Hz nativos a 16000 Hz mono`
  - `WARNING` `No se cambia la entrada de audio mientras se graba o se transcribe.`
  - `ERROR` `No hay dispositivos de entrada disponibles; se mantiene {dispositivo anterior}.`
  - Banner: `Cambio de entrada de audio: tecla 'f8'.`
  - `ERROR` de arranque: `Error con --switch-key: {motivo}` y `--switch-key y --key no pueden ser la misma tecla ({nombre}).`
- Notificación de escritorio, título `SpeechFlow` y cuerpo `Entrada de audio: {nombre del dispositivo}`. Solo al cambiar de verdad: no se envía en el caso de un único dispositivo ni en los avisos.
- El estado del dispositivo vive solo en `PushToTalk.recorder.device`; no se persiste.

## Plan de implementación

1. En `src/speechflow/audio.py`, añadir `input_devices()`, `refresh_devices()`, `device_index()` y `next_input_device()`. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.audio import *; print(input_devices()); print(next_input_device(input_devices()[-1]) == input_devices()[0]); print(next_input_device(None)); print(next_input_device(999))"` imprime la lista de índices, `True`, un índice válido y el primer índice.
2. En `scripts/push_to_talk.py`, hacer que `describe_device()` use `device_index()`, sin cambiar su salida. Verificar: el banner de arranque muestra el mismo texto de dispositivo que antes con `--device 6` y con `--device "Realtek"`.
3. Añadir `--switch-key` (defecto `f8`), su validación (inválida o igual a `--key` → `ERROR` + `sys.exit(1)`) y la línea de banner `Cambio de entrada de audio: tecla 'f8'.`; pasar la tecla a `PushToTalk`. La tecla aún no hace nada. Verificar: `--switch-key tecla_falsa` y `--switch-key ctrl_r` salen con una línea `ERROR` con prefijo y código 1; el arranque normal muestra la línea de banner.
4. Implementar `PushToTalk.switch_device()` y enrutar la tecla en `on_press`/`on_release` (con `_switch_held`): bajo `self._lock`, si no está `IDLE` registrar el `WARNING` y salir; si lo está, `refresh_devices()`, `next_input_device()`, asignar `recorder.device` y registrar `Entrada de audio cambiada: ...` (o los mensajes de un solo dispositivo y de ninguno). Verificar: con dos o más micrófonos, pulsar `f8` imprime el dispositivo siguiente, la siguiente pulsación el otro, y un dictado posterior se graba con el nuevo (el pico de la grabación cambia al hablar en cada micrófono).
5. Enviar la notificación `Entrada de audio: {nombre}` solo en el caso de cambio efectivo. Verificar: `f8` muestra la notificación; un dictado completo sigue sin generar ninguna; el aviso de `RECORDING` no genera notificación.
6. Actualizar `README.md` y el docstring del script con la opción, el ejemplo de salida, las funciones nuevas de `audio.py` y la lista de notificaciones. Verificar: la salida de ejemplo del README coincide con la real.

## Criterios de aceptación

- [ ] `src/speechflow/audio.py` expone `input_devices()`, `refresh_devices()`, `device_index()` y `next_input_device()`.
- [ ] `push_to_talk.py --help` muestra `--switch-key` con defecto `f8`.
- [ ] El banner de arranque incluye `Cambio de entrada de audio: tecla 'f8'.` con el nombre real de la tecla.
- [ ] Pulsar la tecla de cambio en `IDLE` registra `Entrada de audio cambiada: [N] ...` con el índice, nombre y tasa del dispositivo siguiente.
- [ ] Pulsar la tecla de cambio tantas veces como dispositivos de entrada haya vuelve al dispositivo inicial.
- [ ] Tras el cambio, el siguiente dictado se graba con el dispositivo nuevo.
- [ ] Mantener pulsada la tecla de cambio provoca un solo cambio, no uno por repetición automática.
- [ ] Con un micrófono USB conectado después de arrancar, un cambio lo incluye en la rotación sin reiniciar el script.
- [ ] Con el dispositivo actual desconectado, el cambio pasa al primer dispositivo disponible.
- [ ] Con un único dispositivo de entrada, el cambio registra `Solo hay un dispositivo de entrada: ...` a nivel `INFO` y no envía notificación.
- [ ] Pulsar la tecla de cambio durante `RECORDING` o `TRANSCRIBING` registra el `WARNING` indicado, no cambia el dispositivo y no interrumpe la grabación ni la transcripción.
- [ ] Un cambio efectivo envía la notificación `Entrada de audio: {nombre}`; un dictado completo sigue sin generar notificaciones.
- [ ] `--switch-key tecla_falsa` y `--switch-key` igual a `--key` terminan con código 1 y una línea `ERROR` con prefijo.
- [ ] Con `--device 6`, el primer cambio avanza desde el dispositivo 6 y no desde el defecto.
- [ ] El modelo no se recarga al cambiar de dispositivo (no aparece `Cargando` ni cambia el uso de VRAM).
- [ ] `capture_mic.py` y `benchmark_stt.py` producen la misma salida que antes.
- [ ] `README.md` documenta `--switch-key`, la notificación nueva y las funciones de `audio.py`.

## Decisiones

- **Sí:** atajo global para ciclar, por elección del usuario. Funciona desde cualquier ventana, que es el modo de uso del script, y reutiliza el `pynput.Listener` existente.
- **No:** comandos por stdin ni `SIGUSR1`. El primero exige foco en la terminal; el segundo es poco descubrible. Pueden ser otra spec.
- **Sí:** ciclar entre todos los dispositivos de entrada, por elección del usuario. Es lo que lista `--list-devices` y no añade configuración.
- **No:** lista de rotación configurable. Más superficie de CLI para un caso que aún no se ha pedido.
- **Sí:** releer la lista en cada cambio con reinicialización de PortAudio, por elección del usuario. Sin ella `sounddevice` conserva la lista del arranque y no vería micrófonos conectados después.
- **No:** solo `query_devices()` sin reinicializar. No detecta cambios y contradice la elección anterior.
- **Sí:** informar por log `INFO` y notificación de escritorio, por elección del usuario. Al dictar en otra ventana la consola no se ve; sin notificación no se sabe con qué micrófono se hablará.
- **Sí:** esta spec amplía la regla de la SPEC 06 (notificar solo ciclo de vida del modelo y errores) con una notificación más, la de cambio de entrada. La SPEC 06 sigue vigente para todo lo demás.
- **Sí:** ignorar el cambio fuera de `IDLE`, con `WARNING`, por elección del usuario. Nunca se cambia el micrófono a mitad de un dictado ni se acumula estado pendiente.
- **No:** diferir el cambio hasta `IDLE`, ni cambiar solo para la siguiente grabación. Añaden estado oculto o discrepancias entre el log y lo que se graba.
- **Sí:** `--switch-key` con defecto `f8`, por elección del usuario. No coincide con `ctrl_r` ni con el ejemplo `f9` del README.
- **Sí:** salir con error si `--switch-key` iguala a `--key`. Una misma tecla no puede grabar y cambiar a la vez.
- **Sí:** el dispositivo solo vive en memoria, por elección del usuario. Al reiniciar vuelve a `--device` o al valor por defecto; la configuración persistente queda fuera, como en la SPEC 06.
- **Sí:** solo avanzar al siguiente, con vuelta al inicio. Un único gesto basta para recorrer cualquier lista y evita una segunda tecla.
- **Sí:** `Recorder` queda sin cambios; basta asignar `recorder.device`, porque `start()` ya lee el dispositivo en cada grabación.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `sd._terminate()` / `sd._initialize()` es API privada y puede cambiar entre versiones de `sounddevice` | Se encapsulan en `refresh_devices()`, un único punto de cambio. `environment.yml` fija la versión; un fallo de la llamada se captura y se registra como `ERROR` sin cambiar de dispositivo. |
| Reinicializar PortAudio con un stream abierto lo corrompe | Solo se hace en `IDLE`, bajo `self._lock`, cuando `Recorder.stop()` ya cerró el stream. |
| Los índices cambian tras reinicializar (conexión o desconexión) | El índice se resuelve de nuevo en cada cambio y se asigna el índice vigente; nunca se guarda entre cambios. |
| Un dispositivo listado no se puede abrir (p. ej. `Loopback` o un monitor) | El error aparece al dictar con el `ERROR` y la notificación de la SPEC 05/06; el usuario pulsa la tecla de cambio otra vez. Comprobar la apertura queda fuera de alcance. |
| Un dispositivo con 0 canales de entrada o virtual aparece en la rotación | Se filtra por `max_input_channels > 0`, igual que `--list-devices`; la rotación incluye lo que ese listado muestra. |
| La tecla `f8` choca con un atajo de la aplicación enfocada | `pynput` no consume la tecla; `--switch-key` permite cambiarla. |
| La sesión no es X11 y la tecla global no se detecta | Mismo aviso de arranque de la SPEC 05; no se añade comportamiento nuevo. |

## Lo que **no** está en esta spec

- Persistencia del dispositivo elegido entre ejecuciones.
- Cambio por stdin, señales, bandeja o menú gráfico.
- Retroceder, elegir por índice o nombre en caliente y listas de rotación configurables.
- Cambio automático al conectar, desconectar o fallar un dispositivo.
- Diferir el cambio hasta `IDLE`.
- Comprobar que el dispositivo abre al cambiarlo.
- Cambios en `Transcriber`, `inserter.py`, `notifier.py`, `log.py`, `capture_mic.py` y `benchmark_stt.py`.

Cada uno, si se aborda, va en su propia spec.
