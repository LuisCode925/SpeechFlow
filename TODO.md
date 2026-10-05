# TODO — Ideas pendientes

Ideas recogidas de la sección "Lo que **no** está en esta spec" de las SPEC 01–08, sin duplicados y sin las que ya se han implementado. Entre paréntesis, la spec de origen. Cada idea, si se aborda, va en su propia spec.

## Audio y captura

- [ ] VAD (detección de actividad de voz) y recorte de silencios (SPEC 01, 03, 04, 05).
- [ ] Streaming de la captura y de la transcripción (SPEC 03, 04, 05).
- [ ] Reducción de ruido (SPEC 03).
- [ ] Persistencia del dispositivo de audio elegido entre ejecuciones (SPEC 08).
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
- [ ] Descarga del modelo por inactividad y recarga bajo demanda (SPEC 06).
- [ ] Esperar a una transcripción en curso al salir (SPEC 06).
- [ ] Liberar el modelo en señales distintas de `Ctrl+C` (SPEC 06).

## Configuración

- [ ] Archivo de configuración de usuario (SPEC 01, 05).
- [ ] Opciones o archivo de configuración para las notificaciones (SPEC 06).

## Log y diagnóstico

- [ ] Archivo de log, rotación y carpeta `logs/` (SPEC 07).
- [ ] Opciones `--quiet` / `--verbose` y niveles configurables (SPEC 07).
- [ ] Log en `capture_mic.py`, `benchmark_stt.py` y `audio.py` (SPEC 07).
- [ ] Formato JSON, colores y zona horaria en el log (SPEC 07).
- [ ] Mostrar VRAM, versión de CUDA, tecla y sesión X11 en el banner de arranque (SPEC 07).
- [ ] Cambios en las notificaciones de escritorio (SPEC 07).

## Calidad y empaquetado

- [ ] Empaquetado (`pyproject.toml`) y `python -m speechflow` (SPEC 04, 05).
- [ ] Tests con `pytest` (SPEC 04, 05).
