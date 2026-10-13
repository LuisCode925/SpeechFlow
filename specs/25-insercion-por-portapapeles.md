# SPEC 25 — Inserción por portapapeles (Ctrl+V)

> **Estado:** Aprobado
> **Depende de:** SPEC 05, SPEC 10, SPEC 16, SPEC 21, SPEC 24
> **Fecha:** 2026-10-12
> **Objetivo:** Insertar el texto dictado copiándolo al portapapeles y pegándolo con Ctrl+V (Ctrl+Shift+V en terminales) en lugar de teclearlo con `xdotool type`, y restaurar después el texto que había en el portapapeles.

## Por qué existe esta spec

`xdotool type` simula cada carácter como una pulsación de tecla. Con acentos, `ñ`, `¿`, `¡` y símbolos fuera del teclado activo es frágil: depende de la distribución de teclado y puede perder o cambiar caracteres. Pegar desde el portapapeles inserta el texto entero y tal cual. El precio es que el portapapeles del usuario se sobrescribe, así que hay que guardarlo y restaurarlo, y que las terminales usan otro atajo de pegado. Esta spec cubre ese flujo completo, con `xdotool type` como respaldo.

## Alcance

**Dentro:**

- `src/speechflow/inserter.py`: `insert_text(text, method="clipboard", extra_terminals=())`.
  - `method="type"`: el comportamiento actual (`xdotool type --clearmodifiers -- texto`), sin cambios.
  - `method="clipboard"`, con el texto no vacío, en este orden:
    1. Lee el contenido previo del portapapeles: `xclip -selection clipboard -o -t UTF8_STRING`. Si falla o está vacío, no hay nada que restaurar (`previo = None`).
    2. Escribe el dictado: `xclip -selection clipboard -i -t UTF8_STRING` con el texto por `stdin` (con `stdout` y `stderr` a `DEVNULL`, porque `xclip` deja un proceso en segundo plano que mantiene la selección).
    3. Lee la clase de la ventana con foco: `xdotool getwindowfocus getwindowclassname`. Si su minúscula está en `TERMINAL_CLASSES` o en `extra_terminals` (también en minúsculas), el atajo es `ctrl+shift+v`; en otro caso, `ctrl+v`. Si el comando falla, se asume que no es terminal.
    4. Pega: `xdotool key --clearmodifiers <atajo>`.
    5. Espera `PASTE_DELAY` (0,3 s) para que la aplicación destino lea el portapapeles.
    6. Si `previo` no es `None`, lo vuelve a escribir con `xclip -selection clipboard -i -t UTF8_STRING`.
  - Solo se toca la selección `CLIPBOARD`; `PRIMARY` (clic central) no se lee ni se escribe.
  - Si falla `xclip` o `xdotool` en cualquier paso del modo portapapeles (código distinto de 0, `OSError`, tiempo agotado), se restaura el portapapeles si ya se había leído, se registra un `WARNING` `Portapapeles no disponible (<causa>); se teclea con xdotool type.` y se inserta con `xdotool type`. Si `xdotool type` también falla, el error se propaga como hoy.
  - Las llamadas a `xclip` y `xdotool` usan un tiempo máximo (`COMMAND_TIMEOUT`, 2 s).
- Constante `TERMINAL_CLASSES` en `inserter.py` (clases de ventana en minúsculas): `gnome-terminal`, `gnome-terminal-server`, `konsole`, `xterm`, `uxterm`, `urxvt`, `alacritty`, `kitty`, `xfce4-terminal`, `terminator`, `tilix`, `st`, `st-256color`, `wezterm`, `foot`, `lxterminal`, `mate-terminal`, `qterminal`, `terminology`, `guake`, `yakuake`.
- Claves `[text]` en `src/speechflow/config.py` (campos `Config.insert_method` y `Config.terminal_classes`, esquema `_SCHEMA["text"]` y líneas en la plantilla de `write_emergency`):
  - `[text] insert_method` (`str`, defecto `"clipboard"`): `"clipboard"` o `"type"`. Otro valor hace inválido el archivo con un mensaje que nombra `text.insert_method`.
  - `[text] terminal_classes` (lista de `str`, defecto `[]`): clases que se **suman** a `TERMINAL_CLASSES`. Un elemento que no sea texto o esté vacío hace inválido el archivo con un mensaje que nombra `text.terminal_classes`.
  - Constante `INSERT_METHODS = ("clipboard", "type")` en `config.py`.
- `src/speechflow/app.py`:
  - `PushToTalk` recibe `insert_method` y `terminal_classes` (parámetros al final, con defecto `"clipboard"` y `()`) y los pasa a `insert_text`. Se leen solo al arrancar.
  - Comprobación de arranque: si `config.insert_method == "clipboard"` y `shutil.which("xclip")` es `None`, `ERROR` `Falta xclip. Instálalo con: sudo apt install xclip` y `sys.exit(1)`, después de la comprobación de `xdotool`. Con `"type"` no se exige `xclip`.
  - La línea `Insertado (...)` y las notificaciones no cambian.
- Tests nuevos o actualizados en `tests/test_inserter.py`, `tests/test_config.py` y `tests/test_app_helpers.py`, con `subprocess.run` y `time.sleep` sustituidos por dobles.
- Documentación: `speechflow.example.toml`, `README.md` (requisitos, descripción de `inserter.py`, claves `[text]`, limitaciones, nota de `nueva línea`) y `TODO.md` (marcar el elemento 5 y ajustar la línea de Wayland / `ydotool` / portapapeles).

**Fuera de alcance (para futuras specs):**

- Soporte Wayland (`wl-copy`, `wl-paste`, `ydotool`) y el aviso de la sesión no X11, que siguen como hoy.
- Restaurar contenidos del portapapeles que no sean texto (imágenes, listas de archivos) y otros formatos de `TARGETS`.
- Tocar o restaurar la selección `PRIMARY`.
- Interacción con gestores de historial del portapapeles (pueden registrar el dictado y el contenido restaurado).
- Opción de CLI para el método de inserción o tecla para cambiarlo en caliente.
- Detectar el terminal por otro medio que la clase de la ventana (`xprop`, título, proceso).
- Retardo de pegado configurable por TOML (queda como constante).
- Cambiar `punctuation.py`: el texto con `\n` se pega tal cual.
- Cambios en `transcriber.py`, `notifier.py`, `audio.py` y `scripts/`.

## Modelo de datos

```python
# src/speechflow/inserter.py
TERMINAL_CLASSES = frozenset({"gnome-terminal", "konsole", "xterm", "alacritty", "kitty", ...})  # minúsculas
PASTE_DELAY = 0.3        # segundos entre el pegado y la restauración del portapapeles
COMMAND_TIMEOUT = 2.0    # segundos máximos por llamada a xclip / xdotool

def insert_text(text: str, method: str = "clipboard", extra_terminals: tuple[str, ...] = ()) -> None: ...

# src/speechflow/config.py
INSERT_METHODS = ("clipboard", "type")

@dataclass(frozen=True)
class Config:
    ...
    insert_method: str = "clipboard"          # [text] insert_method
    terminal_classes: tuple[str, ...] = ()    # [text] terminal_classes; se suman a TERMINAL_CLASSES
```

```toml
[text]
# insert_method = "clipboard"   # "clipboard": copia y pega con Ctrl+V (Ctrl+Shift+V en terminales) y restaura el portapapeles; "type": teclea con xdotool
# terminal_classes = []         # clases de ventana extra que se pegan con Ctrl+Shift+V; ver: xdotool getwindowfocus getwindowclassname
```

Convenciones:

- `Config.terminal_classes` es una tupla (`frozen=True`); el TOML da una lista y `load_config` la convierte. La plantilla de `write_emergency` deja `terminal_classes` comentada y la lectura da `Config()`.
- La comparación de clases no distingue mayúsculas.
- El contenido previo del portapapeles solo vive en memoria durante la inserción y no se registra en el log.
- `insert_text` sigue lanzando la excepción de `xdotool type` si el respaldo también falla; `PushToTalk` la captura como hoy (`Error: ...`).
- `--list-devices` no se ve afectado.
- Ambas claves se leen solo al arrancar; cambiarlas exige reiniciar.

## Plan de implementación

1. En `config.py`, añadir `INSERT_METHODS`, `Config.insert_method`, `Config.terminal_classes`, las entradas de `_SCHEMA["text"]` (incluida la validación de lista de textos no vacíos) y las líneas de la plantilla de `write_emergency`. Tests en `tests/test_config.py` (defectos `"clipboard"` y `()`, `"type"` válido, `"paste"` inválido con `text.insert_method`, lista válida, elemento no textual o vacío inválido con `text.terminal_classes`, tipo incorrecto, plantilla de emergencia da `Config()`). Verificar: `pytest tests/test_config.py` pasa.
2. En `inserter.py`, añadir las constantes, el parámetro `method`, el flujo de portapapeles con restauración, la detección de terminal y el respaldo a `xdotool type`. Tests en `tests/test_inserter.py` con `subprocess.run` y `time.sleep` falsos que registran las llamadas en orden: con `method="type"` no se llama a `xclip` (los tests actuales de `xdotool type` siguen valiendo pasando `method="type"`); texto vacío no ejecuta nada; secuencia leer → escribir → clase → `ctrl+v` → espera → restaurar; `ctrl+shift+v` con clase de `TERMINAL_CLASSES` y con `extra_terminals` (sin distinguir mayúsculas); fallo de `getwindowclassname` usa `ctrl+v`; portapapeles previo vacío o ilegible no se restaura; fallo de `xclip` o `xdotool key` restaura y teclea con `type` con el `WARNING`; texto que parece opción va tras `--` en el respaldo. Verificar: `pytest tests/test_inserter.py` pasa.
3. En `app.py`, pasar `insert_method` y `terminal_classes` desde `Config` hasta `PushToTalk` y `insert_text`, y añadir la comprobación de arranque de `xclip`. Tests en `tests/test_app_helpers.py` y `tests/test_push_to_talk.py` (la configuración llega a `insert_text`; sin `xclip` y con `"clipboard"` sale con código 1 y el `ERROR`; con `"type"` no se exige). Verificar: `pytest` pasa.
4. Documentar en `speechflow.example.toml` y `README.md`: requisito `xclip`, descripción actual de `inserter.py`, las dos claves, la limitación (aplicaciones que leen el portapapeles tarde pueden pegar el contenido restaurado; el portapapeles previo no textual se pierde; los gestores de historial ven el dictado), cómo averiguar la clase de una ventana y cómo volver a `type`. Actualizar la nota de `nueva línea` / `nuevo párrafo` (con portapapeles se pega un salto de línea, no se teclea `Return`; en un chat puede no enviar el mensaje). Marcar el elemento 5 de `TODO.md`. Verificar: el README coincide con el comportamiento real.
5. Prueba manual en X11: dictar con acentos y símbolos (`¿Cómo estás? ñandú`) en un editor, en un navegador y en una terminal; comprobar que el portapapeles previo de texto se restaura y que con `insert_method = "type"` todo funciona como antes.

## Criterios de aceptación

- [ ] `Config().insert_method == "clipboard"` y `Config().terminal_classes == ()`.
- [ ] `[text] insert_method = "type"` y `"clipboard"` son válidos.
- [ ] `[text] insert_method = "paste"` hace inválido el archivo con un mensaje que nombra `text.insert_method`.
- [ ] `[text] terminal_classes = ["myterm"]` da `Config.terminal_classes == ("myterm",)`.
- [ ] `[text] terminal_classes = [""]` o `[1]` hacen inválido el archivo con un mensaje que nombra `text.terminal_classes`.
- [ ] `write_emergency` produce una plantilla que `load_config` lee y que da `Config()`.
- [ ] `insert_text("", ...)` no ejecuta ningún comando con ninguno de los dos métodos.
- [ ] `insert_text("hola", method="type")` ejecuta solo `xdotool type --clearmodifiers -- hola`.
- [ ] En modo portapapeles, las llamadas ocurren en este orden: leer portapapeles, escribir texto, leer clase de ventana, `xdotool key --clearmodifiers ctrl+v`, espera `PASTE_DELAY`, restaurar.
- [ ] Con la clase `gnome-terminal` (o cualquiera de `TERMINAL_CLASSES`, en cualquier capitalización) el atajo es `ctrl+shift+v`.
- [ ] Con una clase de `extra_terminals` el atajo es `ctrl+shift+v`; con otra clase, `ctrl+v`.
- [ ] Si `getwindowclassname` falla, se pega con `ctrl+v`.
- [ ] El texto se pasa a `xclip` por `stdin` y nunca como argumento de línea de comandos.
- [ ] Con el portapapeles previo vacío o ilegible, no se vuelve a escribir nada tras el pegado.
- [ ] Si falla `xclip` o `xdotool key`, se restaura el portapapeles (si se había leído), se registra el `WARNING` `Portapapeles no disponible (...)` y se inserta con `xdotool type`.
- [ ] Si el respaldo `xdotool type` falla, la excepción llega a `PushToTalk`, que registra `Error: ...` y notifica como hoy.
- [ ] `PRIMARY` no se lee ni se escribe en ningún caso.
- [ ] `speechflow` con `insert_method = "clipboard"` y sin `xclip` termina con código 1 y el `ERROR` `Falta xclip. Instálalo con: sudo apt install xclip`.
- [ ] `speechflow` con `insert_method = "type"` y sin `xclip` arranca con normalidad.
- [ ] La línea de log `Insertado (...)` y las notificaciones no cambian.
- [ ] Prueba manual: `¿Cómo estás? ñandú` se inserta íntegro en un editor, un navegador y una terminal, y el texto previo del portapapeles se recupera.
- [ ] `pytest` pasa con código 0 y no ejecuta `xclip` ni `xdotool` reales ni escribe fuera de `tmp_path`.
- [ ] `git diff main -- scripts src/speechflow/transcriber.py src/speechflow/notifier.py src/speechflow/punctuation.py` está vacío.
- [ ] `speechflow.example.toml` y `README.md` documentan `[text] insert_method`, `[text] terminal_classes` y el requisito `xclip`.

## Decisiones

- **Sí:** portapapeles por defecto, con la clave `[text] insert_method = "clipboard" | "type"`, por elección del usuario. Da la mejora a todos sin editar nada y deja una vía de vuelta al comportamiento anterior.
- **No:** sustituir `xdotool type` sin clave. No habría escape si el portapapeles falla en alguna aplicación.
- **Sí:** `xclip`, por elección del usuario. Ya está instalado en el equipo y permite leer y escribir `CLIPBOARD`; es dependencia obligatoria solo con `insert_method = "clipboard"`.
- **No:** `xsel`, Tkinter o `pyperclip`. `xsel` no está instalado y las librerías Python añaden dependencia y son menos fiables en X11 sin gestor de portapapeles.
- **Sí:** restaurar solo texto (`UTF8_STRING`) tras `PASTE_DELAY` de 0,3 s, por elección del usuario. Cubre el caso habitual con poco código; si el contenido previo no era texto, se conserva el dictado en el portapapeles.
- **No:** restaurar todos los formatos (`TARGETS`). Mucho más complejo y frágil para un caso poco frecuente.
- **Sí:** detectar la ventana con foco y usar `ctrl+shift+v` en terminales, por elección del usuario. Ctrl+V no pega en la mayoría de las terminales, y sin esto el modo por defecto fallaría justo donde más se usa.
- **Sí:** lista `TERMINAL_CLASSES` en el código más `[text] terminal_classes` que se suma, por elección del usuario. Cubre las terminales comunes y permite añadir una nueva sin tocar el código.
- **No:** lista completa solo por TOML o solo en el código. La primera obliga al usuario a mantenerla; la segunda exige editar el código para cada terminal nueva.
- **Sí:** `xdotool getwindowfocus getwindowclassname`, por elección del usuario. `xdotool` ya es obligatorio; `xprop` añadiría una dependencia (`x11-utils`) y un parseo.
- **Sí:** si falta `xclip` con `"clipboard"`, `ERROR` y salida con código 1, por elección del usuario. Es el mismo trato que `xdotool` ausente, y evita que el usuario crea que usa el portapapeles cuando no es así.
- **Sí:** solo `CLIPBOARD`, por elección del usuario. Es la selección que usan los atajos de pegado; `PRIMARY` es del usuario (texto seleccionado) y no debe pisarse.
- **Sí:** respaldo automático a `xdotool type` con `WARNING`. Decisión del diseño: un dictado perdido es peor que uno tecleado de forma menos robusta.
- **Sí:** el texto va a `xclip` por `stdin`. Decisión del diseño: evita límites de longitud de argumentos y que el dictado se vea en la lista de procesos.
- **Sí:** el contenido previo del portapapeles no se escribe en el log. Decisión del diseño: puede contener contraseñas u otros datos privados.
- **Sí:** `nueva línea` y `nuevo párrafo` pasan a pegarse como saltos de línea en modo portapapeles, sin cambiar `punctuation.py`. Decisión del diseño: es consecuencia natural del pegado y se documenta; con `"type"` siguen tecleando `Return`.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| La aplicación destino lee el portapapeles después de `PASTE_DELAY` y pega el contenido restaurado en vez del dictado | 0,3 s cubre las aplicaciones comunes; se documenta y la vuelta a `insert_method = "type"` está en el TOML. |
| Una terminal no incluida en la lista recibe `Ctrl+V` y no pega | `terminal_classes` permite añadirla; el README explica cómo ver la clase de la ventana. |
| Un gestor de historial del portapapeles registra el dictado y el contenido restaurado | Se declara fuera de alcance y se documenta como limitación. |
| `xclip` mantiene abierto un proceso en segundo plano y `subprocess.run` se cuelga esperando los flujos | `stdout` y `stderr` a `DEVNULL` y `COMMAND_TIMEOUT` en cada llamada; test con dobles que lo verifican. |
| El portapapeles previo no era texto y se pierde | Es el comportamiento acordado y se documenta. |
| Aplicaciones que ignoran `Ctrl+V` o bloquean el pegado (algunos campos de contraseña, algunas VM) | `insert_method = "type"`; el `WARNING` solo salta si falla un comando, no si el pegado no tiene efecto. |
| `getwindowclassname` devuelve vacío en algunas ventanas | Se trata como no terminal (`ctrl+v`). |
| Los dobles de `subprocess.run` no reflejan el comportamiento real de `xclip` | Prueba manual del paso 5 con `xclip` y `xdotool` reales. |

## Lo que **no** está en esta spec

- Wayland (`wl-copy`, `ydotool`).
- Restaurar imágenes, archivos u otros formatos del portapapeles.
- La selección `PRIMARY`.
- Gestores de historial del portapapeles.
- Opción de CLI o tecla para cambiar el método en caliente.
- Detección de terminales por título o proceso.
- Retardo de pegado configurable.
- Cambios en `punctuation.py`, `transcriber.py`, `notifier.py`, `audio.py` y `scripts/`.

Cada uno, si se aborda, va en su propia spec.
