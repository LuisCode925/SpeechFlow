# SPEC 05 — Push-to-talk con atajo global

> **Estado:** Implementado
> **Depende de:** SPEC 03, SPEC 04
> **Fecha:** 2026-10-04
> **Objetivo:** Dictar en cualquier aplicación de X11 manteniendo pulsada una tecla global (`Right Ctrl` por defecto): grabar mientras está pulsada, transcribir al soltar y escribir el texto en la ventana con foco.

## Por qué existe esta spec

Las SPEC 03 y 04 validaron la captura del micrófono y dejaron un `Transcriber` reutilizable. Falta unirlos con un disparador global y una salida: es el primer paso donde SpeechFlow cumple su meta de dictar "en cualquier parte del sistema". Para reutilizar la captura sin duplicarla, esta spec extrae también `src/speechflow/audio.py`, que la SPEC 04 dejó fuera de alcance.

## Alcance

**Dentro:**

- Crear `src/speechflow/audio.py` extrayendo de `scripts/capture_mic.py`: `list_devices`, `parse_device`, `default_device`, `resample`, `measure`, `save_wav` y las constantes de captura, más una clase `Recorder` con `start()` / `stop()` que graba a la tasa nativa del dispositivo y devuelve `int16` mono a 16 kHz.
- Modificar `scripts/capture_mic.py` para que use `audio.py` sin cambiar opciones, salida ni comportamiento.
- Crear `src/speechflow/inserter.py` con `insert_text(text)`, que escribe el texto en la ventana con foco mediante `xdotool type`.
- Crear `src/speechflow/notifier.py` con `notify(title, body)`, que envía una notificación de escritorio con `notify-send`.
- Crear `scripts/push_to_talk.py`: carga el `Transcriber` una vez, escucha la tecla global con `pynput` y ejecuta el ciclo grabar → transcribir → insertar, hasta `Ctrl+C`.
- Opciones de `push_to_talk.py`: `--list-devices`, `--device`, `--model` (defecto `medium`), `--language` (defecto `es`) y `--key` (nombre de tecla de `pynput`, defecto `ctrl_r`).
- Ignorar grabaciones de menos de 0.5 s y cortar sola la grabación a los 60 s.
- Mensajes de estado en consola y notificaciones de escritorio (grabando, transcribiendo, texto insertado, error).
- Añadir `pynput` (pip) a `environment.yml`.
- Documentar en `README.md` el uso y los paquetes de sistema (`xdotool`, `libnotify-bin`).

**Fuera de alcance (para futuras specs):**

- Icono de bandeja, daemon, arranque automático con la sesión y servicio `systemd`.
- Modo toggle (pulsar para empezar, pulsar para parar) y combinaciones de varias teclas.
- VAD, recorte de silencios, streaming hacia el modelo y transcripción por trozos.
- Wayland, `wtype`, `ydotool` y la inserción por portapapeles (`xclip` + `Ctrl+V`).
- Detección o cambio de idioma en caliente, cambio de tecla sin reiniciar y archivo de configuración.
- Empaquetado (`pyproject.toml`, `pip install -e .`), `python -m speechflow` y tests con `pytest`.
- Comandos de voz, puntuación automática y post-procesado del texto.
- Medir calidad (WER).

## Modelo de datos

No hay estructuras persistentes nuevas. Interfaz pública de los módulos nuevos (firmas, no implementación):

```python
# src/speechflow/audio.py
SAMPLE_RATE = 16000        # se reexporta desde transcriber o se mueve aquí; una sola definición
CHANNELS = 1
DTYPE = "int16"
PREFERRED_DEVICE = "Realtek"

class Recorder:
    def __init__(self, device: int | str | None = None) -> None: ...
    def start(self) -> None: ...                 # abre InputStream a la tasa nativa y empieza a acumular
    def stop(self) -> np.ndarray: ...            # cierra y devuelve int16 mono a SAMPLE_RATE

# src/speechflow/inserter.py
def insert_text(text: str) -> None: ...          # xdotool type --clearmodifiers -- <text>

# src/speechflow/notifier.py
def notify(title: str, body: str = "") -> None: ...   # notify-send; no lanza si no está instalado
```

Constantes y estado de `scripts/push_to_talk.py`:

```python
DEFAULT_KEY = "ctrl_r"     # nombre de pynput.keyboard.Key, o un carácter suelto
MIN_SECONDS = 0.5          # por debajo no se transcribe ni se escribe nada
MAX_SECONDS = 60.0         # la grabación se corta sola

# Estados: IDLE -> RECORDING -> TRANSCRIBING -> IDLE
```

Convenciones:

- `Recorder.stop()` devuelve `int16` mono a 16 kHz, el contrato de `Transcriber.transcribe()`.
- Una pulsación solo inicia grabación en `IDLE` y si la tecla estuvo suelta antes; las repeticiones automáticas de teclado y las pulsaciones durante `TRANSCRIBING` se ignoran.
- El texto se inserta tal cual lo devuelve `Transcriber` (sin espacio ni salto de línea añadidos).

## Plan de implementación

1. Actualizar el entorno y los paquetes de sistema: añadir `pynput` a `environment.yml` (sección pip) e instalar `xdotool` y `libnotify-bin` con `apt`. Verificar: `python -c "import pynput"`, `xdotool --version` y `notify-send "prueba"` funcionan.
2. Crear `src/speechflow/audio.py` moviendo desde `scripts/capture_mic.py` las funciones y constantes de captura, y añadir `Recorder`. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.audio import Recorder; print(Recorder)"` no falla.
3. Cambiar `scripts/capture_mic.py` para importar de `audio.py` y usar `Recorder` entre las dos pulsaciones de Enter. Eliminar el código movido. Verificar: `python scripts/capture_mic.py --list-devices` y una grabación completa dan la misma salida que antes.
4. Crear `src/speechflow/inserter.py` y `src/speechflow/notifier.py`. `insert_text` con texto vacío no hace nada; `notify` ignora el error si falta `notify-send`. Verificar: abrir un editor, ejecutar `sleep 3; python -c "import sys; sys.path.insert(0, 'src'); from speechflow.inserter import insert_text; insert_text('áéíóú ñ ¿qué?')"` y enfocar el editor; el texto aparece completo.
5. Crear `scripts/push_to_talk.py` con `--list-devices`, `--device`, `--model`, `--language`, `--key` y el arranque: comprobar que existe `xdotool` (si no, salir con mensaje claro), cargar el `Transcriber` e imprimir la tecla activa. Verificar: `python scripts/push_to_talk.py --key ctrl_r` imprime que está listo y termina limpio con `Ctrl+C`; `--key tecla_falsa` falla con un mensaje claro.
6. Implementar el ciclo con `pynput.keyboard.Listener`: al pulsar la tecla en `IDLE` arranca `Recorder` y notifica; al soltarla, `stop()`. Verificar: mantener `Right Ctrl` en otra ventana imprime "Grabando..." y al soltar imprime la duración.
7. Completar el ciclo: descartar audios de menos de `MIN_SECONDS`, cortar a `MAX_SECONDS` con un temporizador, transcribir en un hilo aparte (el listener no se bloquea), insertar con `insert_text` y notificar el resultado o el error. Verificar: dictar una frase en un editor de texto y verla escrita; un toque corto no escribe nada.
8. Actualizar `README.md` con la sección del push-to-talk. Verificar: los comandos y opciones del README coinciden con el script.

## Criterios de aceptación

- [ ] `conda env update -f environment.yml` termina sin errores y `import pynput` funciona.
- [ ] `src/speechflow/audio.py`, `src/speechflow/inserter.py` y `src/speechflow/notifier.py` existen con las interfaces del modelo de datos.
- [ ] `scripts/capture_mic.py` ya no define `record`, `resample`, `measure` ni `save_wav`, y su salida y opciones (`--list-devices`, `--device`, `--model`, `--language`, `--output`) siguen igual.
- [ ] `python scripts/push_to_talk.py` carga el modelo una sola vez al arrancar y queda a la escucha hasta `Ctrl+C`.
- [ ] Mantener `Right Ctrl` en un editor de texto y decir una frase en español escribe esa frase en el editor al soltar.
- [ ] El texto con `á é í ó ú ñ ¿ ?` se escribe sin caracteres perdidos ni cambiados.
- [ ] Dos dictados seguidos funcionan sin reiniciar el script ni recargar el modelo.
- [ ] Una pulsación de menos de 0.5 s no escribe nada y no invoca al modelo.
- [ ] Mantener la tecla más de 60 s corta la grabación, transcribe lo grabado y avisa; no empieza otra grabación hasta soltar y volver a pulsar.
- [ ] Pulsar la tecla mientras se transcribe no inicia otra grabación.
- [ ] `--key f9` cambia la tecla de disparo; una tecla inválida falla con un mensaje claro.
- [ ] Si falta `xdotool`, el script sale al arrancar con un mensaje que indica `sudo apt install xdotool`.
- [ ] Si falta `notify-send`, el script avisa una vez por consola y sigue funcionando solo con mensajes de consola.
- [ ] Un dispositivo inexistente en `--device` falla con un mensaje claro, igual que en `capture_mic.py`.
- [ ] La transcripción de ~10 s tarda menos de 2 s con `medium` int8, sin contar la carga del modelo.
- [ ] `README.md` documenta el script, sus opciones y los paquetes de sistema necesarios.

## Decisiones

- **Sí:** mantener pulsada una tecla (hold), por elección del usuario. Es el push-to-talk estricto y no requiere un segundo gesto para parar.
- **No:** modo toggle ahora. Cambia el modelo de interacción y se evalúa en otra spec si hace falta.
- **Sí:** `Right Ctrl` como tecla por defecto, por elección del usuario. Una tecla modificadora sola casi nunca choca con atajos de aplicaciones y es cómoda de mantener.
- **No:** combinaciones como `Ctrl+Alt+Espacio` por defecto. Exigen varios dedos y gestionar el estado de varias teclas.
- **Sí:** `--key` acepta nombres de `pynput.keyboard.Key` o un carácter suelto, para poder cambiar la tecla sin tocar código.
- **Sí:** `xdotool type` para insertar, por elección del usuario. Escribe en la ventana con foco sin tocar el portapapeles y funciona en terminales, donde `Ctrl+V` no.
- **No:** `xclip` + `Ctrl+V`. Sobrescribe el portapapeles del usuario y falla en terminales.
- **No:** Wayland. La sesión del proyecto es X11 (ver Requisitos del `README.md`) y `xdotool` solo funciona ahí.
- **Sí:** `xdotool type --clearmodifiers` por seguridad, aunque `Right Ctrl` ya está suelto cuando se escribe, porque la transcripción ocurre tras soltar.
- **Sí:** extraer `src/speechflow/audio.py` en esta misma spec, por elección del usuario. El push-to-talk necesita la captura y duplicarla del script sería deuda inmediata.
- **No:** duplicar la captura en `push_to_talk.py`. Dos copias del remuestreo y del dispositivo preferido divergen.
- **Sí:** `Recorder` con `start()` / `stop()` en lugar de la función `record()` con `input()`. El push-to-talk necesita iniciar y parar desde eventos de teclado, no desde Enter.
- **Sí:** script en primer plano en `scripts/push_to_talk.py`, por elección del usuario. Daemon, bandeja y `python -m speechflow` van en otra spec.
- **Sí:** consola más `notify-send`, por elección del usuario. El usuario dicta en otra ventana y no ve la terminal.
- **Sí:** descartar grabaciones de menos de 0.5 s, por elección del usuario. Evita escribir texto basura por toques accidentales; se asume perder palabras monosílabas muy cortas.
- **Sí:** corte automático a 60 s, por elección del usuario. Protege la memoria si la tecla se queda atascada.
- **Sí:** transcribir en un hilo aparte. El callback del listener de `pynput` no debe bloquearse con la inferencia.
- **Sí:** el modelo se carga al arrancar el script, no tras la primera grabación. A diferencia de `capture_mic.py`, aquí cada dictado debe responder rápido.
- **Sí:** `pynput` por pip dentro de `environment.yml`, como `faster-whisper`; no hay paquete conda equivalente que valga la pena.
- **No:** `pytest` ni empaquetado, igual que en la SPEC 04. Verificación manual con micrófono y editor.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `pynput` no recibe teclas globales si la sesión es Wayland o `XWayland` aislado | El proyecto declara X11 como requisito; el script comprueba `XDG_SESSION_TYPE` y avisa si no es `x11`. |
| `Right Ctrl` se usa a la vez en otro atajo (p. ej. `Ctrl+C`) y graba sin querer | El umbral de 0.5 s descarta los toques; se puede cambiar la tecla con `--key`. |
| La tecla pulsada se repite por autorepetición del teclado | El estado `IDLE`/`RECORDING` y el indicador de tecla pulsada ignoran las repeticiones. |
| `xdotool type` pierde o cambia caracteres según el layout del teclado | El criterio de aceptación exige probar `áéíóúñ¿?`; si falla se documenta y se evalúa el portapapeles en otra spec. |
| Escribir antes de que la ventana recupere el foco inserta en el lugar equivocado | El texto se escribe en la ventana con foco al terminar la transcripción; aceptado y documentado en el README. |
| Tecla atascada graba indefinidamente | Corte a `MAX_SECONDS` y no se rearma hasta que la tecla se suelta. |
| `Recorder` cambia el comportamiento de `capture_mic.py` | El paso 3 compara su salida con la anterior y un criterio de aceptación lo exige. |
| Falta `notify-send` o `xdotool` en el sistema | `xdotool` es obligatorio y se comprueba al arrancar; `notify-send` es opcional y se degrada a consola. |

## Lo que **no** está en esta spec

- Bandeja, daemon, arranque automático y `systemd`.
- Modo toggle y combinaciones de varias teclas.
- VAD, streaming y recorte de silencios.
- Wayland, `ydotool` e inserción por portapapeles.
- Cambio de idioma en caliente y archivo de configuración.
- Empaquetado, `python -m speechflow`, `pytest` y WER.

Cada uno, si se aborda, va en su propia spec.
