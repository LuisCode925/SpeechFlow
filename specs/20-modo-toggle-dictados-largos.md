# SPEC 20 — Modo toggle para dictados largos

> **Estado:** Implementado
> **Depende de:** SPEC 05, SPEC 10, SPEC 12, SPEC 16, SPEC 19
> **Fecha:** 2026-10-09
> **Objetivo:** Añadir la clave `[recording] mode` (`"hold"` por defecto, o `"toggle"`) para que, en modo toggle, la tecla `record` empiece la grabación con una pulsación y la pare con la siguiente, permitiendo dictados largos sin mantener la tecla.

## Por qué existe esta spec

Hoy la grabación dura lo que dura la tecla pulsada (SPEC 05). En un dictado largo hay que mantener `ctrl_r` varios minutos, lo que cansa la mano y bloquea la combinación de teclas del resto del teclado. Es el ítem 4 del roadmap "Antes de la GUI" de `TODO.md`. El ciclo de estados (`IDLE` → `RECORDING` → `TRANSCRIBING`) y el filtro de repeticiones de tecla ya existen; solo cambia qué evento arranca y para la grabación.

## Alcance

**Dentro:**

- Clave nueva `[recording] mode` en `src/speechflow/config.py`: `str` con los valores `"hold"` (defecto, comportamiento actual) y `"toggle"`. Cualquier otro valor es inválido y nombra `recording.mode`.
- Campo `Config.mode: str = "hold"`, esquema `_SCHEMA["recording"]["mode"]`, validación del valor y línea de la plantilla de `write_emergency`.
- Parámetro `mode: str = "hold"` en `PushToTalk`, guardado como `self.mode`.
- Con `mode = "hold"`: ningún cambio.
- Con `mode = "toggle"`, tecla `record`:
  - Pulsar en `IDLE` empieza a grabar, con las mismas comprobaciones de hoy (micrófono desconectado, error al abrirlo) y la misma recarga del modelo descargado por inactividad (SPEC 12).
  - Pulsar en `RECORDING` para la grabación y lanza la transcripción por el mismo camino que soltar la tecla en `hold` (descarte por debajo de `min_seconds` incluido).
  - Pulsar en `TRANSCRIBING` registra un `WARNING` y no hace nada.
  - Soltar la tecla no hace nada.
  - Las repeticiones automáticas de la tecla mantenida se ignoran (una pulsación física = un cambio de estado).
- El límite `[recording] max_seconds` se aplica igual: al vencer, la grabación se corta y se transcribe lo grabado. Para dictados más largos, el usuario sube `max_seconds`.
- Mensaje de arranque: `Listo. Pulsa la tecla 'ctrl_r' para empezar a dictar y púlsala de nuevo para parar. Ctrl+C para salir.` en toggle; el actual (`Mantén pulsada ...`) en hold. La línea `Modelo: ...` no cambia.
- Actualizar tests (`tests/test_config.py`, `tests/test_push_to_talk.py`, `tests/test_app_helpers.py` si cubre el mensaje de arranque) y documentación (`speechflow.example.toml`, `README.md`, `TODO.md`, docstring de `app.py`).

**Fuera de alcance (para futuras specs):**

- Cambiar de modo en caliente con una tecla o guardarlo en `state.toml`; el modo se lee solo al arrancar.
- Opción de CLI (`--mode`); la clave del TOML basta.
- Tecla para cancelar una grabación toggle sin transcribirla.
- Límite de duración propio para toggle (`toggle_max_seconds`) o sin límite.
- Notificación de escritorio nueva al empezar o parar la grabación.
- Encolar un dictado nuevo mientras se transcribe el anterior.
- Combinaciones de varias teclas (entrada "Modo toggle y combinaciones de varias teclas" de `TODO.md`: solo se marca la parte del modo toggle).
- Parada automática de la grabación por silencio y streaming.

## Modelo de datos

Esta spec no introduce estructuras nuevas; añade un campo y una clave:

```python
# src/speechflow/config.py
@dataclass(frozen=True)
class Config:
    ...
    mode: str = "hold"   # [recording] mode; "hold" (mantener) o "toggle" (pulsar y pulsar)

_SCHEMA["recording"]["mode"] = ((str,), "mode")
RECORDING_MODES = ("hold", "toggle")
```

```toml
[recording]
# mode = "hold"          # "hold": graba mientras mantienes la tecla; "toggle": una pulsación empieza y otra para
```

```python
# src/speechflow/app.py
# PushToTalk.__init__(..., mode: str = "hold"); self.mode
```

Convenciones:

- `mode` distingue mayúsculas: `"Toggle"` es inválido.
- El valor se lee solo al arrancar; cambiarlo exige reiniciar.
- `_held` sigue filtrando repeticiones en ambos modos: se pone a `True` en la pulsación y a `False` al soltar.
- En toggle, `on_release` solo limpia `_held`; no detiene la grabación.
- La parada manual y la parada por `max_seconds` comparten `_stop_recording()`.

## Plan de implementación

1. En `config.py`, añadir `Config.mode`, `RECORDING_MODES`, la clave `mode` en `_SCHEMA["recording"]`, la validación del valor (error `recording.mode debe ser "hold" o "toggle", no ...`) y la línea de plantilla de `write_emergency`. Tests en `tests/test_config.py` (defecto `"hold"`, `"toggle"` válido, valor desconocido, `"Toggle"`, tipo incorrecto, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. En `app.py`, añadir el parámetro `mode` a `PushToTalk` y separar en `on_press` la lógica de arranque de la grabación en un método interno reutilizable, sin cambiar el comportamiento en `hold`. Verificar: `pytest` pasa sin cambios en los tests existentes.
3. En `app.py`, implementar el modo toggle en `on_press` y `on_release`: pulsar en `RECORDING` llama a `_stop_recording(False)`, pulsar en `TRANSCRIBING` registra el `WARNING`, soltar solo limpia `_held`. Tests en `tests/test_push_to_talk.py`: primera pulsación graba, segunda para y transcribe, soltar no para, repetición de tecla ignorada, pulsar transcribiendo da `WARNING` sin cambiar el estado, grabación corta descartada, corte por `max_seconds` seguido de pulsación sin romper el estado, y `hold` sin cambios. Verificar: `pytest tests/test_push_to_talk.py` pasa.
4. En `main()`: pasar `config.mode` a `PushToTalk` y elegir el mensaje `Listo. ...` según el modo. Test del mensaje. Verificar: `pytest` pasa y `speechflow` con `mode = "toggle"` graba con una pulsación y para con otra.
5. Documentar en `speechflow.example.toml`, `README.md` (sección de grabación y configuración) y el docstring de `app.py`, y marcar el ítem 4 de la Fase 3 y la parte de modo toggle de "Entrada y salida de texto" en `TODO.md`.

## Criterios de aceptación

- [ ] Sin `mode` en el TOML, mantener `ctrl_r` graba y soltarla transcribe, igual que antes.
- [ ] Con `mode = "toggle"`, una pulsación de `ctrl_r` registra `Grabando...` y soltarla no detiene la grabación.
- [ ] Con `mode = "toggle"`, la segunda pulsación registra `Grabación terminada: ...` e inserta el texto transcrito.
- [ ] Con `mode = "toggle"`, mantener la tecla pulsada produce un solo cambio de estado (se ignoran las repeticiones).
- [ ] Con `mode = "toggle"`, pulsar la tecla mientras se transcribe registra un `WARNING` y no inicia otra grabación.
- [ ] Con `mode = "toggle"`, dos pulsaciones separadas menos de `min_seconds` registran `Grabación de ... descartada` y no transcriben.
- [ ] Con `mode = "toggle"` y `max_seconds = 10`, una grabación sin segunda pulsación se corta a los 10 s y se transcribe.
- [ ] Con `mode = "toggle"` e `idle_timeout` con el modelo descargado, la primera pulsación graba al instante y recarga el modelo en paralelo.
- [ ] Con `mode = "toggle"`, las teclas de cambio de micrófono, de idioma y de modo automático siguen rechazadas con un `WARNING` mientras se graba.
- [ ] Con `mode = "toggle"` y el micrófono desconectado, la primera pulsación registra el `WARNING` de hoy y no graba.
- [ ] `mode = "pulsar"`, `mode = "Toggle"` o `mode = true` en el TOML hacen inválido el archivo con un mensaje que nombra `recording.mode`.
- [ ] El mensaje `Listo. ...` indica pulsar para empezar y pulsar de nuevo para parar en toggle, y mantener pulsada en hold.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `pytest` pasa con código 0 y no escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[recording] mode`.

## Decisiones

- **Sí:** clave `[recording] mode` leída al arrancar, por elección del usuario. Sin teclas nuevas ni persistencia en `state.toml`, y mantiene el atajo `record` que el usuario ya conoce.
- **No:** tecla en caliente para alternar el modo (patrón SPEC 08/19). Añade una tecla, una comprobación de duplicados y estado persistido para un ajuste que casi nunca cambia.
- **No:** segunda tecla `toggle` que conviva con `record`. Dos teclas para lo mismo y más choques posibles.
- **Sí:** `hold` como defecto. No cambia el comportamiento de quien ya usa la aplicación.
- **Sí:** el mismo `max_seconds` para ambos modos, por elección del usuario. Sin claves nuevas; el dictado largo se habilita subiendo el valor existente.
- **No:** `toggle_max_seconds` propio. Otra clave y otra validación sin datos que justifiquen dos límites.
- **No:** sin límite en toggle. Una pulsación olvidada llenaría la memoria con audio sin acotar.
- **Sí:** pulsar en `TRANSCRIBING` da un `WARNING` y se ignora, por elección del usuario. Es el mismo criterio que rechaza el cambio de micrófono o de idioma fuera de `IDLE`.
- **No:** encolar un dictado nuevo durante la transcripción. Cambia el modelo de estado y merece su propia spec.
- **Sí:** solo logs, sin notificación al empezar o parar, por elección del usuario. Evita ruido de escritorio en cada dictado.
- **No:** cancelar una grabación toggle, por elección del usuario. Las pulsaciones menores de `min_seconds` ya se descartan; una tecla de cancelar necesita su propia spec.
- **No:** `--mode` en la CLI. El TOML basta y evita otra precedencia que probar (mismo criterio que la SPEC 18 con `--no-vad`).
- **Sí:** reutilizar `_stop_recording()` para la parada manual. Descarte por duración mínima, vigilancia del micrófono y corte por `max_seconds` siguen funcionando sin código nuevo. Decisión del diseño.
- **Sí:** mantener el filtro `_held` en toggle. Sin él, la repetición automática de la tecla alternaría la grabación varias veces por pulsación. Decisión del diseño.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El usuario olvida que está grabando y no hay señal visual | La grabación se corta sola en `max_seconds` y se transcribe; el log muestra `Grabando...`. Una notificación o indicador queda para otra spec (bandeja, GUI). |
| Con el límite de 60 s por defecto, un dictado largo en toggle se corta sin avisar | El corte ya registra el `WARNING` de `max_seconds`; el README indica subir `[recording] max_seconds`. El texto de ese `WARNING` dice "suelta la tecla", que en toggle no aplica, así que se adapta al modo. |
| La repetición automática de la tecla activa y desactiva la grabación | Se mantiene el filtro `_held`, con un test de repetición. |
| Un cambio en `on_press` rompe el modo `hold` | El paso 2 refactoriza sin cambiar comportamiento y los tests existentes deben pasar sin modificarse. |
| Dictados largos tardan más en transcribirse y bloquean la tecla (`TRANSCRIBING`) | Aceptado: la pulsación en ese estado se ignora con `WARNING`; la latencia se mide en otra spec. |

## Lo que **no** está en esta spec

- Cambio de modo en caliente o persistido en `state.toml`.
- Opción `--mode` en la CLI.
- Cancelar una grabación toggle.
- Límite propio para toggle o grabación sin límite.
- Notificaciones nuevas al empezar o parar.
- Cola de dictados durante la transcripción.
- Combinaciones de varias teclas.
- Parada automática por silencio y streaming.

Cada uno, si se aborda, va en su propia spec.
