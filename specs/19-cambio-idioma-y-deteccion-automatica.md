# SPEC 19 — Cambio de idioma en caliente y detección automática

> **Estado:** Aprobado
> **Depende de:** SPEC 04, SPEC 05, SPEC 08, SPEC 10, SPEC 12, SPEC 16, SPEC 18
> **Fecha:** 2026-10-09
> **Objetivo:** Añadir dos teclas globales en `[keys]` (`language`, defecto `f7`, alterna es↔en; `auto`, defecto `f6`, activa o desactiva la detección automática restringida a es/en) que cambian el idioma de la transcripción en caliente y lo guardan en `state.toml`.

## Por qué existe esta spec

Hoy el idioma se fija al arrancar (`--language` o `[model] language`) y cambiarlo exige reiniciar la aplicación y recargar el modelo. Quien dicta en español e inglés tiene que elegir un idioma por sesión, y Whisper traduce o deforma lo que no está en ese idioma. El cambio de entrada de audio en caliente (SPEC 08) ya fijó el patrón: una tecla global, solo en reposo, con log, notificación y persistencia. Es el ítem 2 del roadmap "Antes de la GUI" de `TODO.md`.

## Alcance

**Dentro:**

- Dos claves nuevas en `[keys]`: `language` (defecto `"f7"`) y `auto` (defecto `"f6"`), con el mismo formato que `record` y `switch` (nombre de `pynput.keyboard.Key` o un carácter).
- Campos `Config.language_key` y `Config.auto_key` en `src/speechflow/config.py`, con esquema y plantilla de `write_emergency`.
- Las cuatro teclas (`record`, `switch`, `language`, `auto`) deben ser distintas entre sí; si no, `main()` registra un `ERROR` y sale con código 1, como hoy con `--key` y `--switch-key`.
- `language` acepta el valor especial `"auto"` en `[model] language` y en `--language`, sin cambiar la validación del resto de valores (cualquier texto sigue siendo válido).
- Tecla `language`, solo con el estado en `IDLE`:
  - Idioma fijo `es` → `en`; `en` → `es`; cualquier otro (por ejemplo `fr`) → `es`.
  - En modo auto: sale de auto y fija el otro idioma respecto al último fijo (último `es` → `en`; último `en` → `es`; otro → `es`).
- Tecla `auto`, solo con el estado en `IDLE`: de idioma fijo pasa a auto (recordando ese idioma como "último fijo"); de auto vuelve al último fijo.
- Último fijo inicial: si se arranca en auto, es `es` (`DEFAULT_LANGUAGE`); no se guarda en `state.toml`.
- Modo auto: `Transcriber` detecta el idioma de cada dictado con `WhisperModel.detect_language()`, elige el de mayor probabilidad entre `es` y `en` y transcribe con ese idioma.
- `Transcriber.transcribe(audio, language=None)`: el idioma deja de ser fijo en el objeto; `None` usa `self.language`, y `"auto"` activa la detección. `Transcriber` guarda `last_language` (el idioma realmente usado en la última llamada) para el log.
- Calentamiento: además de las llamadas actuales, una llamada a `detect_language()` sobre el segundo de silencio, para que activar auto en caliente no añada latencia al primer dictado.
- `PushToTalk.language` pasa a mutable; la recarga tras la descarga por inactividad (SPEC 12) usa el idioma vigente, incluido `"auto"`.
- Persistencia: `state.toml` guarda `language` (incluido `"auto"`) junto a `device`, sin pisarse entre sí. Precedencia: CLI `--language` > `state.toml` > `[model] language` > defecto.
- Mensajes: `INFO` y notificación al cambiar; `WARNING` si se pulsa grabando o transcribiendo; `WARNING` si no se puede guardar el estado (no impide el cambio).
- El log `Grabación terminada: ... Transcribiendo con {modelo}/{idioma}...` y `Insertado (...)` / `Sin texto reconocido (...)` muestran `auto→es` o `auto→en` cuando se detectó el idioma.
- Línea de arranque: `Cambio de idioma: tecla 'f7'; modo automático: tecla 'f6'.` y `idioma: auto` en la línea `Modelo: ...`.
- Actualizar tests (`tests/test_config.py`, `tests/test_transcriber.py`, `tests/test_push_to_talk.py`, `tests/test_app_helpers.py`) y documentación (`speechflow.example.toml`, `README.md`, `TODO.md`).

**Fuera de alcance (para futuras specs):**

- Lista de idiomas de rotación o de detección configurable (`[model] languages = [...]`); el conjunto es fijo, `{es, en}`.
- Detección libre entre los ~99 idiomas de Whisper y umbral de confianza con respaldo.
- Opciones de CLI para las teclas nuevas (`--language-key`, `--auto-key`); solo existen en el TOML.
- Cambiar de idioma durante una grabación o una transcripción, o diferir el cambio hasta `IDLE`.
- Detección por segmentos dentro de un mismo dictado (mezclar es y en en una frase).
- Guardar en `state.toml` el último idioma fijo.
- Cambiar el modelo (`small`, `medium`, ...) en caliente.
- Canal de control por socket o señales para cambiar el idioma (ítem 10 del roadmap).
- Cambios en `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.

## Modelo de datos

```python
# src/speechflow/config.py
@dataclass(frozen=True)
class Config:
    ...
    language_key: str = "f7"   # [keys] language; alterna es <-> en
    auto_key: str = "f6"       # [keys] auto; activa o desactiva la detección automática

_SCHEMA["keys"]["language"] = ((str,), "language_key")
_SCHEMA["keys"]["auto"] = ((str,), "auto_key")

def load_state_language() -> str | None: ...        # "es", "en", "auto", ...; None si falta o es inválido
def save_state_language(language: str) -> None: ... # conserva `device` ya guardado
```

```toml
# state.toml (el archivo ya existente, ahora con dos claves)
device = "Realtek ALC1220"
language = "auto"
```

```toml
# config.toml
[model]
# language = "es"        # "es", "en", otro idioma de Whisper, o "auto" (detecta entre es y en en cada dictado)

[keys]
# language = "f7"        # alterna es <-> en en caliente; distinta de record, switch y auto
# auto = "f6"            # activa o desactiva la detección automática de idioma
```

```python
# src/speechflow/transcriber.py
AUTO_LANGUAGE = "auto"
AUTO_CANDIDATES = ("es", "en")

class Transcriber:
    last_language: str | None   # idioma usado en la última llamada a transcribe()
    def transcribe(self, audio, language: str | None = None) -> tuple[str, float]: ...

# src/speechflow/app.py
# PushToTalk: self.language (mutable), self._last_fixed_language, self.language_key, self.auto_key
```

Convenciones:

- `"auto"` es un valor literal en minúsculas; `"Auto"` se trata como un idioma desconocido y Whisper lo rechazará al transcribir, igual que cualquier otro valor inexistente hoy.
- La firma de `Transcriber.transcribe()` sigue devolviendo `(texto, segundos)`; el idioma detectado se lee de `transcriber.last_language`.
- En modo auto, los `segundos` devueltos incluyen la detección.
- El cambio de idioma funciona también con el modelo descargado (SPEC 12): solo modifica `PushToTalk.language`; el modelo recargado usa el valor vigente.
- Estado guardado inválido (`language` que no es texto o está vacío): se ignora con `WARNING`, como `device` hoy.
- `save_state_device` y `save_state_language` leen el archivo actual, cambian su clave y reescriben ambas con archivo temporal + `os.replace`; un `state.toml` ilegible se sobrescribe solo con la clave que se guarda.

## Plan de implementación

1. En `config.py`, añadir `language_key`, `auto_key`, las claves de `_SCHEMA["keys"]` y las líneas de la plantilla de `write_emergency`. Tests en `tests/test_config.py` (valores por defecto, válidos, tipo incorrecto, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. En `config.py`, añadir `load_state_language()` y `save_state_language()`, y hacer que `save_state_device()` conserve `language` (y viceversa). Tests: guardar uno no borra el otro, valor inválido se ignora, archivo ilegible. Verificar: `pytest tests/test_config.py` pasa.
3. En `transcriber.py`, añadir `AUTO_LANGUAGE`, `AUTO_CANDIDATES`, el parámetro `language` de `transcribe()`, `last_language` y la llamada de calentamiento a `detect_language()`. Tests con `WhisperModelFalso` ampliado con `detect_language`: idioma explícito, idioma por defecto, `"auto"` elige `es` o `en` según las probabilidades (aunque otro idioma tenga la mayor), `last_language` se actualiza. Verificar: `pytest tests/test_transcriber.py` pasa.
4. En `app.py`, hacer mutable `PushToTalk.language`, pasarlo a `transcribe()` y usar `last_language` en los logs `Transcribiendo con ...` e `Insertado (...)`. Sin teclas nuevas todavía. Actualizar los tests de `PushToTalk`. Verificar: `pytest` pasa y `speechflow --language en` dicta como antes.
5. En `app.py`, añadir `language_key` y `auto_key` a `PushToTalk`, sus indicadores de tecla mantenida, `switch_language()` y `toggle_auto()` (solo en `IDLE`, con log, notificación y `save_state_language`). Tests: rotación es→en→es, `fr`→`es`, auto→último fijo, tecla de idioma desde auto, rechazo grabando o transcribiendo, repeticiones de tecla ignoradas, fallo de `save_state_language` no impide el cambio. Verificar: `pytest tests/test_push_to_talk.py` pasa.
6. En `main()`: leer `config.language_key` y `config.auto_key`, comprobar que las cuatro teclas son distintas, aplicar la precedencia `--language` > estado > `[model] language`, validar `state.toml` y ampliar las líneas de arranque. Tests de la precedencia y del choque de teclas. Verificar: `pytest` pasa y `speechflow` arranca mostrando las dos teclas.
7. Documentar en `speechflow.example.toml` y `README.md` (teclas, modo auto, `--language auto`, `state.toml`) y marcar el ítem 2 de la Fase 3 y las dos entradas de "Transcripción" en `TODO.md`.

## Criterios de aceptación

- [ ] Con el script en reposo, pulsar `f7` pasa de `es` a `en`, registra el cambio por `INFO` y envía una notificación de escritorio.
- [ ] Pulsar `f7` de nuevo vuelve a `es`.
- [ ] Con `language = "fr"`, pulsar `f7` fija `es`.
- [ ] Pulsar `f6` en idioma fijo activa el modo auto; pulsar `f6` otra vez vuelve al idioma fijo anterior.
- [ ] Estando en auto, `f7` desactiva auto y fija el otro idioma respecto al último fijo.
- [ ] En modo auto, un dictado en inglés se transcribe en inglés y uno en español, en español; el log muestra `auto→en` o `auto→es`.
- [ ] En modo auto, `Transcriber` nunca devuelve un idioma distinto de `es` o `en`, aunque otro tenga la mayor probabilidad.
- [ ] Pulsar `f7` o `f6` mientras se graba o se transcribe registra un `WARNING`, no cambia el idioma y no envía notificación.
- [ ] Mantener pulsada `f7` o `f6` cambia el idioma una sola vez (se ignoran las repeticiones automáticas).
- [ ] Tras un cambio con `f7` o `f6`, `state.toml` contiene `language` y conserva `device`; y tras un cambio de micrófono conserva `language`.
- [ ] Al reiniciar sin `--language`, el idioma arranca con el valor de `state.toml`, aunque `[model] language` sea distinto.
- [ ] `--language en` gana sobre `state.toml` y sobre `[model] language`.
- [ ] `speechflow --language auto` y `language = "auto"` arrancan en modo auto, y la línea `Modelo: ...` muestra `idioma: auto`.
- [ ] Con `idle_timeout` y el modelo descargado, `f7` cambia el idioma, y el modelo recargado en la siguiente pulsación usa el idioma vigente.
- [ ] Dos de las cuatro teclas iguales (`record`, `switch`, `language`, `auto`) hacen salir con código 1 y un `ERROR` que nombra las teclas.
- [ ] Una tecla `language` o `auto` desconocida sale con código 1 y un `ERROR` que nombra la clave.
- [ ] `[keys] language = 1` en el TOML hace inválido el archivo con un mensaje que nombra `keys.language`.
- [ ] Una grabación sin voz en modo auto sigue el camino de `Sin texto reconocido` sin lanzar excepciones.
- [ ] Un fallo al guardar `state.toml` registra un `WARNING`, pero el idioma cambia igualmente.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `pytest` pasa con código 0 y no escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[keys] language`, `[keys] auto`, `language = "auto"` y el nuevo contenido de `state.toml`.

## Decisiones

- **Sí:** dos teclas (idioma y auto), por elección del usuario. Cada una hace una sola cosa y no hay ciclo de tres estados que explicar.
- **No:** una sola tecla en ciclo es → en → auto. Más compacta, pero el usuario prefirió separar auto.
- **Sí:** `language = "auto"` como valor del campo existente y no una clave booleana aparte, por elección del usuario. Un solo campo, sin combinaciones inválidas y `--language auto` sin flag nuevo.
- **No:** `[model] auto = true`. Dos campos que combinar y más validación.
- **Sí:** detección restringida a es/en, por elección del usuario. Con frases cortas o ruido, Whisper libre devuelve idiomas inesperados; elegir entre dos candidatos con `detect_language()` da un resultado estable.
- **No:** detección libre. Sin código extra, pero falla con dictados cortos.
- **No:** respaldo con umbral de confianza. Añade un parámetro y lógica por valores sin medir.
- **Sí:** en auto, la tecla de idioma sale de auto y fija el otro idioma, por elección del usuario. La tecla siempre produce un cambio visible.
- **No:** ignorar la tecla de idioma en auto. Más predecible, pero obliga a un paso más.
- **Sí:** con un idioma fuera de {es, en}, la tecla de idioma pasa a `es`, por elección del usuario. No restringe la validación de `language` y la rotación sigue siendo corta y fija.
- **No:** lista de idiomas configurable. Amplía el alcance (validación, detección restringida a la lista) y merece su propia spec.
- **Sí:** persistir `language` en `state.toml`, con la precedencia CLI > estado > `[model] language` > defecto, por elección del usuario. Es la misma que ya tiene el micrófono; el efecto secundario es que una edición posterior de `[model] language` no se nota mientras exista `language` en el estado, y se documenta en el README.
- **No:** guardar el último idioma fijo. Un campo más en el estado para un caso raro; arrancar en auto usa `es` como último fijo. Decisión del diseño.
- **Sí:** log y notificación al cambiar, solo en `IDLE`, por elección del usuario. Mismo comportamiento y mismas garantías que la tecla de cambio de entrada de audio (SPEC 08).
- **No:** cambiar durante la transcripción. Complica el estado y haría que la línea de log `Transcribiendo con ...` mintiera.
- **Sí:** teclas por defecto `f7` (idioma) y `f6` (auto), por elección del usuario. Contiguas a `f8` (cambio de micrófono) y sin choque con `ctrl_r`.
- **No:** opciones de CLI para las teclas nuevas, por elección del usuario. El TOML basta y evita más precedencia que probar.
- **Sí:** `transcribe(audio, language=None)` en lugar de recrear el `Transcriber` al cambiar. El idioma es un parámetro de la llamada a Whisper, no del modelo cargado; recrearlo costaría segundos de GPU. Decisión del diseño.
- **Sí:** `last_language` en el `Transcriber` para el log. Mantiene el contrato `(texto, segundos)` de las SPEC 16 y 18. Decisión del diseño.
- **Sí:** `detect_language()` también en el calentamiento. Sin eso, el primer dictado tras activar auto en caliente pagaría la primera pasada del codificador de idioma. Decisión del diseño.
- **Sí:** `PushToTalk.language` como fuente de verdad del idioma (ya guardaba una copia para recargar). Funciona con el modelo descargado. Decisión del diseño.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `detect_language()` falla o devuelve algo inesperado con audio sin voz (por ejemplo, con `vad_filter=True` y sin segmentos) | Se prueba en un test con audio de silencio; si lanza o no devuelve probabilidades, se usa el último idioma fijo del `Transcriber` y la transcripción sigue el camino de `Sin texto reconocido`. |
| La detección añade latencia a cada dictado en auto | Una pasada del codificador sobre 30 s máximos de audio; los `segundos` del log la incluyen para poder medirla. Si resulta lenta, se ajusta en otra spec con datos. |
| La detección confunde es y en con frases muy cortas | El usuario puede fijar el idioma con `f7`; aceptado. |
| `state.toml` con `language` antiguo gana sobre un `[model] language` nuevo y desconcierta | Documentado en el README; para volver al valor del TOML basta borrar la clave del estado. |
| `save_state_device` actual reescribe el archivo solo con `device` y borraría `language` | El paso 2 lo cambia a leer–modificar–escribir y lo prueba en ambos sentidos. |
| Las teclas `f6` y `f7` chocan con atajos de otras aplicaciones | Son configurables en `[keys]`; el choque con `record` y `switch` se detecta al arrancar. |
| Los tests existentes asumen `language` fijo en `Transcriber` y en `PushToTalk` | Los pasos 3 y 4 actualizan `WhisperModelFalso` y los dobles de `PushToTalk`. |

## Lo que **no** está en esta spec

- Lista de idiomas de rotación o detección configurable.
- Detección libre de cualquier idioma y umbrales de confianza.
- Opciones de CLI para las teclas nuevas.
- Cambio de idioma durante la grabación o la transcripción.
- Detección por segmentos dentro de un mismo dictado.
- Guardar el último idioma fijo en `state.toml`.
- Cambio de modelo en caliente.
- Canal de control (socket o señales).
- Cambios en `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.

Cada uno, si se aborda, va en su propia spec.
