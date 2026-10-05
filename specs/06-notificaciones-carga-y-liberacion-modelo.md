# SPEC 06 — Notificaciones de carga y liberación del modelo

> **Estado:** Implementado
> **Depende de:** SPEC 04, SPEC 05
> **Fecha:** 2026-10-04
> **Objetivo:** Reducir las notificaciones de escritorio de `push_to_talk.py` a las del ciclo de vida del modelo (cargando, cargado, liberado) y a los errores, dejando el resto de avisos solo en consola.

## Por qué existe esta spec

La SPEC 05 notifica cada paso del dictado (grabando, transcribiendo, texto insertado). Al dictar en otra ventana esas notificaciones tapan la pantalla y repiten lo que el usuario ya ve escrito. Lo que sí interesa saber desde fuera de la terminal es cuándo el modelo está listo para dictar y cuándo se ha liberado la GPU.

## Alcance

**Dentro:**

- En `scripts/push_to_talk.py`, notificar al empezar la carga (`Cargando medium...`) y al terminar (`Modelo medium cargado`), usando el nombre real de `--model`.
- Notificar `Modelo liberado` al salir con `Ctrl+C`, después de liberar el modelo.
- Añadir `Transcriber.close()` en `src/speechflow/transcriber.py`: suelta la referencia al modelo y fuerza la recolección de basura para liberar la GPU.
- Llamar a `close()` al salir de `push_to_talk.py`, antes de notificar la liberación.
- Mantener las notificaciones de error: fallo al abrir el micrófono y fallo al transcribir o insertar.
- Quitar las notificaciones de `Grabando...`, `Transcribiendo...`, `Límite de 60 s alcanzado`, `Sin texto reconocido` y `Texto insertado: ...`.
- Mantener intactos todos los mensajes de consola.
- Actualizar `README.md` (sección de avisos y descripción de `notifier.py` si cambia algo) y el docstring del script si menciona las notificaciones.

**Fuera de alcance (para futuras specs):**

- Descarga del modelo por inactividad y recarga bajo demanda.
- Notificaciones configurables (opción `--notify`, archivo de configuración, niveles de verbosidad).
- Esperar a que termine una transcripción en curso antes de liberar el modelo al salir.
- Liberar el modelo en otras señales (`SIGTERM`, cierre de terminal).
- Cambios en `notifier.py`, `inserter.py` o `audio.py`.
- Reducir o cambiar los mensajes de consola.

## Modelo de datos

No hay estructuras de datos nuevas. Cambia una interfaz pública:

```python
# src/speechflow/transcriber.py
class Transcriber:
    def close(self) -> None: ...   # self._model = None; gc.collect(); idempotente
```

Convenciones:

- Tras `close()`, llamar a `transcribe()` es un error del llamador; no se protege.
- Textos exactos de las notificaciones, con el título `SpeechFlow`:
  - `Cargando {model}...`
  - `Modelo {model} cargado`
  - `Modelo liberado`
  - Errores: los textos actuales `Error al abrir el micrófono: ...` y `Error: ...`.

## Plan de implementación

1. Añadir `Transcriber.close()` en `src/speechflow/transcriber.py`. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); from speechflow.transcriber import Transcriber; t = Transcriber(); t.close(); t.close()"` no falla y `nvidia-smi` no muestra el proceso tras terminar `close()` (con el intérprete aún vivo).
2. En `scripts/push_to_talk.py`, añadir las notificaciones `Cargando {model}...` antes de crear el `Transcriber` y `Modelo {model} cargado` tras crearlo. Verificar: arrancar el script muestra las dos notificaciones y los mismos mensajes de consola que antes.
3. Llamar a `transcriber.close()` y notificar `Modelo liberado` al salir (bloque `except KeyboardInterrupt` o `finally`), tras el `print("\nSaliendo.")`. Verificar: `Ctrl+C` muestra la notificación y la consola imprime `Saliendo.`.
4. Quitar de `PushToTalk` las llamadas a `notify` de grabando, transcribiendo, límite, sin texto y texto insertado. Dejar las de error. Verificar: un dictado completo no genera notificaciones y la consola muestra los mismos mensajes que antes.
5. Actualizar `README.md` con las notificaciones que existen ahora. Verificar: el README coincide con el comportamiento del script.

## Criterios de aceptación

- [ ] Al arrancar, aparecen dos notificaciones en este orden: `Cargando medium...` y `Modelo medium cargado`.
- [ ] Con `--model small`, los textos de las notificaciones dicen `small`.
- [ ] Un dictado completo (grabar, transcribir, insertar) no genera ninguna notificación.
- [ ] Un toque de menos de 0.5 s no genera ninguna notificación.
- [ ] Mantener la tecla más de 60 s no genera notificación de límite; la consola sigue avisando.
- [ ] Con `Ctrl+C` aparece la notificación `Modelo liberado` y el proceso termina.
- [ ] `Transcriber.close()` existe, puede llamarse dos veces y deja la memoria de GPU liberada antes de que termine el proceso.
- [ ] Un fallo al abrir el micrófono sigue generando una notificación de error.
- [ ] Un fallo al transcribir o insertar sigue generando una notificación de error.
- [ ] La salida de consola de un ciclo completo es idéntica a la de la SPEC 05.
- [ ] Si falta `notify-send`, el script sigue funcionando solo con consola, como antes.
- [ ] `README.md` lista las tres notificaciones del modelo y la de errores, y no menciona las eliminadas.

## Decisiones

- **Sí:** notificar solo carga, liberación y errores, por elección del usuario. Son los eventos que el usuario no ve al dictar en otra ventana.
- **Sí:** mantener las notificaciones de error. Un fallo silencioso fuera de la terminal deja al usuario sin saber por qué no se escribe nada.
- **No:** quitar también los errores. Se descartó por el motivo anterior.
- **Sí:** notificar al empezar y al terminar la carga, por elección del usuario. La carga con calentamiento tarda segundos y avisa de cuándo se puede dictar.
- **Sí:** "liberar el modelo" significa salir con `Ctrl+C`, por elección del usuario. Hoy no hay otro momento en que se libere.
- **No:** descarga por inactividad. Añade temporizadores y recargas lentas; es otra spec si hace falta.
- **Sí:** `Transcriber.close()` explícito en lugar de depender del fin del proceso. Hace que la notificación `Modelo liberado` sea verdad en el momento en que se muestra.
- **Sí:** mensajes de consola intactos, por elección del usuario. Solo cambia el canal de escritorio.
- **No:** opción `--notify` o configuración. Es un cambio fijo y simple; la configurabilidad queda para otra spec.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `Ctrl+C` durante una transcripción en curso deja una referencia viva al modelo y la GPU no se libera al llamar a `close()` | Los hilos de transcripción son `daemon` y el proceso termina enseguida; se acepta que la memoria se libere al salir. Esperar al hilo queda fuera de alcance. |
| `gc.collect()` no libera la memoria de CTranslate2 de inmediato | El criterio de aceptación comprueba `nvidia-smi`; si falla, se documenta y se evalúa otra estrategia en una spec nueva. |
| La notificación `Modelo liberado` se envía con `notify-send` justo antes de terminar el proceso y no se muestra | `notify` usa `subprocess.run`, que espera a que `notify-send` termine antes de continuar. |

## Lo que **no** está en esta spec

- Descarga del modelo por inactividad y recarga bajo demanda.
- Opciones o archivo de configuración para las notificaciones.
- Esperar a una transcripción en curso al salir.
- Liberación en señales distintas de `Ctrl+C`.
- Cambios en los mensajes de consola.

Cada uno, si se aborda, va en su propia spec.
