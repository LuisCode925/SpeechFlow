# TODO — Ideas pendientes

Ideas recogidas de la sección "Lo que **no** está en esta spec" de las SPEC 01–08, sin duplicados y sin las que ya se han implementado. Entre paréntesis, la spec de origen. Cada idea, si se aborda, va en su propia spec.

## Audio y captura

- [ ] Streaming de la captura y de la transcripción (SPEC 03, 04, 05).
- [ ] Reducción de ruido (SPEC 03).
- [ ] Cambio de dispositivo por otros medios: stdin, señales, bandeja o menú gráfico (SPEC 08). Cubierto por el socket (SPEC 29, `speechflow ctl device`); quedan señales, bandeja y menú gráfico.
- [ ] Retroceder en la rotación, ~~elegir por índice o por nombre en caliente~~ (SPEC 29, `ctl device`), y listas de rotación configurables (SPEC 08).
- [ ] Cambio automático al conectar, desconectar o fallar un dispositivo (SPEC 08).
- [ ] Diferir el cambio de dispositivo hasta que el estado sea `IDLE` (SPEC 08).
- [ ] Comprobar que el dispositivo abre al cambiarlo (SPEC 08).

## Transcripción

- [ ] Fallback a la nube (SPEC 01).
- [ ] Más modelos o compute types en el benchmark, y audios largos (SPEC 02).
- [ ] Medición de WER (SPEC 02, 03, 04, 05).

## Entrada y salida de texto

- [ ] Combinaciones de varias teclas (SPEC 05).
- [ ] Soporte Wayland y `ydotool` (`wl-copy`, `wl-paste`) (SPEC 01, 05).

## Ejecución en segundo plano

- [ ] Bandeja del sistema (SPEC 01, 03, 04, 05).
- [ ] Acelerar el arranque de `speechflow ctl` (SPEC 29). Hoy tarda ~0,75 s (`import speechflow.control` solo tarda ~30 ms) porque `main()` está en `app.py`, cuyo import (~0,67 s) ocurre antes de delegar. Reparto del import: `speechflow.audio` ~480 ms (arrastra `scipy.signal`), `speechflow.config` → `transcriber` → `faster_whisper` ~120 ms, más `sounddevice` y `pynput`. Opciones, de menos a más cambio:
  - Despachar `ctl` antes de importar `app`: módulo ligero (`speechflow/cli.py` o `__main__.py`) que mira `sys.argv` e importa `app` solo si no es `ctl`, y entry point de `pyproject.toml` apuntando a él. Deja `ctl` en ~50 ms sin tocar `audio.py` ni `transcriber.py`. Opción recomendada.
  - Imports perezosos: `scipy` dentro de `resample()`, `faster_whisper` dentro de `Transcriber`, `sounddevice` y `pynput` al usarse. Toca `audio.py` y `transcriber.py` y también acelera el arranque normal del servicio.
  - Entry point aparte `speechflowctl`: mismo efecto que despachar antes, pero duplica el empaquetado (descartado en la SPEC 29).
  - Cliente que no sea Python (script con `socat` o binario pequeño): arranque en milisegundos, pero añade una dependencia y pierde el formato legible.
  - GUI o bandeja hablando directamente con el socket: el arranque de `ctl` deja de importar para el uso interactivo.

## Log y diagnóstico

- [ ] Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py` (SPEC 07).
- [ ] Formato JSON, colores y zona horaria en el log (SPEC 07).
- [ ] Mostrar VRAM, versión de CUDA, tecla y sesión X11 en el banner de arranque (SPEC 07).
- [ ] Cambios en las notificaciones de escritorio (SPEC 07).

## Criterios de aceptación pendientes de verificar (SPEC 14)

- [ ] `conda env create -f environment.yml` en un entorno limpio instala el paquete y deja `speechflow` en el `PATH` del entorno.
- [ ] `scripts/benchmark_stt.py` no cambia y produce la misma salida que antes (`git diff main -- scripts/benchmark_stt.py` vacío).
- [ ] La vigilancia del micrófono, la descarga por inactividad y la salida con `Ctrl+C` producen los mismos mensajes y notificaciones que antes, salvo las rutas.
