# TODO — Ideas pendientes

Ideas recogidas de la sección "Lo que **no** está en esta spec" de las SPEC 01–08, sin duplicados y sin las que ya se han implementado. Entre paréntesis, la spec de origen. Cada idea, si se aborda, va en su propia spec.

## Fase 2 — Base sólida (roadmap)

Orden y dependencias: 13 → 14 → 15 → 16.

- [x] ~~SPEC 13: mover la app de `scripts/push_to_talk.py` a `src/speechflow/app.py`, sin cambios de comportamiento.~~
- [x] ~~SPEC 14: `pyproject.toml`, comando `speechflow`, `python -m speechflow` y rutas de configuración/estado independientes del repo.~~
- [x] ~~SPEC 15: cierre limpio ante `SIGTERM`/`SIGHUP` y espera a la transcripción en curso.~~
- [x] ~~SPEC 16: tests con `pytest` (config, audio, `PushToTalk` con dobles; los que usen GPU, marcados y excluidos por defecto).~~
- [x] ~~SPEC 17: log rotativo en `$XDG_STATE_HOME/speechflow/speechflow.log` (1 MB x 3 copias, permisos `0600`).~~

Fase 3 (después): servicio `systemd` de usuario y bandeja del sistema.

## Fase 3 — Antes de la GUI (roadmap)

Orden recomendado: 1 → 2 → 4 → 8 → 10 → 9. La GUI será una capa fina sobre estado, historial y canal de control. Los ítems 1, 2, 3, 4, 5, 9 y 11 repiten ideas de las secciones de abajo; al implementarlos, márcalos en ambos sitios.

Alto valor, esfuerzo bajo:

- [x] ~~1. VAD (`vad_filter` de `faster-whisper`, Silero) y recorte de silencios: menos alucinaciones en silencio y transcripción más rápida.~~ (SPEC 18, `[model] vad`)
- [x] ~~2. Cambio de idioma en caliente (es/en) con tecla nueva en `[keys]`, y detección automática de idioma como modo opcional.~~ (SPEC 19, `[keys] language` y `[keys] auto`)
- [x] ~~3. Opciones `--quiet` / `--verbose` y niveles de log configurables.~~ (SPEC 24, `[log] level`, `[log] file_level`)
- [x] ~~4. Modo toggle (pulsar para empezar, pulsar para parar), para dictados largos.~~ (SPEC 20, `[recording] mode`)

Valor medio:

- [x] ~~5. Inserción por portapapeles (Ctrl+V), más robusta que `xdotool type` con acentos y caracteres raros; restaurar el portapapeles después.~~ (SPEC 25, `[text] insert_method`)
- [x] ~~6. Diccionario de reemplazos del usuario (`[replacements]` en TOML) e `initial_prompt` configurable para sesgar el vocabulario.~~ (SPEC 27)
- [x] ~~7. Comandos de voz de puntuación ("punto", "coma", "nueva línea").~~ (SPEC 21, `[text] punctuation_commands`)
- [x] ~~8. Historial de transcripciones (JSONL en `state_dir()`); la GUI lo necesitará y permite recuperar un dictado perdido.~~ (SPEC 26, `[history]`)

Base para la GUI:

- [x] ~~9. Daemon y servicio `systemd` de usuario (la GUI o bandeja será cliente del proceso).~~ (SPEC 28, `speechflow service install`)
- [ ] 10. Canal de control (socket Unix o señales): pausar, cambiar idioma o dispositivo, consultar estado. Es la dependencia real de la GUI.
- [x] ~~11. Fallback a CPU si falla CUDA, para que el servicio no muera al arrancar.~~ (SPEC 22, `[model] device = "auto"`)

Pueden esperar: soporte Wayland y reducción de ruido.

## Audio y captura

- [x] ~~VAD (detección de actividad de voz) y recorte de silencios (SPEC 01, 03, 04, 05).~~ (SPEC 18, con `vad_filter` de `faster-whisper`; sin recorte propio)
- [ ] Streaming de la captura y de la transcripción (SPEC 03, 04, 05).
- [ ] Reducción de ruido (SPEC 03).
- [x] ~~Persistencia del dispositivo de audio elegido entre ejecuciones (SPEC 08).~~ (SPEC 10)
- [ ] Cambio de dispositivo por otros medios: stdin, señales, bandeja o menú gráfico (SPEC 08).
- [ ] Retroceder en la rotación, elegir por índice o por nombre en caliente, y listas de rotación configurables (SPEC 08).
- [ ] Cambio automático al conectar, desconectar o fallar un dispositivo (SPEC 08).
- [ ] Diferir el cambio de dispositivo hasta que el estado sea `IDLE` (SPEC 08).
- [ ] Comprobar que el dispositivo abre al cambiarlo (SPEC 08).

## Transcripción

- [x] ~~Detección automática de idioma (SPEC 04).~~ (SPEC 19, restringida a es/en)
- [x] ~~Cambio de idioma en caliente (SPEC 05).~~ (SPEC 19)
- [x] ~~Fallback a CPU (SPEC 01).~~ (SPEC 22)
- [ ] Fallback a la nube (SPEC 01).
- [ ] Más modelos o compute types en el benchmark, y audios largos (SPEC 02).
- [ ] Medición de WER (SPEC 02, 03, 04, 05).

## Entrada y salida de texto

- [x] ~~Modo toggle~~ (SPEC 20, `[recording] mode`).
- [ ] Combinaciones de varias teclas (SPEC 05).
- [x] ~~Inserción por portapapeles~~ (SPEC 25, `[text] insert_method`).
- [ ] Soporte Wayland y `ydotool` (`wl-copy`, `wl-paste`) (SPEC 01, 05).

## Ejecución en segundo plano

- [ ] Bandeja del sistema (SPEC 01, 03, 04, 05).
- [x] ~~Daemon, arranque automático y `systemd` (SPEC 03, 04, 05).~~ (SPEC 28)
- [x] ~~Descarga del modelo por inactividad y recarga bajo demanda (SPEC 06).~~ (SPEC 12)
- [x] ~~Esperar a una transcripción en curso al salir (SPEC 06).~~ (SPEC 15)
- [x] ~~Liberar el modelo en señales distintas de `Ctrl+C` (SPEC 06).~~ (SPEC 15)

## Configuración

- [x] ~~Archivo de configuración de usuario (SPEC 01, 05).~~ (SPEC 10)
- [x] ~~Opciones o archivo de configuración para las notificaciones (SPEC 06).~~ (SPEC 10)

## Log y diagnóstico

- [x] ~~Archivo de log, rotación y carpeta `logs/` (SPEC 07).~~ (SPEC 17, en `state_dir()` y sin carpeta `logs/`)
- [x] ~~Opciones `--quiet` / `--verbose` y niveles configurables (SPEC 07).~~ (SPEC 24)
- [ ] Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py` (SPEC 07).
- [ ] Formato JSON, colores y zona horaria en el log (SPEC 07).
- [ ] Mostrar VRAM, versión de CUDA, tecla y sesión X11 en el banner de arranque (SPEC 07).
- [ ] Cambios en las notificaciones de escritorio (SPEC 07).

## Calidad y empaquetado

- [x] ~~Empaquetado (`pyproject.toml`) y `python -m speechflow` (SPEC 04, 05).~~ (SPEC 14)
- [x] ~~Tests con `pytest` (SPEC 04, 05).~~ (SPEC 16)

## Criterios de aceptación pendientes de verificar (SPEC 14)

- [ ] `conda env create -f environment.yml` en un entorno limpio instala el paquete y deja `speechflow` en el `PATH` del entorno.
- [ ] `scripts/benchmark_stt.py` no cambia y produce la misma salida que antes (`git diff main -- scripts/benchmark_stt.py` vacío).
- [ ] La vigilancia del micrófono, la descarga por inactividad y la salida con `Ctrl+C` producen los mismos mensajes y notificaciones que antes, salvo las rutas.
