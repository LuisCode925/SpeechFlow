# Daemon y servicio `systemd` de usuario

La frase tiene tres ideas: daemon, servicio systemd de usuario y arquitectura cliente-servidor.

## 1. Daemon

Un **daemon** es un programa que corre en segundo plano, sin ventana ni terminal, y se queda esperando a que le pidan algo. En Linux es lo habitual para tareas que deben estar siempre disponibles, como el sonido (`pipewire`) o la red.

En el proyecto, el daemon sería el proceso que:
- carga el modelo de reconocimiento de voz una sola vez (es lo costoso);
- escucha el micrófono;
- transcribe y aplica el diccionario de reemplazos;
- escribe el texto resultante donde corresponda.

Si cada vez que dictas tuvieras que arrancar un programa y cargar el modelo, tardaría segundos. Con un daemon el modelo ya está en memoria.

## 2. `systemd` y servicio "de usuario"

**`systemd`** es el gestor de servicios de casi todas las distribuciones modernas (Debian 13 lo usa). Es el primer proceso del sistema (PID 1) y se encarga de arrancar, parar, reiniciar y vigilar procesos.

Hay dos modos:

| | Servicio de sistema | Servicio de usuario |
|---|---|---|
| Se ejecuta como | `root` | tu usuario (`code925`) |
| Arranca | al encender la máquina | al iniciar tu sesión |
| Definido en | `/etc/systemd/system/` | `~/.config/systemd/user/` |
| Comando | `systemctl` | `systemctl --user` |
| Necesita sudo | sí | no |

Para una app de dictado conviene el **de usuario**: necesita acceder a tu micrófono, tu sesión gráfica y tus archivos de configuración. Un servicio de sistema no tiene acceso natural a eso. Además no requiere permisos de administrador.

Se define con un archivo de texto, por ejemplo `~/.config/systemd/user/speechflow.service`:

```ini
[Unit]
Description=SpeechFlow daemon

[Service]
ExecStart=/home/code925/miniconda3/envs/speechflow/bin/python -m speechflow.daemon
Restart=on-failure

[Install]
WantedBy=default.target
```

Y se maneja así:

```bash
systemctl --user enable --now speechflow   # activar y arrancar al iniciar sesión
systemctl --user status speechflow         # ver estado
systemctl --user restart speechflow        # reiniciar
journalctl --user -u speechflow -f         # ver logs
```

Lo que te da systemd sin que lo programes tú:
- arranque automático al iniciar sesión;
- reinicio automático si el proceso se cae (`Restart=on-failure`);
- logs centralizados con `journalctl`;
- una forma estándar de arrancar y parar el servicio.

## 3. "La GUI o bandeja será cliente del proceso"

Esto es una separación **cliente-servidor** entre dos procesos distintos:

```
┌──────────────────┐    comandos (iniciar/parar,     ┌─────────────────────┐
│ GUI / icono de   │ ─────  recargar config...) ───▶ │  Daemon (servidor)  │
│ bandeja (cliente)│ ◀──── estado, eventos ───────── │  modelo + micrófono │
└──────────────────┘     socket Unix / D-Bus         └─────────────────────┘
```

- El **daemon** hace todo el trabajo real y no tiene interfaz.
- La **GUI o el icono de bandeja** (system tray) es solo una pantalla de control. Se conecta al daemon para pedirle cosas ("empieza a dictar", "recarga el diccionario") y mostrar su estado ("grabando", "error").

Se comunican con IPC (comunicación entre procesos). Las opciones típicas son un **socket Unix** (un archivo especial en `$XDG_RUNTIME_DIR`) o **D-Bus**, el bus de mensajes estándar de escritorio en Linux.

### Qué ventajas tiene

- **La GUI es opcional.** Si se cierra o se cuelga, el dictado sigue funcionando.
- **Varios clientes posibles.** Puedes tener bandeja, una ventana de ajustes y una CLI (`speechflow toggle`) hablando con el mismo daemon.
- **Puedes asignar un atajo de teclado** del escritorio a un comando CLI que le habla al daemon.
- **El modelo se carga una sola vez**, aunque abras y cierres la GUI.
- **Se prueba mejor:** puedes probar el núcleo sin interfaz gráfica.

## Resumen

La spec pide que el núcleo de SpeechFlow sea un proceso en segundo plano, gestionado por `systemd --user`, que arranque con tu sesión y se reinicie si falla. La interfaz de bandeja o la ventana no es el programa en sí, sino un mando a distancia que se conecta a él mediante un socket o D-Bus.
