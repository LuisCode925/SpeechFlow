# SPEC 07 — Log de consola verboso en push-to-talk

> **Estado:** Aprobado
> **Depende de:** SPEC 05, SPEC 06
> **Fecha:** 2026-10-05
> **Objetivo:** Hacer que cada línea de consola de `push_to_talk.py` lleve fecha, hora con milisegundos y nivel, y que el arranque y cada dictado muestren el modelo, el idioma, el dispositivo de audio y las duraciones, mediante un módulo `logging` propio.

## Por qué existe esta spec

Las SPEC 05 y 06 dejaron la consola con mensajes sueltos (`Grabando...`, `Insertado (1.03 s): ...`) sin marca de tiempo ni contexto. Como el script corre durante horas en segundo plano, al revisar la terminal no se sabe cuándo ocurrió cada evento, con qué modelo ni con qué micrófono. Esta spec añade ese contexto sin cambiar el flujo del dictado ni las notificaciones de escritorio.

## Alcance

**Dentro:**

- Crear `src/speechflow/log.py` con `setup_logging()`, que configura el logger `speechflow` con un formato único:
  `2026-10-05 14:32:07.412 INFO    Grabando...` (fecha, hora local con milisegundos, nivel y mensaje).
- Enviar `INFO` a stdout y `WARNING`/`ERROR` a stderr, igual que hoy (los errores ya van a stderr).
- Sustituir todos los `print` de `scripts/push_to_talk.py` (salvo `--list-devices`) por llamadas al logger, incluidos los avisos de arranque y los mensajes de `sys.exit`, que pasan a `logger.error(...)` seguido de `sys.exit(1)`.
- Banner de arranque tras cargar el modelo, con estas líneas `INFO`:
  - `Modelo: medium | idioma: es | compute_type: int8 | GPU`
  - `Modelo cargado en 4.82 s (incluye calentamiento)`
  - `Dispositivo de audio: [6] Realtek ALC... | 44100 Hz nativos a 16000 Hz mono`
  - `Listo. Mantén pulsada la tecla 'ctrl_r' para dictar. Ctrl+C para salir.`
- Ampliar los mensajes del ciclo de dictado conservando su texto actual como inicio del mensaje:
  - `Grabando...`
  - `Grabación terminada: 11.18 s. Transcribiendo con medium/es...`
  - `Insertado (1.03 s, 0.09x tiempo real, 112 caracteres, medium/es): <texto>`
  - `Sin texto reconocido (1.03 s, medium/es).`
  - `Grabación de 0.21 s descartada (mínimo 0.5 s).` (sin cambios)
  - Límite de 60 s: el texto actual, como `WARNING`.
  - Errores de micrófono y de transcripción o inserción: el texto actual, como `ERROR`.
- Al salir con `Ctrl+C`: `Saliendo.` y, tras `Transcriber.close()`, `Modelo medium liberado.`, ambos `INFO`.
- Pasar `model_name` al constructor de `PushToTalk` para poder escribirlo en los mensajes (el idioma ya está en `Transcriber.language`).
- Actualizar `README.md` (salida de ejemplo de la sección Push-to-talk, descripción de `log.py` y avisos) y el docstring del script si procede.

**Fuera de alcance (para futuras specs):**

- Archivo de log en disco, rotación y carpeta `logs/`.
- Opción `--quiet`, `--verbose` o niveles configurables; la verbosidad es fija.
- Aplicar el log a `capture_mic.py` y `benchmark_stt.py`.
- Cambiar `audio.py`: el aviso de estado de `PortAudio` (`print(status, file=sys.stderr)`) queda sin prefijo.
- Mensajes de `argparse` (uso y errores de opciones), que mantienen su formato propio.
- Formato JSON, colores ANSI y zona horaria en la marca de tiempo.
- Cambios en las notificaciones de escritorio (SPEC 06), `notifier.py`, `inserter.py` o `Transcriber`.
- Información de VRAM, versión de CUDA y tecla/sesión X11 en el banner.

## Modelo de datos

No hay estructuras de datos persistentes nuevas. Interfaz pública del módulo nuevo:

```python
# src/speechflow/log.py
LOGGER_NAME = "speechflow"
FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging() -> logging.Logger: ...   # idempotente; INFO a stdout, WARNING+ a stderr
```

Convenciones:

- `setup_logging()` se llama una vez al inicio de `main()`, antes de las comprobaciones de arranque, y devuelve el logger `speechflow`. Llamarla otra vez no duplica los manejadores.
- El nivel del logger es `INFO`; no hay `DEBUG`.
- La marca de tiempo usa la hora local del sistema (`time.localtime`).
- `--list-devices` sigue imprimiendo con `print` y sin prefijo: es un listado, no un evento.
- Factor de tiempo real: segundos de inferencia divididos entre segundos de audio, con dos decimales y sufijo `x`.
- Caracteres: `len(text)` del texto devuelto por `Transcriber`, sin recortes.
- Dispositivo de audio en el banner: índice (`index` de `sd.query_devices`), nombre y `default_samplerate` enteros. Si el dispositivo es el del sistema (`None`), se resuelve con `sd.query_devices(None, "input")`.

## Plan de implementación

1. Crear `src/speechflow/log.py` con `setup_logging()`: dos manejadores (stdout con filtro `levelno < WARNING`, stderr con nivel `WARNING`), un solo `Formatter`, sin propagación al logger raíz e idempotente. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.log import setup_logging; l = setup_logging(); setup_logging(); l.info('a'); l.error('b')"` imprime dos líneas con el formato esperado, una en stdout y otra en stderr, cada una una sola vez.
2. En `scripts/push_to_talk.py`, llamar a `setup_logging()` al inicio de `main()` y sustituir los `print` y `sys.exit(mensaje)` del arranque (xdotool, sesión, `notify-send`, `--key`, dispositivo) por `logger.warning` / `logger.error` + `sys.exit(1)`, sin cambiar sus textos. Verificar: `--key tecla_falsa` imprime una línea `ERROR` con prefijo en stderr y sale con código 1; sin `xdotool` (simulado con `PATH`) sale con el mensaje `sudo apt install xdotool`.
3. Añadir el banner de arranque: medir el tiempo de `Transcriber(...)` con `time.perf_counter`, consultar el dispositivo con `sd.query_devices` e imprimir las cuatro líneas `INFO`. Verificar: arrancar el script muestra el banner con modelo, idioma, `compute_type`, tiempo de carga y dispositivo, cada línea con marca de tiempo.
4. Pasar `model_name` a `PushToTalk` y migrar los mensajes del ciclo (grabando, terminada, descartada, límite, insertado, sin texto, errores) al logger con los textos del alcance. Verificar: un dictado completo muestra `Grabando...`, `Grabación terminada: ... con medium/es...` e `Insertado (... caracteres, medium/es): ...`; un toque corto muestra el mensaje de descartada.
5. Migrar `Saliendo.` y añadir `Modelo {model} liberado.` tras `transcriber.close()`. Verificar: `Ctrl+C` imprime ambas líneas con prefijo, en ese orden, y la notificación `Modelo liberado` sigue apareciendo.
6. Actualizar `README.md` con la salida de ejemplo nueva, `log.py` en la lista de módulos y la nota sobre stdout/stderr. Verificar: el ejemplo del README coincide con la salida real del script.

## Criterios de aceptación

- [ ] `src/speechflow/log.py` existe y expone `setup_logging()`, `LOGGER_NAME`, `FORMAT` y `DATE_FORMAT`.
- [ ] Llamar dos veces a `setup_logging()` no duplica ninguna línea.
- [ ] Toda línea de consola de `push_to_talk.py` durante el arranque y el dictado empieza con `AAAA-MM-DD HH:MM:SS.mmm` y el nivel.
- [ ] Las líneas `INFO` salen por stdout y las `WARNING` y `ERROR` por stderr.
- [ ] El banner muestra modelo, idioma, `compute_type`, tiempo de carga del modelo y dispositivo de audio (índice, nombre y tasa nativa).
- [ ] Con `--model small --language en`, el banner y los mensajes de dictado dicen `small` y `en`.
- [ ] Con `--device` apuntando a otro micrófono, el banner muestra el índice y el nombre de ese dispositivo.
- [ ] `Grabación terminada` y `Insertado` incluyen el modelo y el idioma; `Insertado` incluye segundos de inferencia, factor de tiempo real y número de caracteres.
- [ ] Mantener la tecla más de 60 s imprime el aviso de límite con nivel `WARNING`.
- [ ] Un fallo al abrir el micrófono y un fallo al transcribir o insertar se registran con nivel `ERROR`, y las notificaciones de error de la SPEC 06 se mantienen.
- [ ] `Ctrl+C` imprime `Saliendo.` y `Modelo medium liberado.` con prefijo, y sigue apareciendo la notificación `Modelo liberado`.
- [ ] `--key tecla_falsa`, un `--device` inexistente y la falta de `xdotool` terminan con código 1 y una línea `ERROR` con prefijo.
- [ ] `--list-devices` imprime el mismo listado que antes, sin prefijo.
- [ ] Las notificaciones de escritorio son exactamente las de la SPEC 06.
- [ ] `capture_mic.py` y `benchmark_stt.py` producen la misma salida que antes.
- [ ] `README.md` muestra la salida con prefijos y menciona `log.py`.

## Decisiones

- **Sí:** módulo `logging` de la biblioteca estándar en `src/speechflow/log.py`, por elección del usuario. Da niveles, formato único y separación stdout/stderr sin dependencias; los scripts futuros lo reutilizan.
- **No:** helper propio de `print` ni `print` editados a mano. Duplican el formato y divergen con cada script nuevo.
- **Sí:** solo `push_to_talk.py`, solo consola, por elección del usuario. Es el proceso largo donde importa el contexto; `capture_mic.py` y el benchmark son ejecuciones cortas.
- **No:** archivo de log en disco. Añade ruta, rotación y `.gitignore`; es otra spec si hace falta.
- **Sí:** marca de tiempo local con milisegundos (`2026-10-05 14:32:07.412`), por elección del usuario. Permite medir la latencia entre eventos, como pulsar y soltar.
- **No:** ISO 8601 con zona. Es más largo y no aporta en una terminal local.
- **Sí:** "interfaz" significa dispositivo de audio (índice, nombre, tasa nativa), por elección del usuario. Es lo que el script ya resuelve en `default_device()` y `Recorder`.
- **No:** mostrar tecla, sesión X11, VRAM o versión de CUDA en el banner. El usuario eligió solo modelo, idioma, `compute_type`, tiempo de carga y dispositivo.
- **Sí:** el banner incluye el tiempo de carga del modelo, por elección del usuario. Distingue arranques con descarga o caché fría de los normales.
- **Sí:** el nivel de log aparece en cada línea, por elección del usuario. Separa de un vistazo avisos y errores del flujo normal.
- **Sí:** modelo e idioma en `Grabación terminada` e `Insertado`, y duración, factor de tiempo real y caracteres en `Insertado`, por elección del usuario.
- **Sí:** verbosidad fija, sin `--quiet`. La SPEC 06 ya descartó la configurabilidad y se mantiene el criterio; un segundo formato doblaría lo que probar.
- **Sí:** ampliar los mensajes existentes conservando su texto inicial, por elección del usuario. Esto reemplaza el criterio de la SPEC 06 "mensajes de consola intactos": desde esta spec la consola cambia de forma deliberada. Los criterios de consola de las SPEC 05 y 06 se leen sin el prefijo y sin los campos añadidos.
- **Sí:** errores y avisos de arranque pasan por el logger con `sys.exit(1)`. Toda línea del script en ejecución lleva prefijo y nivel, y el código de salida es explícito.
- **Sí:** `model_name` se pasa a `PushToTalk` en lugar de añadir un atributo a `Transcriber`. Evita tocar un módulo cuya interfaz cerró la SPEC 04.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El logger duplica líneas si `setup_logging()` se llama más de una vez o si el logger raíz también imprime | `setup_logging()` es idempotente y desactiva la propagación (`propagate = False`); un criterio de aceptación lo comprueba. |
| stdout y stderr se entrelazan en el orden en la terminal por el búfer de stdout | Con `StreamHandler` y `flush` tras cada registro, el orden se conserva; se verifica en el paso 2 con un error durante el arranque. |
| Una línea `Insertado` con texto largo rompe la lectura | El texto se muestra completo, como en la SPEC 05; recortarlo queda fuera de alcance. |
| `sd.query_devices(...)` no incluye la clave `index` según la versión de `sounddevice` | Se toma el índice de `--device`/`default_device()` cuando es entero y, si no, de la posición en `sd.query_devices()`; el paso 3 lo verifica con `--device` por nombre. |
| El aviso de estado de `PortAudio` en `audio.py` sale sin prefijo | Aceptado y documentado; `audio.py` también lo usa `capture_mic.py`, fuera de alcance. |
| Los criterios de consola de las SPEC 05 y 06 dejan de cumplirse literalmente | La decisión lo declara; esta spec pasa a ser la referencia del formato de consola. |

## Lo que **no** está en esta spec

- Archivo de log, rotación y carpeta `logs/`.
- Opciones `--quiet` / `--verbose` y niveles configurables.
- Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py`.
- Formato JSON, colores y zona horaria.
- VRAM, versión de CUDA, tecla y sesión X11 en el banner.
- Cambios en las notificaciones de escritorio.

Cada uno, si se aborda, va en su propia spec.
