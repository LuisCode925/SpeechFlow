# SPEC 26 — Historial de transcripciones (JSONL)

> **Estado:** Implementado
> **Depende de:** SPEC 10, SPEC 14, SPEC 16, SPEC 17, SPEC 21, SPEC 25
> **Fecha:** 2026-10-13
> **Objetivo:** Guardar cada dictado transcrito como una línea JSON en `history.jsonl` dentro de `state_dir()`, con rotación por tamaño, para poder recuperar un dictado perdido y como base de la futura GUI.

## Por qué existe esta spec

Hoy el texto dictado solo sale por el log (que rota y mezcla otros mensajes) y por la inserción en la ventana con foco. Si la ventana cambia, la aplicación destino ignora el pegado o `xdotool` falla, el dictado se pierde. Un archivo propio, con una línea JSON por dictado, permite recuperarlo con `jq` o `less`. También es el dato que la GUI necesitará (elemento 8 de `TODO.md`). Esta spec cubre solo la escritura; leerlo desde la aplicación va en otra spec.

## Alcance

**Dentro:**

- Módulo nuevo `src/speechflow/history.py` con la clase `History`:
  - `History(path, max_bytes, backup_count)`: abre el archivo con rotación por tamaño y permisos `0600` (misma técnica que el log de la SPEC 17).
  - `History.add(entry)`: escribe `entry` como una línea JSON (`json.dumps(..., ensure_ascii=False)`), con un hilo a la vez (`threading.Lock`).
  - `History.close()`: cierra el archivo.
- `history_path()` en `src/speechflow/config.py`: `state_dir() / "history.jsonl"`.
- Claves `[history]` en `src/speechflow/config.py` (campos `Config.history_enabled` y `Config.history_max_mb`, esquema `_SCHEMA["history"]` y líneas en la plantilla de `write_emergency`):
  - `[history] enabled` (`bool`, defecto `true`): `false` no crea ni escribe el archivo.
  - `[history] max_mb` (`int` o `float`, defecto `5`): tamaño máximo del archivo activo antes de rotar. Un valor menor o igual que 0 hace inválido el archivo con un mensaje que nombra `history.max_mb`.
  - Constantes `HISTORY_BACKUP_COUNT = 2` (copias `history.jsonl.1` y `history.jsonl.2`) en `history.py`.
- `src/speechflow/app.py`:
  - `PushToTalk` recibe `history` (parámetro al final, defecto `None` = sin historial) y llama a `history.add(...)` en `_transcribe_and_insert`, **después** de aplicar la puntuación por voz y **antes** de `insert_text`. Así el dictado queda guardado aunque la inserción falle.
  - `main()` crea `History` solo si `config.history_enabled`, y la cierra en el cierre limpio de la SPEC 15.
  - Si el archivo no se puede abrir al arrancar, `WARNING` `No se puede escribir el historial en <ruta>: <causa>. Se sigue sin historial.` y el programa sigue.
  - Si una escritura falla durante la ejecución, `WARNING` `No se pudo guardar el dictado en el historial: <causa>`; solo el primer fallo seguido se registra, y el dictado se inserta igualmente. Una escritura correcta rearma el aviso.
  - No se guardan los dictados sin texto reconocido (`Sin texto reconocido`) ni el audio descartado.
- Tests nuevos en `tests/test_history.py` y actualizados en `tests/test_config.py` y `tests/test_push_to_talk.py`, con directorio temporal y dobles.
- Documentación: `speechflow.example.toml`, `README.md` (claves `[history]`, formato de la línea, ruta, aviso de privacidad y ejemplo con `jq`) y `TODO.md` (marcar el elemento 8).

**Fuera de alcance (para futuras specs):**

- Subcomando `speechflow history`, búsqueda, borrado o exportación desde la CLI.
- Mostrar o reinsertar entradas desde la GUI o la bandeja.
- Guardar el audio.
- Cifrado del archivo.
- Registrar el resultado de la inserción (método usado, respaldo a `type`, fallo).
- Recorte por número de entradas o por antigüedad.
- Cambios en `transcriber.py`, `inserter.py`, `punctuation.py`, `audio.py`, `notifier.py` y `scripts/`.

## Modelo de datos

Una línea por dictado en `$XDG_STATE_HOME/speechflow/history.jsonl` (o `~/.local/state/speechflow/history.jsonl`):

```json
{"ts": "2026-10-13T10:42:07.318-05:00", "text": "Hola, mundo.", "original": "hola coma mundo punto", "language": "es", "model": "small", "audio_seconds": 2.4, "seconds": 0.61}
```

| Campo | Tipo | Significado |
| --- | --- | --- |
| `ts` | `str` | Fecha y hora local en ISO 8601 con milisegundos y desfase (`datetime.now().astimezone().isoformat(timespec="milliseconds")`). |
| `text` | `str` | Texto final, tal como se entrega a `insert_text`. |
| `original` | `str` | Texto de Whisper antes de la puntuación por voz. Igual a `text` si no hubo cambios o la opción está desactivada. |
| `language` | `str` | Idioma usado: `transcriber.last_language` (en modo automático, el detectado). |
| `model` | `str` | `PushToTalk.model_name`. |
| `audio_seconds` | `float` | Duración del audio, redondeada a 2 decimales. |
| `seconds` | `float` | Tiempo de transcripción, redondeado a 2 decimales. |

Convenciones:

- Codificación UTF-8, sin escapar acentos; un salto de línea dentro del texto se escribe `\n` (JSON), así que cada entrada ocupa una sola línea.
- Archivos rotados: `history.jsonl.1` es el más reciente, `history.jsonl.2` el más antiguo.
- Permisos `0600` en el archivo activo y en cada rotado.

## Plan de implementación

1. En `log.py`, renombrar `_PrivateRotatingFileHandler` a `PrivateRotatingFileHandler` (público) y actualizar sus usos. Verificar: `pytest` pasa igual que antes.
2. Añadir `history_path()` y `[history]` (`enabled`, `max_mb`) a `config.py`: campos, esquema, validación de `max_mb`, plantilla de `write_emergency`. Tests en `tests/test_config.py`.
3. Crear `history.py` con `History` (`add`, `close`, rotación por tamaño, `0600`, `Lock`). Tests en `tests/test_history.py`: una línea JSON válida por `add`, acentos sin escapar, rotación al superar `max_bytes`, permisos `0600`, dos hilos escribiendo sin mezclar líneas.
4. Conectar a `app.py`: parámetro `history` en `PushToTalk`, llamada antes de `insert_text`, creación y cierre en `main()`, avisos de fallo. Tests en `tests/test_push_to_talk.py` con un `History` doble: se guarda con texto, no se guarda sin texto, se guarda aunque `insert_text` falle, un fallo de escritura no impide la inserción y avisa una sola vez.
5. Documentar en `speechflow.example.toml` y `README.md`; marcar el elemento 8 de `TODO.md`. Prueba manual: dictar dos frases, ver dos líneas con `jq . ~/.local/state/speechflow/history.jsonl`. Verificar: el README coincide con el comportamiento real.

## Criterios de aceptación

- [ ] Con la configuración por defecto, un dictado con texto añade exactamente una línea a `history.jsonl`, y esa línea es JSON válido con los siete campos de la tabla.
- [ ] Un dictado sin texto reconocido no añade ninguna línea.
- [ ] `text` contiene el texto tras la puntuación por voz y `original` el de Whisper; con `punctuation_commands = false` ambos son iguales.
- [ ] Un texto con `á`, `ñ` y `¿` aparece tal cual en el archivo, sin secuencias `\u00xx`.
- [ ] Si `insert_text` lanza una excepción, la línea del historial ya está escrita.
- [ ] Con `[history] enabled = false` el archivo no se crea ni se modifica.
- [ ] Al superar `max_mb`, el archivo activo pasa a `history.jsonl.1`, y nunca existen más de `history.jsonl.1` y `history.jsonl.2` además del activo.
- [ ] El archivo activo y los rotados tienen permisos `0600`.
- [ ] `[history] max_mb = 0` y `max_mb = "5"` hacen inválido el archivo con un mensaje que nombra `history.max_mb`; `enabled = "si"` nombra `history.enabled`.
- [ ] Si `state_dir()` no es escribible, `speechflow` arranca, muestra el `WARNING` de apertura y dicta con normalidad.
- [ ] Si una escritura falla, el dictado se inserta igualmente y el `WARNING` aparece una sola vez hasta que una escritura vuelva a funcionar.
- [ ] El cierre limpio por `SIGTERM` cierra el historial sin dejar la última línea a medias.
- [ ] `pytest` pasa sin cambios en los tests existentes, salvo los de `log.py` por el renombrado.

## Decisiones

- **Sí:** JSONL en `state_dir()`, por elección del usuario. Una línea por dictado se añade sin reescribir el archivo, se lee con `jq` y la GUI lo puede seguir leyendo.
- **Sí:** campos `ts`, `text`, `original`, `language`, `model`, `audio_seconds` y `seconds`, por elección del usuario. Permite recuperar el dictado y depurar la puntuación por voz y el idioma detectado.
- **No:** registrar el método de inserción y el resultado. Añade campos que mantener y la inserción ocurre después de guardar; si hace falta, va en otra spec.
- **Sí:** activo por defecto, con `[history] enabled = false` para apagarlo, por elección del usuario. La utilidad de recuperar un dictado perdido exige que ya esté activo cuando se pierde.
- **No:** desactivado por defecto. Nadie tendría el historial en el momento en que lo necesita.
- **Sí:** rotación por tamaño (`max_mb`, defecto 5, dos copias), por elección del usuario. Reutiliza la técnica de la SPEC 17 y no reescribe el archivo.
- **No:** recorte por número de entradas. Obliga a reescribir el archivo en cada recorte.
- **No:** sin límite. El archivo crece sin parar en un programa pensado para quedar siempre abierto.
- **Sí:** solo el archivo, sin CLI, por elección del usuario. Consultar y reinsertar llegarán con la GUI y el canal de control.
- **Sí:** guardar antes de `insert_text`. Decisión del diseño: el objetivo es recuperar dictados cuya inserción falló.
- **Sí:** el texto del dictado se guarda en claro, y el README lo avisa. Decisión del diseño: cifrarlo sin una forma de gestionar la clave no aporta protección real; los permisos `0600` limitan el acceso a otros usuarios.
- **Sí:** un fallo del historial nunca interrumpe el dictado. Decisión del diseño: el historial es auxiliar; perder una entrada es mejor que perder la inserción.
- **Sí:** hacer público `PrivateRotatingFileHandler`. Decisión del diseño: evita importar un nombre privado desde otro módulo y no duplica código.
- **No:** reutilizar el logger de `speechflow` para escribir el historial. Mezclaría las entradas con el formato de log y con los niveles de la SPEC 24.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El historial guarda en claro lo que el usuario dicta, incluidas contraseñas o datos privados | Permisos `0600`, `enabled = false` para apagarlo y aviso explícito en el README. |
| Dos hilos escriben a la vez (transcripción y cierre) y mezclan líneas | `Lock` en `add`/`close` y test con dos hilos. |
| La rotación parte una línea por la mitad | `RotatingFileHandler` rota antes de escribir y cada `add` escribe la línea completa en una sola llamada; test que lo verifica. |
| `state_dir()` no es escribible o el disco está lleno | `WARNING` y dictado sin historial; nunca se propaga la excepción. |
| El cierre limpio llega con una escritura en curso | `close()` toma el `Lock`; se invoca después de esperar la transcripción (SPEC 15). |

## Lo que **no** está en esta spec

- Subcomando de CLI para consultar, buscar, borrar o exportar el historial.
- Reinsertar o mostrar entradas desde la GUI o la bandeja.
- Guardar el audio de los dictados.
- Cifrado del historial.
- Registro del resultado de la inserción.
- Recorte por número de entradas o por antigüedad.
- Cambios en `transcriber.py`, `inserter.py`, `punctuation.py`, `audio.py`, `notifier.py` y `scripts/`.

Cada uno, si se aborda, va en su propia spec.
