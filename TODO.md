# TODO — Ideas pendientes

Ideas recogidas de la sección "Lo que **no** está en esta spec" de las SPEC 01–08, sin duplicados y sin las que ya se han implementado. Entre paréntesis, la spec de origen. Cada idea, si se aborda, va en su propia spec.

## Fase 2 — Base sólida (roadmap)

Orden y dependencias: 13 → 14 → 15 → 16.

- [x] ~~SPEC 13: mover la app de `scripts/push_to_talk.py` a `src/speechflow/app.py`, sin cambios de comportamiento.~~
- [x] ~~SPEC 14: `pyproject.toml`, comando `speechflow`, `python -m speechflow` y rutas de configuración/estado independientes del repo.~~
- [ ] SPEC 15: cierre limpio ante `SIGTERM`/`SIGHUP` y espera a la transcripción en curso.
- [ ] SPEC 16: tests con `pytest` (config, audio, `PushToTalk` con dobles; los que usen GPU, marcados y excluidos por defecto).

Fase 3 (después): servicio `systemd` de usuario, archivo de log con rotación y bandeja del sistema.

## Audio y captura

- [ ] VAD (detección de actividad de voz) y recorte de silencios (SPEC 01, 03, 04, 05).
- [ ] Streaming de la captura y de la transcripción (SPEC 03, 04, 05).
- [ ] Reducción de ruido (SPEC 03).
- [x] ~~Persistencia del dispositivo de audio elegido entre ejecuciones (SPEC 08).~~ (SPEC 10)
- [ ] Cambio de dispositivo por otros medios: stdin, señales, bandeja o menú gráfico (SPEC 08).
- [ ] Retroceder en la rotación, elegir por índice o por nombre en caliente, y listas de rotación configurables (SPEC 08).
- [ ] Cambio automático al conectar, desconectar o fallar un dispositivo (SPEC 08).
- [ ] Diferir el cambio de dispositivo hasta que el estado sea `IDLE` (SPEC 08).
- [ ] Comprobar que el dispositivo abre al cambiarlo (SPEC 08).

## Transcripción

- [ ] Detección automática de idioma (SPEC 04).
- [ ] Cambio de idioma en caliente (SPEC 05).
- [ ] Fallback a CPU o a la nube (SPEC 01).
- [ ] Más modelos o compute types en el benchmark, y audios largos (SPEC 02).
- [ ] Medición de WER (SPEC 02, 03, 04, 05).

## Entrada y salida de texto

- [ ] Modo toggle y combinaciones de varias teclas (SPEC 05).
- [ ] Soporte Wayland, `ydotool` e inserción por portapapeles (SPEC 01, 05).

## Ejecución en segundo plano

- [ ] Bandeja del sistema (SPEC 01, 03, 04, 05).
- [ ] Daemon, arranque automático y `systemd` (SPEC 03, 04, 05).
- [x] ~~Descarga del modelo por inactividad y recarga bajo demanda (SPEC 06).~~ (SPEC 12)
- [ ] Esperar a una transcripción en curso al salir (SPEC 06).
- [ ] Liberar el modelo en señales distintas de `Ctrl+C` (SPEC 06).

## Configuración

- [x] ~~Archivo de configuración de usuario (SPEC 01, 05).~~ (SPEC 10)
- [x] ~~Opciones o archivo de configuración para las notificaciones (SPEC 06).~~ (SPEC 10)

## Log y diagnóstico

- [ ] Archivo de log, rotación y carpeta `logs/` (SPEC 07).
- [ ] Opciones `--quiet` / `--verbose` y niveles configurables (SPEC 07).
- [ ] Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py` (SPEC 07).
- [ ] Formato JSON, colores y zona horaria en el log (SPEC 07).
- [ ] Mostrar VRAM, versión de CUDA, tecla y sesión X11 en el banner de arranque (SPEC 07).
- [ ] Cambios en las notificaciones de escritorio (SPEC 07).

## Calidad y empaquetado

- [x] ~~Empaquetado (`pyproject.toml`) y `python -m speechflow` (SPEC 04, 05).~~ (SPEC 14)
- [ ] Tests con `pytest` (SPEC 04, 05).

## Criterios de aceptación pendientes de verificar (SPEC 14)

- [ ] `conda env create -f environment.yml` en un entorno limpio instala el paquete y deja `speechflow` en el `PATH` del entorno.
- [ ] `scripts/benchmark_stt.py` no cambia y produce la misma salida que antes (`git diff main -- scripts/benchmark_stt.py` vacío).
- [ ] La vigilancia del micrófono, la descarga por inactividad y la salida con `Ctrl+C` producen los mismos mensajes y notificaciones que antes, salvo las rutas.
