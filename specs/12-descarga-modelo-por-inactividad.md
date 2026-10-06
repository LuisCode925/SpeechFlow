# SPEC 12 — Descarga del modelo por inactividad y recarga bajo demanda

> **Estado:** Implementado
> **Depende de:** SPEC 04, SPEC 05, SPEC 06, SPEC 07, SPEC 10, SPEC 11
> **Fecha:** 2026-10-06
> **Objetivo:** Liberar el modelo de la GPU en `push_to_talk.py` tras `[model] idle_timeout` segundos sin uso y recargarlo al pulsar la tecla de grabar, sin perder lo que el usuario dicte durante la carga.

## Por qué existe esta spec

El script se ejecuta en segundo plano durante horas y el modelo `medium` ocupa VRAM de la GTX 1060 (6 GB) aunque no se dicte. Liberarla tras un rato sin uso permite a otros programas usar la GPU. El coste es la recarga (~5 s), por eso la grabación empieza al instante y la carga corre en paralelo. La SPEC 06 dejó fuera esta función.

## Alcance

**Dentro:**

- Clave nueva `[model] idle_timeout` en la configuración (SPEC 10): segundos de inactividad antes de liberar el modelo. Defecto `0.0` (desactivado). Un valor distinto de cero debe ser mayor o igual que `30.0`.
- Con `idle_timeout = 0`, el comportamiento es idéntico al actual.
- Un temporizador propio (`threading.Timer`, `daemon`) en `PushToTalk`. Se arma al volver a `IDLE` con el modelo cargado y se cancela al empezar a grabar.
- La inactividad cuenta desde que `PushToTalk` vuelve a `IDLE`: tras una transcripción, tras una grabación descartada por corta o tras una recarga fallida.
- Al vencer el temporizador, bajo `self._lock`: si el estado sigue en `IDLE` y el modelo está cargado, se llama a `Transcriber.close()` y se deja `self.transcriber = None`.
- Recarga bajo demanda: si se pulsa la tecla de grabar con el modelo descargado y el micrófono abre bien, la grabación empieza ya y un hilo carga el modelo en paralelo. Al soltar la tecla, la transcripción espera a que termine la carga.
- Si la recarga falla: `ERROR` y notificación de error, se descarta el audio, el estado vuelve a `IDLE` y la siguiente pulsación reintenta la carga.
- Con el modelo descargado, el micrófono se abre antes de lanzar la carga; si el micrófono falla, no se carga nada.
- Avisos solo por consola en el ciclo de inactividad (descarga y recarga). Se mantienen las notificaciones de error y las de arranque y salida de la SPEC 06.
- Al salir con `Ctrl+C`: si hay una carga en curso, se espera a que termine; si el modelo está cargado, se libera como hoy (`Modelo {modelo} liberado.` y notificación `Modelo liberado`); si ya estaba descargado, no se repite el aviso de liberación.
- Actualizar `speechflow.example.toml`, la plantilla de emergencia, `README.md`, el docstring del script y `TODO.md`.

**Fuera de alcance (para futuras specs):**

- Carga perezosa en el arranque (la carga inicial sigue siendo inmediata).
- Opción de CLI `--idle-timeout`.
- Notificaciones de escritorio para la descarga y la recarga por inactividad.
- Descargar por otros criterios (VRAM libre, bloqueo de pantalla, suspensión).
- Esperar a una transcripción en curso al salir y liberar el modelo en señales distintas de `Ctrl+C` (siguen pendientes de la SPEC 06).
- Cambios en `Transcriber`, `audio.py`, `inserter.py`, `notifier.py`, `log.py`, `capture_mic.py` y `benchmark_stt.py`.
- Cambiar de modelo o idioma en la recarga.

## Modelo de datos

```python
# src/speechflow/config.py
@dataclass(frozen=True)
class Config:
    ...
    idle_timeout: float = 0.0     # [model] idle_timeout, en segundos; 0 = desactivado
```

```toml
[model]
# idle_timeout = 0.0   # segundos sin dictar antes de liberar el modelo; 0 desactiva; mínimo 30.0
```

```python
# scripts/push_to_talk.py
class PushToTalk:
    transcriber: Transcriber | None         # None = modelo descargado
    idle_timeout: float
    language: str                           # para recargar; antes se leía de transcriber.language
    _idle_timer: threading.Timer | None
    _loader: threading.Thread | None        # hilo de recarga en curso
    _load_error: Exception | None           # fallo de la última recarga

    def _arm_idle_timer(self) -> None: ...  # bajo el lock; no hace nada si idle_timeout == 0 o no hay modelo
    def _unload_model(self) -> None: ...    # callback del temporizador
    def _load_model(self) -> None: ...      # cuerpo del hilo de recarga
```

Convenciones:

- `transcriber`, `_idle_timer`, `_loader` y `_load_error` se leen y escriben solo bajo `self._lock`.
- `_arm_idle_timer()` cancela el temporizador anterior antes de crear otro. Se llama al volver a `IDLE` (en `_stop_recording()` al descartar, en `_transcribe_and_insert()` y tras una recarga fallida).
- `on_press()` cancela el temporizador al pasar a `RECORDING`.
- El temporizador no se arma ni dispara con el estado `RECORDING` o `TRANSCRIBING`.
- `_unload_model()` no hace nada si el estado ya no es `IDLE` o `transcriber` es `None`.
- La transcripción del audio espera con `self._loader.join()` fuera del lock; después lee `self._load_error`.
- Validación de la clave: `idle_timeout` debe ser número (no `bool`) y valer `0` o al menos `30.0`; si no, `ConfigError` con `model.idle_timeout` en el mensaje.
- Mensajes de consola:
  - `INFO` `Modelo {modelo} liberado por inactividad ({N:g} s sin uso).`
  - `INFO` `Modelo descargado: se carga {modelo} mientras grabas.`
  - Al cargar se reutilizan las líneas de la SPEC 07: `Cargando {modelo} (int8, GPU)...` y `Modelo cargado en {s} s (incluye calentamiento)`.
  - `ERROR` `Error al recargar el modelo: {error}`.
- Notificaciones de escritorio, título `SpeechFlow`: solo `Error al recargar el modelo: {error}`. La descarga y la recarga con éxito no notifican.
- La línea `Listo. ...` y la tabla de opciones del README no cambian.

## Plan de implementación

1. En `src/speechflow/config.py`, añadir `Config.idle_timeout`, su entrada en `_SCHEMA` (`model.idle_timeout`), la validación y la línea de la plantilla de emergencia; documentar la clave en `speechflow.example.toml`. Verificar: un TOML con `idle_timeout = 60` devuelve `60.0`; `0` devuelve `0.0`; `10`, `-1`, `"60"` y `true` lanzan `ConfigError` con `model.idle_timeout`; la plantilla de emergencia incluye la clave.
2. En `scripts/push_to_talk.py`, extraer la carga del modelo de `main()` a una función `load_transcriber(model, language)` que registra las líneas `Cargando ...` y `Modelo cargado en ...` y devuelve el `Transcriber`. `main()` la usa en el arranque y el comportamiento no cambia. Verificar: el arranque imprime las mismas líneas y notificaciones que antes y un dictado funciona.
3. Pasar `idle_timeout` y `language` a `PushToTalk`, hacer `transcriber` opcional y añadir `_arm_idle_timer()` y `_unload_model()`, armados al volver a `IDLE` y cancelados al pulsar. Con `idle_timeout = 0`, no se crea ningún temporizador. Verificar: con `idle_timeout = 30` y sin dictar, a los 30 s aparece `Modelo medium liberado por inactividad (30 s sin uso).` y `nvidia-smi` muestra la VRAM del proceso reducida; un dictado antes de los 30 s reinicia la cuenta.
4. Añadir la recarga bajo demanda: en `on_press()`, con `transcriber is None` y el micrófono abierto, lanzar `_load_model()` en un hilo; en `_transcribe_and_insert()`, esperar al hilo y comprobar `_load_error`. Verificar: tras una descarga, pulsar la tecla graba al instante, aparecen `Cargando medium (int8, GPU)...` y `Modelo cargado en ...`, y al soltar el texto se inserta. Soltar antes de que acabe la carga espera y transcribe igualmente.
5. Añadir el camino de error: si la carga falla, `ERROR` + notificación, audio descartado, estado `IDLE`, `transcriber` sigue en `None` y la siguiente pulsación reintenta. Verificar: forzando un fallo (p. ej. `model = "no-existe"` tras descargar el modelo), el script no se cae, avisa una vez por intento y se recupera al reintentar.
6. Ajustar la salida en `main()`: esperar al hilo de carga si lo hay, cancelar el temporizador, y liberar el modelo y notificar solo si está cargado. Verificar: `Ctrl+C` con el modelo cargado se comporta como antes; con el modelo descargado imprime `Saliendo.` y no `Modelo ... liberado.`; `Ctrl+C` durante una recarga termina limpio.
7. Actualizar `README.md` (clave `idle_timeout`, comportamiento y mensajes), el docstring del script y marcar en `TODO.md` el ítem de descarga por inactividad. Verificar: el README coincide con la salida real.

## Criterios de aceptación

- [ ] `[model] idle_timeout` acepta `0` o números mayores o iguales que `30.0`; el defecto es `0.0`.
- [ ] `10`, `-1`, un texto o un booleano terminan en el camino de configuración inválida de la SPEC 10 con `model.idle_timeout` en la causa.
- [ ] `speechflow.example.toml` y la plantilla de emergencia incluyen `idle_timeout`.
- [ ] Con `idle_timeout = 0`, el modelo nunca se libera por inactividad y no se crea ningún temporizador.
- [ ] Con `idle_timeout = N`, tras `N` s en `IDLE` sin dictar se registra `Modelo {modelo} liberado por inactividad ({N:g} s sin uso).` y la VRAM del proceso baja.
- [ ] La descarga por inactividad no envía ninguna notificación de escritorio.
- [ ] Un dictado completo reinicia la cuenta de inactividad desde que termina la transcripción.
- [ ] Una grabación descartada por corta también reinicia la cuenta.
- [ ] El modelo no se libera durante `RECORDING` ni `TRANSCRIBING`.
- [ ] Con el modelo descargado, pulsar la tecla de grabar empieza a grabar de inmediato y lanza la carga en paralelo.
- [ ] Un dictado hecho con el modelo descargado se transcribe e inserta completo, incluido lo hablado durante la carga.
- [ ] La recarga con éxito no envía ninguna notificación de escritorio y registra las líneas `Cargando ...` y `Modelo cargado en ...`.
- [ ] Si el micrófono falla al abrir con el modelo descargado, no se inicia la carga.
- [ ] Si la recarga falla, se registra `Error al recargar el modelo: ...`, se envía la notificación de error, se descarta el audio, el script sigue vivo y la siguiente pulsación reintenta la carga.
- [ ] `Ctrl+C` con el modelo cargado libera el modelo, notifica `Modelo liberado` y termina como antes.
- [ ] `Ctrl+C` con el modelo descargado termina sin repetir `Modelo ... liberado.` ni la notificación.
- [ ] `Ctrl+C` durante una recarga espera a que termine la carga y sale sin colgarse ni excepciones.
- [ ] El arranque sigue cargando el modelo de inmediato, con los mismos mensajes y notificaciones de las SPEC 06 y 07.
- [ ] La vigilancia del micrófono (SPEC 11) y el cambio de entrada (SPEC 08) funcionan igual con el modelo descargado.
- [ ] `--list-devices`, `capture_mic.py` y `benchmark_stt.py` producen la misma salida que antes.
- [ ] `README.md` documenta `idle_timeout`, el ciclo de descarga y recarga, y los mensajes nuevos.

## Decisiones

- **Sí:** `[model] idle_timeout` en el archivo de configuración, por elección del usuario. Sigue la SPEC 10 y no añade superficie de CLI.
- **Sí:** defecto `0` (desactivado), por elección del usuario. No cambia el comportamiento de quien no lo pida.
- **No:** defecto activo (600 s). Cambiaría el comportamiento actual de todos.
- **No:** opción `--idle-timeout`. Más superficie para el mismo efecto; se puede añadir después.
- **Sí:** mínimo de `30.0` s para valores distintos de cero. Evita ciclos de descarga y recarga continuos (cada recarga cuesta ~5 s). El valor lo fija esta spec.
- **Sí:** grabar al instante y cargar en paralelo, por elección del usuario. El usuario no habla al vacío ni pierde palabras.
- **No:** ignorar la pulsación hasta cargar, o empezar a grabar solo al terminar la carga. Ambas obligan a esperar ~5 s antes de hablar.
- **Sí:** la inactividad cuenta desde que `PushToTalk` vuelve a `IDLE`, por elección del usuario. Un dictado largo o una transcripción lenta no cuentan como inactividad.
- **Sí:** una grabación descartada por corta cuenta como uso. El usuario sigue interactuando con el script.
- **No:** contar la tecla de cambio como actividad. El cambio de micrófono no indica intención de dictar inmediatamente.
- **Sí:** solo consola para la descarga y la recarga por inactividad, por elección del usuario. Evita notificaciones durante el uso normal. Se mantienen la notificación de error y las de arranque y salida de la SPEC 06.
- **Sí:** temporizador propio con `threading.Timer`, por elección del usuario. Precisión exacta; no acopla esta función al hilo vigilante de la SPEC 11.
- **No:** ampliar el hilo vigilante del micrófono. Tendría precisión de `watch_interval` s y mezclaría dos responsabilidades.
- **Sí:** ante un fallo de recarga, `ERROR` + notificación, descartar el audio y reintentar en la siguiente pulsación, por elección del usuario. Un fallo transitorio de VRAM no debe matar el proceso.
- **No:** salir con código 1 tras un fallo de recarga.
- **Sí:** la carga inicial al arrancar no cambia, por elección del usuario. La carga perezosa altera los avisos de las SPEC 06 y 07 y va en otra spec.
- **Sí:** al salir, esperar a una recarga en curso. Si no, el hilo de carga podría dejar el modelo en la GPU tras terminar el proceso principal.
- **Sí:** `Transcriber` no cambia. `close()` y un nuevo `Transcriber(...)` bastan para descargar y recargar.
- **Sí:** esta spec cubre el ítem "Descarga del modelo por inactividad y recarga bajo demanda" del `TODO.md` (origen SPEC 06).

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `close()` y `gc.collect()` no devuelven toda la VRAM (caché de CUDA/ctranslate2) | El paso 3 mide con `nvidia-smi`; la SPEC 06 ya verificó que `close()` libera la GPU. Si queda memoria residual, se documenta en el README. |
| Carrera entre el temporizador y una pulsación | `_unload_model()` comprueba estado y `transcriber` bajo `self._lock`; `on_press()` cancela el temporizador y cambia a `RECORDING` bajo el mismo lock. |
| Soltar la tecla antes de acabar la recarga bloquea el hilo del listener | La espera `join()` ocurre en el hilo de transcripción, no en el del listener. |
| La recarga compite por VRAM con otro proceso que tomó la memoria liberada | Camino de error del paso 5: aviso, audio descartado y reintento. Es el coste de liberar la GPU. |
| Una recarga lenta con audios cortos ofrece peor latencia que antes | Aceptado: la latencia extra (~5 s) solo se paga tras la inactividad. Con `idle_timeout = 0` no existe. |
| `Ctrl+C` durante la carga tarda lo que tarde la carga | Aceptado: es poco habitual y evita dejar VRAM ocupada. |
| Una descarga en medio de un cambio de micrófono (`switch_device()`) | Ambas operaciones toman `self._lock`; no se solapan. |

## Lo que **no** está en esta spec

- Carga perezosa del modelo al arrancar.
- Opción `--idle-timeout` de CLI.
- Notificaciones de escritorio para la descarga y la recarga por inactividad.
- Descarga por criterios distintos del tiempo de inactividad.
- Esperar a una transcripción en curso al salir, y liberar el modelo en señales distintas de `Ctrl+C`.
- Cambiar de modelo o idioma en la recarga.

Cada uno, si se aborda, va en su propia spec.
