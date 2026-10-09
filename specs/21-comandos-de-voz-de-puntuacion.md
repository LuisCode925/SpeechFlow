# SPEC 21 — Comandos de voz de puntuación

> **Estado:** Implementado
> **Depende de:** SPEC 04, SPEC 10, SPEC 16, SPEC 19
> **Fecha:** 2026-10-09
> **Objetivo:** Añadir la clave `[text] punctuation_commands` (activada por defecto) y un módulo `punctuation.py` que sustituye, tras transcribir y antes de insertar, palabras dictadas como "punto", "coma" o "nueva línea" (y sus equivalentes en inglés) por el signo o salto correspondiente.

## Por qué existe esta spec

Whisper puntúa por su cuenta, pero sin control: quien dicta no decide dónde va un punto, un salto de línea o un paréntesis. Es el ítem 7 del roadmap "Antes de la GUI" de `TODO.md`. La transcripción no cambia; solo se añade un posprocesado puro entre `Transcriber.transcribe()` e `insert_text()`, que depende del idioma realmente usado en el dictado (`Transcriber.last_language`, SPEC 19).

## Alcance

**Dentro:**

- Módulo nuevo `src/speechflow/punctuation.py` con `apply_voice_punctuation(text: str, language: str) -> str`, función pura sin dependencias de audio, GPU ni `pynput`.
- Vocabulario fijo en español e inglés, elegido por el idioma usado en el dictado (`transcriber.last_language`, que en modo auto es `es` o `en`). Con cualquier otro idioma (por ejemplo `fr`) el texto no se toca, ni siquiera la mayúscula inicial.
- Tabla de comandos (se ignoran mayúsculas, acentos de Whisper en mayúscula inicial y la puntuación que Whisper pegue a las palabras del comando):

  | Resultado | Español | Inglés |
  | --- | --- | --- |
  | `.` | `punto` | `period` |
  | `,` | `coma` | `comma` |
  | `;` | `punto y coma` | `semicolon` |
  | `:` | `dos puntos` | `colon` |
  | `?` | `interrogación`, `cerrar interrogación` | `question mark` |
  | `¿` | `abrir interrogación` | — |
  | `!` | `exclamación`, `cerrar exclamación` | `exclamation mark` |
  | `¡` | `abrir exclamación` | — |
  | `...` | `puntos suspensivos` | `ellipsis` |
  | `\n` | `nueva línea` | `new line` |
  | `\n\n` | `nuevo párrafo` | `new paragraph` |
  | `(` | `abrir paréntesis` | `open parenthesis` |
  | `)` | `cerrar paréntesis` | `close parenthesis` |
  | `"` (apertura) | `abrir comillas` | `open quote` |
  | `"` (cierre) | `cerrar comillas` | `close quote` |
  | `-` | `guion` | `dash` |

- Coincidencia por la frase más larga: `punto y coma` gana a `punto`, y `dos puntos` a `puntos suspensivos` o a `punto`.
- Palabra de escape: `literal` (es) o `literally` (en) justo delante de un comando lo deja como palabra normal y se descarta; no afecta a más de una palabra. Si no precede a un comando, `literal` se conserva. No hay forma de escribir `literal` seguido de un comando.
- Espaciado: sin espacio antes de `. , ; : ? ! ...` ni antes de `)` y del `"` de cierre; sin espacio después de `¿ ¡ (` y del `"` de apertura; sin espacios alrededor de `\n`. El guion lleva un espacio a cada lado.
- Puntuación propia de Whisper: la que Whisper pegue a las palabras del comando se descarta (`Punto.` o `coma,` valen igual que `punto`). Además, si el comando es `. , ; : ? ! ...`, se descarta también la puntuación final pegada a la palabra inmediatamente anterior (`Hola, coma` no produce `Hola,,`).
- Mayúsculas: la primera letra del texto y la primera letra tras `.`, `?`, `!`, `\n` y `\n\n` se ponen en mayúscula. La marca de mayúscula pendiente atraviesa signos de apertura (`¿ ¡ ( "`) hasta la siguiente letra.
- Clave `[text] punctuation_commands` (`bool`, defecto `true`) en `src/speechflow/config.py`: campo `Config.punctuation_commands`, esquema `_SCHEMA["text"]["punctuation_commands"]` y línea en la plantilla de `write_emergency`. Con `false` el texto se inserta tal cual, sin mayúscula inicial.
- Parámetro `punctuation_commands: bool = False` en `PushToTalk`, guardado como `self.punctuation_commands`; `main()` le pasa `config.punctuation_commands`.
- En `PushToTalk._transcribe_and_insert()`: si la clave está activa y hay texto, se aplica `apply_voice_punctuation(text, transcriber.last_language)` antes de `insert_text()`. Si el texto procesado difiere del original, se registra una línea `INFO` `Texto original: ...` antes de `Insertado (...)`, que muestra el texto final y su número de caracteres.
- Actualizar tests (`tests/test_punctuation.py` nuevo, `tests/test_config.py`, `tests/test_push_to_talk.py`) y documentación (`speechflow.example.toml`, `README.md`, `TODO.md`).

**Fuera de alcance (para futuras specs):**

- Tabla de comandos configurable por el usuario y diccionario de reemplazos (ítem 6 del roadmap).
- Más idiomas además de es/en.
- Comandos de edición ("borra eso", "deshacer", "mayúsculas") y de teclado ("tabulador", "escape").
- Atajo en caliente para activar o desactivar la función; la clave se lee solo al arrancar.
- Opción de CLI (`--no-punctuation`); la clave del TOML basta.
- Teclear los saltos de línea como `Shift+Return` o evitar que `Return` envíe el mensaje en chats; `xdotool type` los teclea como `Return` tal cual.
- Escapar la propia palabra `literal` o varias palabras seguidas.
- Heurísticas que distingan `punto` como comando de `punto` como palabra ("punto de vista").
- Capitalizar nombres propios, siglas o después de `...`.
- Cambios en `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.

## Modelo de datos

```python
# src/speechflow/config.py
@dataclass(frozen=True)
class Config:
    ...
    punctuation_commands: bool = True   # [text] punctuation_commands

_SCHEMA["text"] = {"punctuation_commands": ((bool,), "punctuation_commands")}
```

```toml
[text]
# punctuation_commands = true   # sustituye "punto", "coma", "nueva línea"... por su signo; false inserta lo que transcribe Whisper
```

```python
# src/speechflow/punctuation.py
# Solo estructuras de datos de la tabla; sin estado.
COMMANDS: dict[str, dict[tuple[str, ...], str]] = {
    "es": {("punto",): ".", ("punto", "y", "coma"): ";", ("nueva", "línea"): "\n", ...},
    "en": {("period",): ".", ("new", "line"): "\n", ...},
}
ESCAPE_WORDS = {"es": "literal", "en": "literally"}

def apply_voice_punctuation(text: str, language: str) -> str: ...

# src/speechflow/app.py
# PushToTalk.__init__(..., punctuation_commands: bool = False); self.punctuation_commands
```

Convenciones:

- Las claves de `COMMANDS` son tuplas de palabras en minúscula, sin signos. La comparación normaliza cada palabra del texto a minúscula y le quita la puntuación de los extremos antes de buscar la frase.
- Los comandos de cierre y de apertura (`"` , `(`) se distinguen por la entrada de la tabla, no por el contexto; `cerrar comillas` sin `abrir comillas` produce igualmente `"`.
- `language` distinto de `es` y `en` devuelve el texto sin cambios.
- Texto vacío devuelve texto vacío.
- El valor de `punctuation_commands` se lee solo al arrancar; cambiarlo exige reiniciar.

## Plan de implementación

1. En `config.py`, añadir `Config.punctuation_commands`, la sección `text` en `_SCHEMA` y la línea de plantilla de `write_emergency`. Tests en `tests/test_config.py` (defecto `True`, `false` válido, tipo incorrecto como `"si"` con error que nombra `text.punctuation_commands`, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. Crear `src/speechflow/punctuation.py` con la tabla `COMMANDS`, `ESCAPE_WORDS` y `apply_voice_punctuation()` limitada a sustituir comandos y colocar espacios (sin mayúsculas ni limpieza de la puntuación de Whisper todavía). Tests iniciales en `tests/test_punctuation.py` para es y en. Verificar: `pytest tests/test_punctuation.py` pasa.
3. En `punctuation.py`, añadir la coincidencia por frase más larga, la normalización de mayúsculas y puntuación pegada por Whisper, la palabra de escape y la regla de mayúsculas. Ampliar los tests de tabla: `Hola, coma, mundo, punto.` → `Hola, mundo.`, `punto y coma` frente a `punto`, escape, `fr` sin cambios, texto vacío, texto solo con comandos. Verificar: `pytest tests/test_punctuation.py` pasa.
4. En `app.py`, añadir el parámetro `punctuation_commands` a `PushToTalk`, aplicar `apply_voice_punctuation()` en `_transcribe_and_insert()` con la línea `Texto original: ...` y pasar `config.punctuation_commands` desde `main()`. Tests en `tests/test_push_to_talk.py` con dobles: `insert_text` recibe el texto procesado, con la clave en `False` recibe el texto intacto, en modo auto se usa `last_language`, y el log muestra el original solo si cambia. Verificar: `pytest` pasa y `speechflow` inserta `Hola, mundo.` al dictar "hola coma mundo punto".
5. Documentar en `speechflow.example.toml` y `README.md` (tabla de comandos, escape `literal`, mayúscula inicial, aviso de que `nueva línea` teclea `Return`, cómo apagar la función) y marcar el ítem 7 de la Fase 3 en `TODO.md`.

## Criterios de aceptación

- [ ] `apply_voice_punctuation("hola coma mundo punto", "es")` devuelve `"Hola, mundo."`.
- [ ] `apply_voice_punctuation("Hola, coma, mundo, punto.", "es")` devuelve `"Hola, mundo."` (la puntuación de Whisper no se duplica).
- [ ] `apply_voice_punctuation("hola punto adiós", "es")` devuelve `"Hola. Adiós"`.
- [ ] `apply_voice_punctuation("uno punto y coma dos", "es")` devuelve `"Uno; dos"` y `"hola dos puntos"` devuelve `"Hola:"`.
- [ ] `apply_voice_punctuation("abrir interrogación cómo estás cerrar interrogación", "es")` devuelve `"¿Cómo estás?"`.
- [ ] `apply_voice_punctuation("hola nueva línea adiós", "es")` devuelve `"Hola\nAdiós"` y `nuevo párrafo` produce `"\n\n"`.
- [ ] `apply_voice_punctuation("abrir paréntesis hola cerrar paréntesis", "es")` devuelve `"(Hola)"`.
- [ ] `apply_voice_punctuation("hello comma world period", "en")` devuelve `"Hello, world."`.
- [ ] `apply_voice_punctuation("un literal punto de vista", "es")` devuelve `"Un punto de vista"`.
- [ ] `literal` que no precede a un comando se conserva (`"literal mente"` no pierde la palabra).
- [ ] Con `language = "fr"` el texto sale idéntico, incluida la primera letra.
- [ ] Texto vacío devuelve texto vacío.
- [ ] Con `punctuation_commands = true` y un dictado sin comandos, la primera letra sale en mayúscula y el resto no cambia.
- [ ] En modo auto con idioma detectado `en`, se usa el vocabulario inglés.
- [ ] Con `[text] punctuation_commands = false` el texto se inserta exactamente como lo devuelve `Transcriber`.
- [ ] Cuando el texto cambia, el log muestra `Texto original: ...` antes de `Insertado (...)`, y `Insertado` muestra el texto final.
- [ ] `[text] punctuation_commands = "si"` en el TOML hace inválido el archivo con un mensaje que nombra `text.punctuation_commands`.
- [ ] Una clave desconocida en `[text]` se rechaza como las demás secciones.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `pytest` pasa con código 0 y no escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[text] punctuation_commands`, la tabla de comandos y la palabra de escape.

## Decisiones

- **Sí:** vocabulario fijo en es y en según el idioma del dictado, por elección del usuario. Reutiliza `last_language` (SPEC 19) y funciona con el modo auto.
- **No:** solo español. Rompería la coherencia con el cambio de idioma.
- **No:** tabla configurable en el TOML. Se solapa con el diccionario de reemplazos (ítem 6) y merece su propia spec.
- **Sí:** conjunto ampliado (puntuación, aperturas y cierres, suspensivos, saltos, paréntesis, comillas, guion), por elección del usuario. El texto de la tabla queda cerrado en esta spec.
- **Sí:** coincidencia sin distinguir mayúsculas ni puntuación pegada, por elección del usuario. Whisper casi siempre devuelve `Punto.` o `coma,`; con coincidencia exacta casi nunca se activaría.
- **Sí:** clave `[text] punctuation_commands` activada por defecto, por elección del usuario. Quien dicta la palabra "punto" literalmente puede apagarla; se asume el cambio de comportamiento para todos los usuarios actuales.
- **No:** clave desactivada por defecto o función sin clave. La primera esconde la función; la segunda no ofrece salida.
- **Sí:** teclear `Return` para los saltos tal cual, por elección del usuario. Es lo que pide "nueva línea"; el riesgo de enviar un chat se documenta en el README.
- **No:** `Shift+Return`. Cambia `inserter.py` y no equivale a un salto de línea en todos los editores.
- **Sí:** quitar el espacio antes de los signos de cierre, mayúscula tras `. ? !` y salto, y mayúscula al inicio del dictado, por elección del usuario. La mayúscula inicial se aplica siempre que la función esté activa, aunque no haya comandos; es un efecto de la función y se documenta.
- **Sí:** palabra de escape `literal` / `literally`, por elección del usuario. Resuelve "punto de vista" sin heurísticas. Solo afecta a la palabra siguiente.
- **No:** detectar por contexto si `punto` es comando o palabra. Frágil y difícil de probar.
- **Sí:** módulo `punctuation.py` con función pura entre `Transcriber` y `insert_text`, por elección del usuario. Se prueba sin GPU con tests de tabla (SPEC 16).
- **No:** meter el posprocesado en `transcriber.py`. Mezcla Whisper con reglas de texto y complica los dobles de `WhisperModel`.
- **Sí:** un idioma fuera de es/en deja el texto intacto, incluida la mayúscula inicial. Decisión del diseño: no hay vocabulario que aplicar y se evita tocar texto en idiomas sin reglas.
- **Sí:** `punctuation_commands` en `PushToTalk` con defecto `False`. Decisión del diseño: los tests existentes con dobles no cambian su texto esperado; `main()` pasa el valor real (`True` por defecto en `Config`).
- **Sí:** el guion lleva un espacio a cada lado y `...` son tres puntos ASCII. Decisión del diseño: `guion` suele separar incisos, y el ASCII evita problemas de tecleado con `xdotool`.
- **Sí:** `Texto original: ...` en el log solo cuando el texto cambia. Decisión del diseño: no duplica cada línea de dictado normal.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| La palabra `punto`, `coma`, `guion` o `comillas` en una frase normal se sustituye sin querer | Palabra de escape `literal`, la clave `punctuation_commands = false` y el log `Texto original: ...` para ver qué cambió. |
| `nueva línea` o `nuevo párrafo` teclean `Return` y envían el mensaje en un chat o formulario | Documentado en el README; la función se apaga con la clave. Alternativa con `Shift+Return` queda fuera de alcance. |
| Whisper transcribe el comando con otra grafía (`puntó`, `coma` como `Coma.`, `new-line`) | La normalización cubre mayúsculas y puntuación pegada; las variantes no cubiertas se verán en el log `Texto original: ...` y se añaden a la tabla en una spec posterior. |
| La mayúscula inicial altera dictados que continúan una frase ya empezada en la ventana de destino | Es un efecto declarado de la función; con la clave en `false` se desactiva. |
| La puntuación pegada por Whisper se elimina de más y rompe un texto legítimo (`Hola, coma` mal reconocido) | La regla solo borra la puntuación final de la palabra inmediatamente anterior, y solo cuando el comando es de puntuación; tests de tabla lo fijan. |
| Un cambio en `_transcribe_and_insert()` rompe los tests de `PushToTalk` | El parámetro tiene defecto `False`, así que los tests existentes deben pasar sin modificarse. |

## Lo que **no** está en esta spec

- Tabla de comandos configurable y diccionario de reemplazos.
- Otros idiomas además de es/en.
- Comandos de edición o de teclado.
- Activar o desactivar la función en caliente, o con una opción de CLI.
- Saltos de línea con `Shift+Return` o protección frente al envío de chats.
- Escapar la palabra `literal` o varias palabras seguidas.
- Heurísticas para distinguir comando de palabra.
- Mayúscula tras `...` y capitalización de nombres propios.
- Cambios en `scripts/benchmark_stt.py` y `scripts/capture_mic.py`.

Cada uno, si se aborda, va en su propia spec.
