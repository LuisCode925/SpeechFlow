# SPEC 27 — Diccionario de reemplazos e `initial_prompt`

> **Estado:** Aprobado
> **Depende de:** SPEC 10, SPEC 16, SPEC 18, SPEC 19, SPEC 21, SPEC 26
> **Fecha:** 2026-10-13
> **Objetivo:** Permitir que el usuario corrija el texto dictado con un diccionario de reemplazos por expresiones regulares (`[replacements]` en el TOML) y sesgue el vocabulario de Whisper con un `initial_prompt` configurable (`[model] initial_prompt`).

## Por qué existe esta spec

Whisper escribe mal los nombres propios, las marcas y la jerga del usuario (`git hub`, `pi torch`, `Kubernetes` como `cuber netis`). Hay dos palancas complementarias: darle contexto antes de transcribir (`initial_prompt`, que reduce el error) y corregir lo que aun así falla después de transcribir (reemplazos, que lo eliminan de forma determinista). Las dos salen del elemento 6 de `TODO.md` y comparten archivo de configuración y documentación, por eso van en una sola spec.

## Alcance

**Dentro:**

- Módulo nuevo `src/speechflow/replacements.py`, sin dependencias del resto del paquete:
  - `compile_rules(pairs)`: recibe una secuencia de pares `(patrón, reemplazo)` y devuelve una tupla de `(re.Pattern, str)`, compilados con `re.IGNORECASE`. Lanza `ValueError` con la causa si un patrón no compila, si el reemplazo no es válido para ese patrón (`re.error` al expandirlo) o si el patrón coincide con la cadena vacía.
  - `apply_replacements(text, rules)`: aplica las reglas en orden con `Pattern.sub`; cada regla ve la salida de la anterior. El reemplazo admite `\1` y `\g<nombre>`. Devuelve el texto con `strip()`.
- `[replacements]` en `src/speechflow/config.py` (campos `Config.replacements` y `Config.replacements_by_language`, validación en `load_config` y líneas en la plantilla de `write_emergency`):
  - Claves de la tabla plana: `"patrón" = "reemplazo"`, ambos `str`, el patrón no vacío. Se aplican con cualquier idioma.
  - Subtablas `[replacements.<idioma>]` (por ejemplo `[replacements.es]`): mismas claves, solo se aplican cuando el idioma usado en el dictado (`transcriber.last_language`, también en modo automático) coincide con el nombre de la subtabla. Cualquier nombre no vacío es válido; una subtabla de un idioma que nunca se usa no tiene efecto.
  - Orden de aplicación: primero la subtabla del idioma usado, después la tabla plana, cada una en el orden en que aparece en el TOML.
  - Un valor que no sea `str` (salvo una subtabla), un patrón vacío, una regex que no compila, un reemplazo inválido o un patrón que coincide con la cadena vacía hace inválido el archivo con un mensaje que nombra `replacements.<clave>` (o `replacements.<idioma>.<clave>`) y la causa.
  - Las reglas se compilan una sola vez al cargar la configuración; se leen solo al arrancar.
- `[model] initial_prompt` (`str`, defecto `""`) en `config.py` (campo `Config.initial_prompt`, esquema `_SCHEMA["model"]`, plantilla de `write_emergency`):
  - Texto de contexto que se pasa a Whisper en cada dictado. Vacío significa sin prompt.
  - Constante `INITIAL_PROMPT_WARN_CHARS = 1000` en `config.py`: si el prompt es más largo, `WARNING` `model.initial_prompt tiene <n> caracteres; Whisper solo usa los últimos ~224 tokens.` y el valor se usa tal cual, sin truncar.
- `src/speechflow/transcriber.py`:
  - `Transcriber.__init__` recibe `initial_prompt: str = ""` (parámetro al final) y lo guarda.
  - `Transcriber.transcribe` pasa `initial_prompt=self.initial_prompt or None` a `self._model.transcribe(...)`. La detección automática de idioma (`_detect`) y el calentamiento del VAD no lo usan.
- `src/speechflow/app.py`:
  - `load_transcriber` y `PushToTalk` reciben `initial_prompt` (parámetro al final, defecto `""`) para que la recarga tras la descarga por inactividad (SPEC 12) conserve el prompt. `PushToTalk` recibe además `replacements` (tupla de reglas por idioma y plana, defecto vacío).
  - `_transcribe_and_insert` aplica los reemplazos **después** de la puntuación por voz (SPEC 21) y **antes** de guardar en el historial (SPEC 26) y de `insert_text`.
  - `original` en el historial y en el log `Texto original: ...` sigue siendo el texto de Whisper; `text` es el final, con puntuación y reemplazos.
  - Si tras los reemplazos el texto queda vacío, se trata como un dictado sin texto: `INFO` `Sin texto tras los reemplazos ({seconds:.2f} s, {label}).`, no se guarda en el historial y no se inserta nada.
- Tests nuevos en `tests/test_replacements.py` y actualizados en `tests/test_config.py`, `tests/test_transcriber.py` y `tests/test_push_to_talk.py`, con dobles (sin GPU ni modelo real).
- Documentación: `speechflow.example.toml`, `README.md` (claves `[model] initial_prompt` y `[replacements]`, orden de aplicación, sintaxis de las regex y de las referencias `\1`, ejemplos y consejos para escribir un buen prompt) y `TODO.md` (marcar el elemento 6).

**Fuera de alcance (para futuras specs):**

- Recarga del diccionario o del prompt en caliente; cambiarlos exige reiniciar.
- Reemplazos distintos según la aplicación con foco.
- `hotwords` de `faster-whisper` y otros parámetros de decodificación (`condition_on_previous_text`, `temperature`...).
- Un prompt distinto por idioma.
- Mutar el prompt con los últimos dictados (contexto acumulado).
- Flags por regla (sensible a mayúsculas, multilínea): se usa `(?-i:...)` dentro del patrón.
- Reemplazos aplicados antes de la puntuación por voz.
- Comandos de voz definidos por el usuario (los de la SPEC 21 siguen fijos en `punctuation.py`).
- Subcomando de CLI para probar o listar reglas.
- Cambios en `audio.py`, `inserter.py`, `punctuation.py`, `notifier.py`, `history.py` y `scripts/`.

## Modelo de datos

```python
# src/speechflow/replacements.py
Rule = tuple[re.Pattern[str], str]   # (patrón compilado con IGNORECASE, reemplazo)

def compile_rules(pairs: Iterable[tuple[str, str]]) -> tuple[Rule, ...]: ...   # ValueError si no compila
def apply_replacements(text: str, rules: Iterable[Rule]) -> str: ...

# src/speechflow/config.py
INITIAL_PROMPT_WARN_CHARS = 1000

@dataclass(frozen=True)
class Config:
    ...
    initial_prompt: str = ""                                               # [model] initial_prompt
    replacements: tuple[tuple[str, str], ...] = ()                         # [replacements] plano, en orden del TOML
    replacements_by_language: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()  # [replacements.<idioma>]
```

```toml
[model]
# initial_prompt = ""   # contexto para Whisper; ej.: "Hablo de GitHub, PyTorch y Kubernetes."

[replacements]
# "git ?hub" = "GitHub"                  # regex, sin distinguir mayúsculas
# "pi ?torch" = "PyTorch"
# "(\\d+) por ciento" = "\\1 %"          # referencias \1 en el reemplazo

[replacements.es]
# "cuber ?netis" = "Kubernetes"

[replacements.en]
# "cube ?r ?netes" = "Kubernetes"
```

Convenciones:

- `Config.replacements` y `Config.replacements_by_language` son tuplas (`frozen=True`) que guardan el texto original de patrones y reemplazos; `load_config` las valida compilándolas y `main()` las vuelve a compilar con `compile_rules` para `PushToTalk`. La plantilla de `write_emergency` deja todo comentado y la lectura da `Config()`.
- Las claves de TOML con barras invertidas se escriben entre comillas simples (`'(\d+) por ciento' = '\1 %'`) o con la barra duplicada; el README lo explica.
- La comparación no distingue mayúsculas (`re.IGNORECASE`). El reemplazo se inserta tal cual, sin adaptar la capitalización.
- El texto de los patrones y reemplazos no se escribe en el log (puede contener nombres o datos privados); un fallo de validación nombra solo la clave y la causa de la regex.
- `--list-devices` no se ve afectado.

## Plan de implementación

1. Crear `replacements.py` con `compile_rules` y `apply_replacements`. Tests en `tests/test_replacements.py`: sustitución simple, sin distinguir mayúsculas, referencias `\1` y `\g<nombre>`, orden secuencial (la segunda regla ve la salida de la primera), texto sin coincidencias intacto, resultado con `strip()`, regex que no compila, grupo inexistente en el reemplazo y patrón que coincide con la cadena vacía lanzan `ValueError`. Verificar: `pytest tests/test_replacements.py` pasa.
2. Añadir a `config.py` `Config.initial_prompt`, `Config.replacements`, `Config.replacements_by_language`, su validación (usando `compile_rules`), el `WARNING` por prompt largo y las líneas de la plantilla de `write_emergency`. Tests en `tests/test_config.py`: defectos, prompt válido, tipo incorrecto en `model.initial_prompt`, tabla plana y subtablas válidas con el orden del TOML conservado, valor no textual, patrón vacío, regex inválida, patrón que coincide con vacío y referencia inválida con mensajes que nombran la clave, prompt de más de 1000 caracteres con `WARNING`, plantilla de emergencia da `Config()`. Verificar: `pytest tests/test_config.py` pasa.
3. En `transcriber.py`, añadir `initial_prompt` a `Transcriber` y pasarlo a `self._model.transcribe(...)` en `transcribe`. En `app.py`, pasarlo por `load_transcriber`, `PushToTalk` y `main()` (incluida la recarga tras la descarga por inactividad). Tests en `tests/test_transcriber.py` y `tests/test_push_to_talk.py` con un modelo doble: cadena vacía llega como `None`, un texto llega tal cual, `_detect` no lo recibe, la recarga conserva el valor. Verificar: `pytest` pasa.
4. En `app.py`, conectar los reemplazos: compilar en `main()`, pasarlos a `PushToTalk` y aplicarlos en `_transcribe_and_insert` tras la puntuación por voz, con el caso de texto vacío tras reemplazar. Tests en `tests/test_push_to_talk.py`: se aplican tras la puntuación, subtabla del idioma usado antes que la plana (también con idioma automático), `history.text` lleva los reemplazos y `history.original` el texto de Whisper, texto vacío tras reemplazar no inserta ni guarda y registra el `INFO`. Verificar: `pytest` pasa.
5. Documentar en `speechflow.example.toml` y `README.md`; marcar el elemento 6 de `TODO.md`. Prueba manual: con `initial_prompt = "Hablo de Kubernetes y PyTorch."` y un reemplazo de prueba, dictar una frase con esos términos y comprobar la inserción y el `jq` de `history.jsonl`. Verificar: el README coincide con el comportamiento real.

## Criterios de aceptación

- [ ] `Config().initial_prompt == ""`, `Config().replacements == ()` y `Config().replacements_by_language == ()`.
- [ ] `[model] initial_prompt = "Kubernetes"` da `Config.initial_prompt == "Kubernetes"`; `initial_prompt = 5` hace inválido el archivo con un mensaje que nombra `model.initial_prompt`.
- [ ] Un `initial_prompt` de más de 1000 caracteres arranca con `WARNING` y se usa sin truncar.
- [ ] `Transcriber.transcribe` llama a `self._model.transcribe` con `initial_prompt=None` si el prompt es `""` y con el texto si no.
- [ ] `_detect` y el calentamiento del VAD no reciben `initial_prompt`.
- [ ] Tras una descarga por inactividad y una recarga, el modelo nuevo conserva el `initial_prompt`.
- [ ] `[replacements]` con `"git ?hub" = "GitHub"` hace que `apply_replacements("sube a Git hub", ...)` devuelva `"sube a GitHub"`; con `GIT HUB` también.
- [ ] `'(\d+) por ciento' = '\1 %'` convierte `20 por ciento` en `20 %`.
- [ ] Las reglas se aplican en el orden del TOML y la segunda ve la salida de la primera.
- [ ] Con idioma `es`, las reglas de `[replacements.es]` se aplican antes que las de la tabla plana; las de `[replacements.en]` no se aplican; con `auto` se usa el idioma detectado.
- [ ] Las reglas se aplican después de la puntuación por voz y antes de `history.add` e `insert_text`.
- [ ] `history.original` es el texto de Whisper y `history.text` el final; el log `Texto original: ...` sigue apareciendo cuando difieren.
- [ ] Un texto vacío tras los reemplazos no se inserta ni se guarda y registra `Sin texto tras los reemplazos (...)`.
- [ ] Un patrón vacío, una regex que no compila (`"(" = "x"`), un reemplazo con grupo inexistente (`"a" = "\\1"`), un patrón que coincide con vacío (`"x*" = "y"`) y un valor no textual hacen inválido el archivo con un mensaje que nombra `replacements.<clave>` y la causa.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] Sin `[replacements]` ni `initial_prompt`, el comportamiento y el log son idénticos a los de la SPEC 26.
- [ ] Prueba manual: con un `initial_prompt` y un reemplazo configurados, un dictado con esos términos se inserta con la grafía esperada y `history.jsonl` guarda `original` y `text` distintos.
- [ ] `pytest` pasa con código 0, sin GPU y sin modelo real.
- [ ] `git diff main -- scripts src/speechflow/audio.py src/speechflow/inserter.py src/speechflow/punctuation.py src/speechflow/notifier.py src/speechflow/history.py` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[model] initial_prompt`, `[replacements]` y `[replacements.<idioma>]`.

## Decisiones

- **Sí:** las dos mitades del elemento 6 de `TODO.md` en una spec. Comparten archivo de configuración y documentación, y el valor se ve al probarlas juntas.
- **Sí:** expresiones regulares en las claves, por elección del usuario. Permiten variantes (`git ?hub`) y capturas (`\1`) con una sola entrada; el precio es validar cada patrón al cargar.
- **No:** claves literales. Más simples, pero cada variante de Whisper (`git hub`, `Git-hub`, `guit hub`) exigiría su propia entrada.
- **Sí:** `re.IGNORECASE` siempre, por elección del usuario. Whisper capitaliza a su manera; sin esto muchas reglas fallarían en silencio. Quien necesite distinguir usa `(?-i:...)`.
- **No:** flags por regla o sintaxis extra en la clave. Complica el formato para un caso poco frecuente.
- **Sí:** el reemplazo admite `\1` y `\g<nombre>`, por elección del usuario. Es la razón de usar regex.
- **Sí:** aplicar después de la puntuación por voz, por elección del usuario. Las reglas ven el texto final y la mayúscula inicial de la SPEC 21 no pisa una grafía como `iPhone`.
- **No:** antes de la puntuación, ni orden configurable. Una clave más y dos caminos que probar sin que nadie lo pida.
- **Sí:** tabla plana más subtablas por idioma, por elección del usuario. La plana cubre lo común (marcas, nombres) y las subtablas lo propio de un idioma, también en modo automático.
- **No:** solo subtablas. Obliga a duplicar términos como `GitHub` en cada idioma.
- **Sí:** orden secuencial: subtabla del idioma usado y luego la plana, cada una en el orden del TOML, por elección del usuario. Lo específico del idioma actúa primero, y el usuario controla el orden con la posición en el archivo.
- **No:** una sola pasada simultánea. Exige combinar patrones en una regex y complica los grupos de captura.
- **Sí:** una regex o reemplazo inválido hace inválido el archivo, por elección del usuario. Mismo trato que el resto de errores de `config.py` y se compila una sola vez al arrancar.
- **No:** ignorar la regla con `WARNING`. El error pasaría desapercibido y el texto saldría mal sin explicación.
- **Sí:** rechazar patrones que coinciden con la cadena vacía. Decisión del diseño: `Pattern.sub` insertaría el reemplazo entre todos los caracteres y rompería el dictado.
- **Sí:** `initial_prompt` único y de tipo `str` en `[model]`, por elección del usuario. Un texto sirve para cualquier idioma y no duplica claves.
- **No:** un prompt por idioma. Mejor sesgo en modo automático, pero más claves; si hace falta, va en otra spec.
- **Sí:** `initial_prompt` vacío se pasa como `None`. Decisión del diseño: es lo que `faster-whisper` entiende como sin prompt.
- **Sí:** `WARNING` si el prompt pasa de 1000 caracteres, sin truncar, por elección del usuario. Whisper ya ignora lo que excede su ventana; truncar solo ocultaría un prompt demasiado largo.
- **Sí:** el prompt solo se pasa a la transcripción. Decisión del diseño: `detect_language` no lo usa y el calentamiento del VAD solo carga Silero.
- **Sí:** `history.original` sigue siendo el texto de Whisper, por elección del usuario. No cambia el significado de un campo ya publicado en la SPEC 26.
- **Sí:** un texto vacío tras los reemplazos se trata como un dictado sin texto. Decisión del diseño: el usuario puede borrar muletillas con una regla (`"eh+" = ""`) y no tiene sentido pegar una cadena vacía ni guardarla.
- **Sí:** no registrar patrones ni reemplazos en el log. Decisión del diseño: pueden contener nombres o datos privados.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Una regex mal escrita se come texto válido (por ejemplo `"a" = ""`) | Se aplican solo palabras que el usuario escribe; el log muestra `Texto original` y el historial guarda `original` y `text` para ver qué cambió. |
| Una regex con retroceso catastrófico congela la transcripción | Los textos de un dictado son cortos (máximo `max_seconds`) y las reglas las escribe el usuario; se documenta en el README. |
| Un `initial_prompt` mal elegido sesga o empeora la transcripción (repite el prompt, alucina vocabulario) | Defecto vacío, documentación con consejos y `WARNING` si es demasiado largo. |
| Una regla de la tabla plana pisa lo que cambió la subtabla del idioma | El orden está documentado y se controla con la posición en el TOML; test que lo fija. |
| Barras invertidas mal escapadas en el TOML (`\d` en cadena con comillas dobles) | Error de TOML mal formado con la línea; el README muestra la forma con comillas simples. |
| Cambiar el prompt o el diccionario sin reiniciar no tiene efecto | Se declara fuera de alcance y se documenta (se leen solo al arrancar). |

## Lo que **no** está en esta spec

- Recarga en caliente del diccionario o del prompt.
- Reemplazos por aplicación con foco.
- `hotwords` y otros parámetros de decodificación de `faster-whisper`.
- Un `initial_prompt` por idioma o acumulado con los últimos dictados.
- Flags por regla o comandos de voz definidos por el usuario.
- Reemplazos antes de la puntuación por voz.
- Subcomando de CLI para probar o listar reglas.
- Cambios en `audio.py`, `inserter.py`, `punctuation.py`, `notifier.py`, `history.py` y `scripts/`.

Cada uno, si se aborda, va en su propia spec.
