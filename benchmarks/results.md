# Resultados del benchmark de STT

- Fecha: 2026-10-04
- GPU: NVIDIA GeForce GTX 1060 6GB, 550.163.01
- Idioma fijado: `es` (sin muestras en inglés todavía)
- Objetivo: < 2 s por cada 10 s de audio, VRAM < 6144 MB
- `load_seconds` puede incluir la descarga del modelo en la primera ejecución.

| Modelo | Compute | Muestra | Audio (s) | Carga (s) | Transcripción (s) | VRAM pico (MB) |
| ------ | ------- | ------- | --------- | --------- | ----------------- | -------------- |
| small | int8 | mercado-libre_000.wav | 10.0 | 1.34 | 0.47 | 503 |
| small | int8 | mercado-libre_001.wav | 10.0 | 1.34 | 0.52 | 503 |
| small | int8 | mercado-libre_002.wav | 10.0 | 1.34 | 0.52 | 503 |
| small | int8 | mercado-libre_003.wav | 10.0 | 1.34 | 0.53 | 503 |
| small | int8 | mercado-libre_004.wav | 10.0 | 1.34 | 0.50 | 503 |
| medium | int8 | mercado-libre_000.wav | 10.0 | 1066.22 | 1.15 | 1146 |
| medium | int8 | mercado-libre_001.wav | 10.0 | 1066.22 | 1.19 | 1146 |
| medium | int8 | mercado-libre_002.wav | 10.0 | 1066.22 | 1.16 | 1146 |
| medium | int8 | mercado-libre_003.wav | 10.0 | 1066.22 | 1.21 | 1146 |
| medium | int8 | mercado-libre_004.wav | 10.0 | 1066.22 | 1.10 | 1146 |

## Mediana por modelo (transcripción normalizada a 10 s de audio)

- `small`: 0.52 s, VRAM pico 503 MB
- `medium`: 1.16 s, VRAM pico 1146 MB

## Modelo por defecto para la siguiente spec

**`medium` int8**: el modelo más grande que cumple latencia y VRAM.

## Transcripciones

- `small` / `mercado-libre_000.wav`: Mercado pago acaba de empeorar y para colmo nos lo hará ver como algo bueno. Dos cambios relevantes, ahora las condiciones para mantener el 12%
- `small` / `mercado-libre_001.wav`: de rendimiento van a cambiar dependiendo de la persona. A mí, por ejemplo, me sigue pidiendo lo de depositar 3 mil pesos, pero varias personas me han compartido que a ellas les pide
- `small` / `mercado-libre_002.wav`: gastar. Distintos montos, mil, dos mil pesos, son los que me llegaron a contar. Si a ti te pide más o alguna condición diferente, por favor cuéntanos en los comentarios.
- `small` / `mercado-libre_003.wav`: No cambio, regrese el 15% en su sección de apartados, pero para esto pide si o si suscribirse a MeliPlus, para lo cual hay paquetes desde 49 hasta casi 400.
- `small` / `mercado-libre_004.wav`: los pesos. Y te adelanto, creo que esto solo vale la pena si ya usaras los otros beneficios de esta suscripción, de lo contrario paso sin ver. Veamos entonces a
- `medium` / `mercado-libre_000.wav`: Mercado pago acaba de empeorar y para colmo nos lo hará ver como algo bueno, dos cambios relevantes, ahora las condiciones para mantener el 12 por ciento
- `medium` / `mercado-libre_001.wav`: de rendimiento van a cambiar dependiendo de la persona, a mí por ejemplo, me sigue pidiendo lo de depositar 3000 pesos, pero varias personas me han compartido que a ellas les pide.
- `medium` / `mercado-libre_002.wav`: gastar, distintos montos 1000, 2000 pesos son los que me llegaron a contar, si a ti te pide más o alguna condición diferente por favor cuéntanos en los comentarios.
- `medium` / `mercado-libre_003.wav`: cambio regrese el 15% en su sección de apartados, pero para esto pide sí o sí suscribirse a Meli Plus, para lo cual hay paquetes desde 49 hasta casi 400.
- `medium` / `mercado-libre_004.wav`: pesos. Y te adelanto, creo que esto solo vale la pena si ya usarás los otros beneficios de esta suscripción, de lo contrario paso sin ver. Veamos entonces a
