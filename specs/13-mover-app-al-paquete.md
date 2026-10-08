# SPEC 13 — Mover la app de push-to-talk al paquete

> **Estado:** Aceptado
> **Depende de:** SPEC 04, SPEC 05, SPEC 06, SPEC 07, SPEC 08, SPEC 10, SPEC 11, SPEC 12
> **Fecha:** 2026-10-07
> **Objetivo:** Mover la lógica de `scripts/push_to_talk.py` a `src/speechflow/app.py` para que sea importable y testeable, sin cambiar el comportamiento, el CLI ni la salida.

## Por qué existe esta spec

Toda la lógica de la aplicación (`State`, `PushToTalk`, `parse_key`, `describe_device`, `load_transcriber`, `resolve_config` y `main()`) vive en `scripts/push_to_talk.py` (480 líneas) y depende de un `sys.path.insert` para encontrar el paquete. No se puede importar desde tests ni desde un punto de entrada instalable. Es el primer paso de la Fase 2 (SPEC 13–16): empaquetado (14), tests (15) y cierre limpio (16) dependen de esto.

## Alcance

**Dentro:**

- Crear `src/speechflow/app.py` con `State`, `PushToTalk`, `parse_key`, `describe_device`, `load_transcriber`, `resolve_config` y `main()`, movidos tal cual.
- Dejar `scripts/push_to_talk.py` como envoltorio: inserta `src` en `sys.path` (aún no hay `pyproject.toml`), importa `speechflow.app.main` y la llama.
- El docstring del módulo (que alimenta `--help`) pasa a `app.py`; el script conserva uno breve.
- Mismo CLI, mismas opciones, mismos mensajes de log y notificaciones, mismos códigos de salida.
- Actualizar `README.md` (rutas de módulos) y `TODO.md`.

**Fuera de alcance (para futuras specs):**

- `pyproject.toml`, `python -m speechflow` y el comando `speechflow` (SPEC 14).
- Cambiar las rutas de configuración, estado y plantilla de emergencia (`REPO_ROOT`) (SPEC 14).
- Tests (SPEC 15).
- Manejo de `SIGTERM`/`SIGHUP` y espera a la transcripción en curso (SPEC 16).
- Refactorizar `PushToTalk` o dividir `app.py` en más módulos.
- Cambios en `audio.py`, `config.py`, `inserter.py`, `log.py`, `notifier.py`, `transcriber.py`, `capture_mic.py` y `benchmark_stt.py`.

## Modelo de datos

```python
# src/speechflow/app.py
class State(Enum): ...
class PushToTalk: ...                       # sin cambios de interfaz
def parse_key(name: str) -> keyboard.Key | keyboard.KeyCode: ...
def describe_device(device: int | str | None) -> str: ...
def load_transcriber(model: str, language: str) -> Transcriber: ...
def resolve_config(explicit: Path | None) -> Config: ...
def main() -> None: ...
```

```python
# scripts/push_to_talk.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from speechflow.app import main

if __name__ == "__main__":
    main()
```

Convenciones:

- El movimiento es literal: no se renombra ni se reordena nada que no sea necesario para que `app.py` importe.
- `app.py` no inserta nada en `sys.path`; eso queda solo en el envoltorio hasta la SPEC 14.
- `--help` debe mostrar el mismo texto que ahora.

## Plan de implementación

1. Crear `src/speechflow/app.py` copiando el contenido de `scripts/push_to_talk.py` (imports, `State`, `PushToTalk`, funciones y `main()`) sin el `sys.path.insert` ni el bloque `if __name__`. Verificar: `python -c "import sys; sys.path.insert(0, 'src'); import speechflow.app"` no falla (sin cargar el modelo ni abrir el micrófono).
2. Reducir `scripts/push_to_talk.py` al envoltorio. Verificar: `python scripts/push_to_talk.py --list-devices` y `--help` dan la misma salida que antes de la spec (guardar la salida previa para comparar).
3. Comprobar que nada más importa de `scripts/push_to_talk.py` (`grep -rn "push_to_talk" scripts src`). Verificar: sin referencias rotas.
4. Prueba manual completa con el modelo real: arranque con el mismo banner y líneas de log, un dictado, `f8`, desconexión y reconexión del micrófono, `[model] idle_timeout = 30` con descarga y recarga, y `Ctrl+C`. Verificar: el log coincide con el ejemplo del README.
5. Actualizar `README.md` (mencionar que la lógica vive en `src/speechflow/app.py` y que `scripts/push_to_talk.py` es el punto de entrada) y marcar la fase en `TODO.md`. Verificar: el README no menciona rutas obsoletas.

## Criterios de aceptación

- [ ] `src/speechflow/app.py` contiene `State`, `PushToTalk`, `parse_key`, `describe_device`, `load_transcriber`, `resolve_config` y `main()`.
- [ ] `scripts/push_to_talk.py` no contiene lógica, solo el envoltorio.
- [ ] `import speechflow.app` no tiene efectos secundarios (no carga el modelo, no abre el micrófono, no configura el log).
- [ ] `--help` y `--list-devices` producen la misma salida que antes.
- [ ] El arranque, el dictado, el cambio de entrada, la vigilancia del micrófono, la descarga por inactividad y la salida con `Ctrl+C` producen los mismos mensajes y notificaciones que antes.
- [ ] Los errores de arranque siguen terminando con código 1 y el mismo mensaje.
- [ ] `capture_mic.py` y `benchmark_stt.py` no cambian.
- [ ] `README.md` refleja la nueva ubicación del código.

## Decisiones

- **Sí:** movimiento literal sin refactor. Reduce el riesgo y deja el diff revisable como un simple traslado.
- **Sí:** `scripts/push_to_talk.py` se conserva como envoltorio. Los comandos documentados en el README siguen funcionando hasta la SPEC 14.
- **No:** crear ya `__main__.py` ni `pyproject.toml`. Es el alcance de la SPEC 14.
- **No:** tocar `REPO_ROOT` ni las rutas de configuración. Cambiarlas aquí mezclaría movimiento de código con cambios de comportamiento.
- **No:** dividir `PushToTalk` en varios módulos. Se puede valorar tras los tests de la SPEC 15.
- **Sí:** el nombre `app.py` en vez de `push_to_talk.py` dentro del paquete, para evitar dos módulos con el mismo nombre y dejar espacio a otros modos de ejecución (daemon, bandeja) en la Fase 3.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Un efecto secundario a nivel de módulo (`logger`, imports pesados) cambia al importar desde el paquete | Paso 1 comprueba que importar `speechflow.app` no tiene efectos; el `logger` solo se obtiene, no se configura. |
| `--help` cambia porque el docstring se mueve | Guardar la salida previa y compararla en el paso 2. |
| Importar `pynput` sin sesión gráfica falla al importar `app.py` | Ya ocurría con el script; la SPEC 15 lo resolverá con dobles. Se anota, no se corrige aquí. |
| Rutas relativas a `__file__` en el código movido apuntan a otro sitio | Revisar los usos de `Path(__file__)` en el código movido; las rutas del repo ya salen de `config.REPO_ROOT`. |

## Lo que **no** está en esta spec

- Empaquetado, `python -m speechflow` y comando `speechflow`.
- Rutas de configuración y estado independientes del repo.
- Tests con `pytest`.
- Cierre ante `SIGTERM`/`SIGHUP` y espera a la transcripción en curso.
- Dividir `PushToTalk` en módulos más pequeños.

Cada uno, si se aborda, va en su propia spec.
