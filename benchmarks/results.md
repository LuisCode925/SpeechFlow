# Resultados del benchmark de STT

- Fecha: 2026-10-04
- GPU: NVIDIA GeForce GTX 1060 6GB, 550.163.01
- Idioma de cada muestra: por el prefijo de su nombre (`mercado-libre` → `es`, `bug-lower` → `en`)
- Objetivo: < 2 s por cada 10 s de audio en cada idioma, VRAM < 6144 MB
- `load_seconds` puede incluir la descarga del modelo en la primera ejecución.

## Mediana por modelo e idioma (transcripción normalizada a 10 s de audio)

- `small` / `en`: 0.54 s (74 muestras), VRAM pico 535 MB
- `small` / `es`: 0.51 s (44 muestras), VRAM pico 535 MB
- `medium` / `en`: 1.26 s (74 muestras), VRAM pico 2337 MB
- `medium` / `es`: 1.18 s (44 muestras), VRAM pico 2337 MB

## Modelo por defecto para la siguiente spec

**`medium` int8**: el modelo más grande que cumple latencia y VRAM en ambos idiomas.

## Muestras

| Modelo | Compute | Idioma | Muestra | Audio (s) | Carga (s) | Transcripción (s) | VRAM pico (MB) |
| ------ | ------- | ------ | ------- | --------- | --------- | ----------------- | -------------- |
| small | int8 | en | bug-lower_000.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | en | bug-lower_001.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_002.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | en | bug-lower_003.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | en | bug-lower_004.wav | 10.0 | 1.05 | 0.71 | 535 |
| small | int8 | en | bug-lower_005.wav | 10.0 | 1.05 | 0.58 | 535 |
| small | int8 | en | bug-lower_006.wav | 10.0 | 1.05 | 0.52 | 535 |
| small | int8 | en | bug-lower_007.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | en | bug-lower_008.wav | 10.0 | 1.05 | 0.67 | 535 |
| small | int8 | en | bug-lower_009.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_010.wav | 10.0 | 1.05 | 0.69 | 535 |
| small | int8 | en | bug-lower_011.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_012.wav | 10.0 | 1.05 | 0.53 | 535 |
| small | int8 | en | bug-lower_013.wav | 10.0 | 1.05 | 0.52 | 535 |
| small | int8 | en | bug-lower_014.wav | 10.0 | 1.05 | 0.39 | 535 |
| small | int8 | en | bug-lower_015.wav | 10.0 | 1.05 | 0.45 | 535 |
| small | int8 | en | bug-lower_016.wav | 10.0 | 1.05 | 0.43 | 535 |
| small | int8 | en | bug-lower_017.wav | 10.0 | 1.05 | 0.60 | 535 |
| small | int8 | en | bug-lower_018.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_019.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_020.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | en | bug-lower_021.wav | 10.0 | 1.05 | 0.41 | 535 |
| small | int8 | en | bug-lower_022.wav | 10.0 | 1.05 | 0.69 | 535 |
| small | int8 | en | bug-lower_023.wav | 10.0 | 1.05 | 0.57 | 535 |
| small | int8 | en | bug-lower_024.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_025.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | en | bug-lower_026.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | en | bug-lower_027.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | en | bug-lower_028.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | en | bug-lower_029.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | en | bug-lower_030.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | en | bug-lower_031.wav | 10.0 | 1.05 | 0.44 | 535 |
| small | int8 | en | bug-lower_032.wav | 10.0 | 1.05 | 0.77 | 535 |
| small | int8 | en | bug-lower_033.wav | 10.0 | 1.05 | 0.60 | 535 |
| small | int8 | en | bug-lower_034.wav | 10.0 | 1.05 | 0.56 | 535 |
| small | int8 | en | bug-lower_035.wav | 10.0 | 1.05 | 0.62 | 535 |
| small | int8 | en | bug-lower_036.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | en | bug-lower_037.wav | 10.0 | 1.05 | 0.61 | 535 |
| small | int8 | en | bug-lower_038.wav | 10.0 | 1.05 | 0.61 | 535 |
| small | int8 | en | bug-lower_039.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | en | bug-lower_040.wav | 10.0 | 1.05 | 0.58 | 535 |
| small | int8 | en | bug-lower_041.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | en | bug-lower_042.wav | 10.0 | 1.05 | 0.70 | 535 |
| small | int8 | en | bug-lower_043.wav | 10.0 | 1.05 | 0.75 | 535 |
| small | int8 | en | bug-lower_044.wav | 10.0 | 1.05 | 0.61 | 535 |
| small | int8 | en | bug-lower_045.wav | 10.0 | 1.05 | 0.65 | 535 |
| small | int8 | en | bug-lower_046.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | en | bug-lower_047.wav | 10.0 | 1.05 | 0.61 | 535 |
| small | int8 | en | bug-lower_048.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_049.wav | 10.0 | 1.05 | 0.44 | 535 |
| small | int8 | en | bug-lower_050.wav | 10.0 | 1.05 | 0.56 | 535 |
| small | int8 | en | bug-lower_051.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | en | bug-lower_052.wav | 10.0 | 1.05 | 0.56 | 535 |
| small | int8 | en | bug-lower_053.wav | 10.0 | 1.05 | 0.44 | 535 |
| small | int8 | en | bug-lower_054.wav | 10.0 | 1.05 | 0.58 | 535 |
| small | int8 | en | bug-lower_055.wav | 10.0 | 1.05 | 0.61 | 535 |
| small | int8 | en | bug-lower_056.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | en | bug-lower_057.wav | 10.0 | 1.05 | 0.71 | 535 |
| small | int8 | en | bug-lower_058.wav | 10.0 | 1.05 | 0.63 | 535 |
| small | int8 | en | bug-lower_059.wav | 10.0 | 1.05 | 0.59 | 535 |
| small | int8 | en | bug-lower_060.wav | 10.0 | 1.05 | 0.47 | 535 |
| small | int8 | en | bug-lower_061.wav | 10.0 | 1.05 | 0.45 | 535 |
| small | int8 | en | bug-lower_062.wav | 10.0 | 1.05 | 0.45 | 535 |
| small | int8 | en | bug-lower_063.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | en | bug-lower_064.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | en | bug-lower_065.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | en | bug-lower_066.wav | 10.0 | 1.05 | 0.59 | 535 |
| small | int8 | en | bug-lower_067.wav | 10.0 | 1.05 | 0.43 | 535 |
| small | int8 | en | bug-lower_068.wav | 10.0 | 1.05 | 0.65 | 535 |
| small | int8 | en | bug-lower_069.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_070.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | en | bug-lower_071.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | en | bug-lower_072.wav | 10.0 | 1.05 | 0.60 | 535 |
| small | int8 | en | bug-lower_073.wav | 3.9 | 1.05 | 0.42 | 535 |
| small | int8 | es | mercado-libre_000.wav | 10.0 | 1.05 | 0.45 | 535 |
| small | int8 | es | mercado-libre_001.wav | 10.0 | 1.05 | 0.50 | 535 |
| small | int8 | es | mercado-libre_002.wav | 10.0 | 1.05 | 0.52 | 535 |
| small | int8 | es | mercado-libre_003.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | es | mercado-libre_004.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | es | mercado-libre_005.wav | 10.0 | 1.05 | 0.47 | 535 |
| small | int8 | es | mercado-libre_006.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | es | mercado-libre_007.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | es | mercado-libre_008.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | es | mercado-libre_009.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | es | mercado-libre_010.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | es | mercado-libre_011.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | es | mercado-libre_012.wav | 10.0 | 1.05 | 0.50 | 535 |
| small | int8 | es | mercado-libre_013.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | es | mercado-libre_014.wav | 10.0 | 1.05 | 0.49 | 535 |
| small | int8 | es | mercado-libre_015.wav | 10.0 | 1.05 | 0.47 | 535 |
| small | int8 | es | mercado-libre_016.wav | 10.0 | 1.05 | 0.47 | 535 |
| small | int8 | es | mercado-libre_017.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | es | mercado-libre_018.wav | 10.0 | 1.05 | 0.52 | 535 |
| small | int8 | es | mercado-libre_019.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | es | mercado-libre_020.wav | 10.0 | 1.05 | 0.52 | 535 |
| small | int8 | es | mercado-libre_021.wav | 10.0 | 1.05 | 0.50 | 535 |
| small | int8 | es | mercado-libre_022.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | es | mercado-libre_023.wav | 10.0 | 1.05 | 0.47 | 535 |
| small | int8 | es | mercado-libre_024.wav | 10.0 | 1.05 | 0.60 | 535 |
| small | int8 | es | mercado-libre_025.wav | 10.0 | 1.05 | 0.50 | 535 |
| small | int8 | es | mercado-libre_026.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | es | mercado-libre_027.wav | 10.0 | 1.05 | 0.48 | 535 |
| small | int8 | es | mercado-libre_028.wav | 10.0 | 1.05 | 0.52 | 535 |
| small | int8 | es | mercado-libre_029.wav | 10.0 | 1.05 | 0.47 | 535 |
| small | int8 | es | mercado-libre_030.wav | 10.0 | 1.05 | 0.59 | 535 |
| small | int8 | es | mercado-libre_031.wav | 10.0 | 1.05 | 0.46 | 535 |
| small | int8 | es | mercado-libre_032.wav | 10.0 | 1.05 | 0.50 | 535 |
| small | int8 | es | mercado-libre_033.wav | 10.0 | 1.05 | 0.56 | 535 |
| small | int8 | es | mercado-libre_034.wav | 10.0 | 1.05 | 0.54 | 535 |
| small | int8 | es | mercado-libre_035.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | es | mercado-libre_036.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | es | mercado-libre_037.wav | 10.0 | 1.05 | 0.51 | 535 |
| small | int8 | es | mercado-libre_038.wav | 10.0 | 1.05 | 0.53 | 535 |
| small | int8 | es | mercado-libre_039.wav | 10.0 | 1.05 | 0.55 | 535 |
| small | int8 | es | mercado-libre_040.wav | 10.0 | 1.05 | 0.50 | 535 |
| small | int8 | es | mercado-libre_041.wav | 10.0 | 1.05 | 0.56 | 535 |
| small | int8 | es | mercado-libre_042.wav | 10.0 | 1.05 | 0.53 | 535 |
| small | int8 | es | mercado-libre_043.wav | 2.3 | 1.05 | 0.28 | 535 |
| medium | int8 | en | bug-lower_000.wav | 10.0 | 3.22 | 1.09 | 2337 |
| medium | int8 | en | bug-lower_001.wav | 10.0 | 3.22 | 1.35 | 2337 |
| medium | int8 | en | bug-lower_002.wav | 10.0 | 3.22 | 1.21 | 2337 |
| medium | int8 | en | bug-lower_003.wav | 10.0 | 3.22 | 1.11 | 2337 |
| medium | int8 | en | bug-lower_004.wav | 10.0 | 3.22 | 1.67 | 2337 |
| medium | int8 | en | bug-lower_005.wav | 10.0 | 3.22 | 1.62 | 2337 |
| medium | int8 | en | bug-lower_006.wav | 10.0 | 3.22 | 1.18 | 2337 |
| medium | int8 | en | bug-lower_007.wav | 10.0 | 3.22 | 1.02 | 2337 |
| medium | int8 | en | bug-lower_008.wav | 10.0 | 3.22 | 1.40 | 2337 |
| medium | int8 | en | bug-lower_009.wav | 10.0 | 3.22 | 1.26 | 2337 |
| medium | int8 | en | bug-lower_010.wav | 10.0 | 3.22 | 2.71 | 2337 |
| medium | int8 | en | bug-lower_011.wav | 10.0 | 3.22 | 1.34 | 2337 |
| medium | int8 | en | bug-lower_012.wav | 10.0 | 3.22 | 1.21 | 2337 |
| medium | int8 | en | bug-lower_013.wav | 10.0 | 3.22 | 1.82 | 2337 |
| medium | int8 | en | bug-lower_014.wav | 10.0 | 3.22 | 0.94 | 2337 |
| medium | int8 | en | bug-lower_015.wav | 10.0 | 3.22 | 1.01 | 2337 |
| medium | int8 | en | bug-lower_016.wav | 10.0 | 3.22 | 1.00 | 2337 |
| medium | int8 | en | bug-lower_017.wav | 10.0 | 3.22 | 1.31 | 2337 |
| medium | int8 | en | bug-lower_018.wav | 10.0 | 3.22 | 1.40 | 2337 |
| medium | int8 | en | bug-lower_019.wav | 10.0 | 3.22 | 1.22 | 2337 |
| medium | int8 | en | bug-lower_020.wav | 10.0 | 3.22 | 1.08 | 2337 |
| medium | int8 | en | bug-lower_021.wav | 10.0 | 3.22 | 1.00 | 2337 |
| medium | int8 | en | bug-lower_022.wav | 10.0 | 3.22 | 1.61 | 2337 |
| medium | int8 | en | bug-lower_023.wav | 10.0 | 3.22 | 1.25 | 2337 |
| medium | int8 | en | bug-lower_024.wav | 10.0 | 3.22 | 1.20 | 2337 |
| medium | int8 | en | bug-lower_025.wav | 10.0 | 3.22 | 1.17 | 2337 |
| medium | int8 | en | bug-lower_026.wav | 10.0 | 3.22 | 1.93 | 2337 |
| medium | int8 | en | bug-lower_027.wav | 10.0 | 3.22 | 1.05 | 2337 |
| medium | int8 | en | bug-lower_028.wav | 10.0 | 3.22 | 1.10 | 2337 |
| medium | int8 | en | bug-lower_029.wav | 10.0 | 3.22 | 1.23 | 2337 |
| medium | int8 | en | bug-lower_030.wav | 10.0 | 3.22 | 1.16 | 2337 |
| medium | int8 | en | bug-lower_031.wav | 10.0 | 3.22 | 1.06 | 2337 |
| medium | int8 | en | bug-lower_032.wav | 10.0 | 3.22 | 1.21 | 2337 |
| medium | int8 | en | bug-lower_033.wav | 10.0 | 3.22 | 1.36 | 2337 |
| medium | int8 | en | bug-lower_034.wav | 10.0 | 3.22 | 1.23 | 2337 |
| medium | int8 | en | bug-lower_035.wav | 10.0 | 3.22 | 1.42 | 2337 |
| medium | int8 | en | bug-lower_036.wav | 10.0 | 3.22 | 1.20 | 2337 |
| medium | int8 | en | bug-lower_037.wav | 10.0 | 3.22 | 1.37 | 2337 |
| medium | int8 | en | bug-lower_038.wav | 10.0 | 3.22 | 1.34 | 2337 |
| medium | int8 | en | bug-lower_039.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | en | bug-lower_040.wav | 10.0 | 3.22 | 1.41 | 2337 |
| medium | int8 | en | bug-lower_041.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | en | bug-lower_042.wav | 10.0 | 3.22 | 1.48 | 2337 |
| medium | int8 | en | bug-lower_043.wav | 10.0 | 3.22 | 1.50 | 2337 |
| medium | int8 | en | bug-lower_044.wav | 10.0 | 3.22 | 1.40 | 2337 |
| medium | int8 | en | bug-lower_045.wav | 10.0 | 3.22 | 1.37 | 2337 |
| medium | int8 | en | bug-lower_046.wav | 10.0 | 3.22 | 1.13 | 2337 |
| medium | int8 | en | bug-lower_047.wav | 10.0 | 3.22 | 1.43 | 2337 |
| medium | int8 | en | bug-lower_048.wav | 10.0 | 3.22 | 1.98 | 2337 |
| medium | int8 | en | bug-lower_049.wav | 10.0 | 3.22 | 1.13 | 2337 |
| medium | int8 | en | bug-lower_050.wav | 10.0 | 3.22 | 1.43 | 2337 |
| medium | int8 | en | bug-lower_051.wav | 10.0 | 3.22 | 1.30 | 2337 |
| medium | int8 | en | bug-lower_052.wav | 10.0 | 3.22 | 1.18 | 2337 |
| medium | int8 | en | bug-lower_053.wav | 10.0 | 3.22 | 1.07 | 2337 |
| medium | int8 | en | bug-lower_054.wav | 10.0 | 3.22 | 1.26 | 2337 |
| medium | int8 | en | bug-lower_055.wav | 10.0 | 3.22 | 1.31 | 2337 |
| medium | int8 | en | bug-lower_056.wav | 10.0 | 3.22 | 1.30 | 2337 |
| medium | int8 | en | bug-lower_057.wav | 10.0 | 3.22 | 1.50 | 2337 |
| medium | int8 | en | bug-lower_058.wav | 10.0 | 3.22 | 1.41 | 2337 |
| medium | int8 | en | bug-lower_059.wav | 10.0 | 3.22 | 1.32 | 2337 |
| medium | int8 | en | bug-lower_060.wav | 10.0 | 3.22 | 1.28 | 2337 |
| medium | int8 | en | bug-lower_061.wav | 10.0 | 3.22 | 1.02 | 2337 |
| medium | int8 | en | bug-lower_062.wav | 10.0 | 3.22 | 1.05 | 2337 |
| medium | int8 | en | bug-lower_063.wav | 10.0 | 3.22 | 1.17 | 2337 |
| medium | int8 | en | bug-lower_064.wav | 10.0 | 3.22 | 1.27 | 2337 |
| medium | int8 | en | bug-lower_065.wav | 10.0 | 3.22 | 1.25 | 2337 |
| medium | int8 | en | bug-lower_066.wav | 10.0 | 3.22 | 1.43 | 2337 |
| medium | int8 | en | bug-lower_067.wav | 10.0 | 3.22 | 1.03 | 2337 |
| medium | int8 | en | bug-lower_068.wav | 10.0 | 3.22 | 1.44 | 2337 |
| medium | int8 | en | bug-lower_069.wav | 10.0 | 3.22 | 1.39 | 2337 |
| medium | int8 | en | bug-lower_070.wav | 10.0 | 3.22 | 1.29 | 2337 |
| medium | int8 | en | bug-lower_071.wav | 10.0 | 3.22 | 1.10 | 2337 |
| medium | int8 | en | bug-lower_072.wav | 10.0 | 3.22 | 1.65 | 2337 |
| medium | int8 | en | bug-lower_073.wav | 3.9 | 3.22 | 0.95 | 2337 |
| medium | int8 | es | mercado-libre_000.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | es | mercado-libre_001.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | es | mercado-libre_002.wav | 10.0 | 3.22 | 1.14 | 2337 |
| medium | int8 | es | mercado-libre_003.wav | 10.0 | 3.22 | 1.22 | 2337 |
| medium | int8 | es | mercado-libre_004.wav | 10.0 | 3.22 | 1.13 | 2337 |
| medium | int8 | es | mercado-libre_005.wav | 10.0 | 3.22 | 1.11 | 2337 |
| medium | int8 | es | mercado-libre_006.wav | 10.0 | 3.22 | 1.18 | 2337 |
| medium | int8 | es | mercado-libre_007.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | es | mercado-libre_008.wav | 10.0 | 3.22 | 1.23 | 2337 |
| medium | int8 | es | mercado-libre_009.wav | 10.0 | 3.22 | 1.30 | 2337 |
| medium | int8 | es | mercado-libre_010.wav | 10.0 | 3.22 | 1.13 | 2337 |
| medium | int8 | es | mercado-libre_011.wav | 10.0 | 3.22 | 1.21 | 2337 |
| medium | int8 | es | mercado-libre_012.wav | 10.0 | 3.22 | 1.18 | 2337 |
| medium | int8 | es | mercado-libre_013.wav | 10.0 | 3.22 | 1.14 | 2337 |
| medium | int8 | es | mercado-libre_014.wav | 10.0 | 3.22 | 1.19 | 2337 |
| medium | int8 | es | mercado-libre_015.wav | 10.0 | 3.22 | 1.90 | 2337 |
| medium | int8 | es | mercado-libre_016.wav | 10.0 | 3.22 | 1.14 | 2337 |
| medium | int8 | es | mercado-libre_017.wav | 10.0 | 3.22 | 1.19 | 2337 |
| medium | int8 | es | mercado-libre_018.wav | 10.0 | 3.22 | 1.20 | 2337 |
| medium | int8 | es | mercado-libre_019.wav | 10.0 | 3.22 | 1.09 | 2337 |
| medium | int8 | es | mercado-libre_020.wav | 10.0 | 3.22 | 1.21 | 2337 |
| medium | int8 | es | mercado-libre_021.wav | 10.0 | 3.22 | 1.10 | 2337 |
| medium | int8 | es | mercado-libre_022.wav | 10.0 | 3.22 | 6.38 | 2337 |
| medium | int8 | es | mercado-libre_023.wav | 10.0 | 3.22 | 1.10 | 2337 |
| medium | int8 | es | mercado-libre_024.wav | 10.0 | 3.22 | 1.20 | 2337 |
| medium | int8 | es | mercado-libre_025.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | es | mercado-libre_026.wav | 10.0 | 3.22 | 1.17 | 2337 |
| medium | int8 | es | mercado-libre_027.wav | 10.0 | 3.22 | 1.12 | 2337 |
| medium | int8 | es | mercado-libre_028.wav | 10.0 | 3.22 | 1.21 | 2337 |
| medium | int8 | es | mercado-libre_029.wav | 10.0 | 3.22 | 1.13 | 2337 |
| medium | int8 | es | mercado-libre_030.wav | 10.0 | 3.22 | 15.44 | 2337 |
| medium | int8 | es | mercado-libre_031.wav | 10.0 | 3.22 | 1.10 | 2337 |
| medium | int8 | es | mercado-libre_032.wav | 10.0 | 3.22 | 5.68 | 2337 |
| medium | int8 | es | mercado-libre_033.wav | 10.0 | 3.22 | 1.31 | 2337 |
| medium | int8 | es | mercado-libre_034.wav | 10.0 | 3.22 | 1.15 | 2337 |
| medium | int8 | es | mercado-libre_035.wav | 10.0 | 3.22 | 1.20 | 2337 |
| medium | int8 | es | mercado-libre_036.wav | 10.0 | 3.22 | 1.18 | 2337 |
| medium | int8 | es | mercado-libre_037.wav | 10.0 | 3.22 | 1.11 | 2337 |
| medium | int8 | es | mercado-libre_038.wav | 10.0 | 3.22 | 1.17 | 2337 |
| medium | int8 | es | mercado-libre_039.wav | 10.0 | 3.22 | 1.25 | 2337 |
| medium | int8 | es | mercado-libre_040.wav | 10.0 | 3.22 | 1.19 | 2337 |
| medium | int8 | es | mercado-libre_041.wav | 10.0 | 3.22 | 1.22 | 2337 |
| medium | int8 | es | mercado-libre_042.wav | 10.0 | 3.22 | 1.16 | 2337 |
| medium | int8 | es | mercado-libre_043.wav | 2.3 | 3.22 | 0.65 | 2337 |

## Transcripciones

- `small` / `bug-lower_000.wav`: Ladies and gentlemen boys and girls land me land me lend me your ears I want to show you this really neat vulnerability in you boot that everyone's talking about not everyone, but I am so if you
- `small` / `bug-lower_001.wav`: You run the script here, KimuDrive, QMU, Bada Bing, Bada Boom, you will see the magical values, the 41414141, the 41414141, and the 424242.
- `small` / `bug-lower_002.wav`: 3e. What the hell is even going on? What are we talking about guys? We're talking about a vulnerability in you boot, the boot loader that allows you to bypass signature.
- `small` / `bug-lower_003.wav`: verification by exploiting a vulnerability in the boot loader itself. Bugs like this are really, really neat because they actually invalidate an entire trust chain in the way that weird
- `small` / `bug-lower_004.wav`: Devices like this, like embedded ones, and even ones that you're sitting in your pocket, validate if they use UBoot. Obviously, this one does not, this one might. Anyway, I'm gonna break down the bug, what went wrong, what can you can do about it, and then I'll...
- `small` / `bug-lower_005.wav`: So what the hell all this stuff means the finding today was found by a company named but been our Lee biner Lee I've done videos on their stuff before they do a really good job on finding vulnerabilities in like a lower level It's the name of the channel by the way
- `small` / `bug-lower_006.wav`: level. Low level systems like boot loaders or BMC, board management controller stuff like that. Again, not an ad for this company. Just say do a lot of good work. So the vulnerability that today
- `small` / `bug-lower_007.wav`: is a stack buffer underflow, kind of hard to say, in U-boot during the FIT image, signature verification, specifically in the FDT find.
- `small` / `bug-lower_008.wav`: regions functions. A lot of words said there. I'm gonna go into what all that means here a little bit. Okay, so enter U-boot, right? What is U-boot? Well U-boot, kind of like the name of this folder that I had, I called it DOS-boot.
- `small` / `bug-lower_009.wav`: U-boot is a system that allows you to, in the embedded world, boot other OSs, right? So typically, the way these weird devices work is you have to bring them up, you gotta get the bo-
- `small` / `bug-lower_010.wav`: or to BLI to bring the CPU to live. And then the first thing that you run on a router like this is this thing called a bootloader. A bootloader is a piece of code that allows you to run other code. The idea is,
- `small` / `bug-lower_011.wav`: You don't have to make that piece of code know how to boot against every other CPU You just bring the CPU up to the bootloader and the bootloader does the rest of the work right you can use that
- `small` / `bug-lower_012.wav`: to run your OS like Linux or Windows or whatever. So if the job of the bootloader is to run code that we want it to run why does RCE in a
- `small` / `bug-lower_013.wav`: Why does a vulnerability in U-Boot matter to anybody? Great question! What actually is interesting about U-Boot is its ability to facilitate this thing called verified boot.
- `small` / `bug-lower_014.wav`: There is this whole world of boot processes that the entire job is to make sure that code that is not meant to be ran does not run
- `small` / `bug-lower_015.wav`: on the device. And when you do this thing where we use a bunch of cryptographical algorithms using asymmetric encryption with like RSA keys and public keys and stuff to
- `small` / `bug-lower_016.wav`: sign the software image before it tries to get loaded and then using a public key on the device, we verify if that manufacturer signed image is
- `small` / `bug-lower_017.wav`: actually what we want, right? Is it the proper thing that is allowed to run on this device, right? Because maybe we just don't want anyone to be able to run any software they want on random piece of.
- `small` / `bug-lower_018.wav`: Chinese router right maybe that's the thing that they don't want okay so the issue that happens here is when you go to boot with a u-boot image in this fit format this flattened imagery for
- `small` / `bug-lower_019.wav`: it is signed with a signature. It is basically taking a private key that the manufacturer owns. We use that to embed a signature cryptographically that says, Yup, it was signed by this manufacturer.
- `small` / `bug-lower_020.wav`: manufacturer, and then we use the public key on the device to verify the signature that it was manufactured. It is the proper image, but we can invalidate this entire signature.
- `small` / `bug-lower_021.wav`: verification process, we can upload and execute a piece of code that is not intended by the manufacturer if we can find and exploit a vulnerability in
- `small` / `bug-lower_022.wav`: side of the bootloader, and this is exactly what Binaryly did, and I'm sorry if you're worth with Binaryly, and I'm mispronouncing the company's name, I'm not very good at English. Okay, so, uh, Stackbuffer Underflow in U-
- `small` / `bug-lower_023.wav`: boot during the FIT image signature verification in FDT find regions. Basically, there's code in the bootloader that is finding different regions of the actual image itself, and the vulnerability is based on the same issue.
- `small` / `bug-lower_024.wav`: is one above where we rely on the fact that FTT get name, which is a call that happens above, can fail. But this time we were interested in what it writes to the length argument upon failure.
- `small` / `bug-lower_025.wav`: the error code. Very interesting. So there's this function called fdtgetname that if for any reason in the searching of the image during this fdtgetname
- `small` / `bug-lower_026.wav`: process where it's getting the name of a leaf of this this image format right if for some reason it's searching and it finds that one of the leaves does not have a slash right so stir our
- `small` / `bug-lower_027.wav`: stir care is a thread safe version of stir care, which basically looks for a token in a string. If that fails, we set error equal to some value and we go to
- `small` / `bug-lower_028.wav`: fail. And then in the fail label, we say if the length pointer exists, we are going to write out that length pointer, which should be the output of the actual length of the name instead of
- `small` / `bug-lower_029.wav`: we're going to output an error value and that error value is FTT error bad structure and then notice that later on in the code we're going to do is we're going to say start copy on to end
- `small` / `bug-lower_030.wav`: the name that we found from that function O and also end plus equals length. Well, the issue here is that length holds a negative value. It is a large negative.
- `small` / `bug-lower_031.wav`: error code. So instead of actually moving the end of that cursor of parsing forward, the pointer moves backwards. It'll go backwards by the size or the value.
- `small` / `bug-lower_032.wav`: you of error bad structure, which is negative 11th, and then it will increment that and add a slash. As the amount of code generated by AI increases, one thing that scares me is the ability to
- `small` / `bug-lower_033.wav`: maintain that volume of code. And that's why today's video is sponsored by CodeRabbit. CodeRabbit is an AI code review tool that helps engineers manage the world of AI-generated PRs. For one of my pla-
- `small` / `bug-lower_034.wav`: forms, all of the labs I added a feature to add bookmarks to the site, right? A fairly simple feature, but adding new API endpoints like anything does create potential new security vulnerabilities in someone at the end of the day.
- `small` / `bug-lower_035.wav`: it has to review this code. Now CodeRabbit's new change stack feature makes this really, really easy. If you go to the PR overview page, you get a nice walkthrough of how the code changed, what the major changes are.
- `small` / `bug-lower_036.wav`: And also it does some really nice things where it generates diagrams for you that you can easily put into your code's documentation One of the hardest things about a growing code base is not only tech debt but knowledge debt, right?
- `small` / `bug-lower_037.wav`: making sure there's documentation that explains exactly how the code works. Now, if you go inside the change stack, you actually see that there's layers here. What CodeRabbit is doing is breaking down the PR into the separate...
- `small` / `bug-lower_038.wav`: layers and it affects, right? We have the first layer, which is just the bookmark system, right? The single couple of Go files that maintain the bookmarks. But what's even more important is you get a very
- `small` / `bug-lower_039.wav`: clean view here of okay, now how does this system integrate to the overall back end API? This gives you your semantic diff of the code base showing you what changes and how it
- `small` / `bug-lower_040.wav`: changes as a function of the new feature. You know, then we have the last layer here. We have the TypeScript interface that shows you how the new webpage created for the bookmarks is integrated into the rest of the types.
- `small` / `bug-lower_041.wav`: system. Breaking down the PR like this gives you a much better idea of exactly what the PR does. You can go through and review the code, but knowing systematically how it affects
- `small` / `bug-lower_042.wav`: the overall code base is a much cleaner path to a secure development life cycle. And guys, CodeRabbit is used all over the world. You can actually try CodeRabbit for free at this URL below. Go try CodeRabbit out and see if your pull-
- `small` / `bug-lower_043.wav`: and need some more work. And if CodeRabbit can help you get there. Thank you for responding to the video, CodeRabbit. Let's get back to it. So the end result is like actually beautiful, right? So what you have here is a stack frame for the function.
- `small` / `bug-lower_044.wav`: question, right? If the stack frame for this function, and you have this end pointer, right? So it's end is this and it's saying end plus equals length. So the pointer for end should go up and up and up. The stack grows.
- `small` / `bug-lower_045.wav`: more positively down. That is important for you to know if you don't know that, you should know that watching this channel, damn it. But what's actually happening is we have another stack frame above us and every time we exploit this vulnerability.
- `small` / `bug-lower_046.wav`: with these sections that have bad names that don't have a slash in them, we're actually subtracting the end pointer back and back and back 11 bytes at a time until eventually
- `small` / `bug-lower_047.wav`: the end pointer points to the return address of the previous stack frame. And I know you're thinking, if you're like a binary explorer person, you're like, wait, if this is its own stack frame here, isn't there nothing?
- `small` / `bug-lower_048.wav`: thing above it. Well no, the actual, the contents of this buffer lives in another stack frame below it. So just trust me, this is how it works. So end goes up above. And then using a new
- `small` / `bug-lower_049.wav`: Malformed section name that does have a slash we can write arbitrary data We want to the program counter and get it to return to whatever address we want again if this is
- `small` / `bug-lower_050.wav`: you know 32-bit like arm we're gonna have like a a a b right and if you're new to the world of exploitation right what's Happening here by overriding the the program counter value. We now have the ability to arbitrate
- `small` / `bug-lower_051.wav`: Run or at least point the CPU to a place to run other code, right? Like we could have put code and like another part of the image and we can like wrap around to like and protect
- `small` / `bug-lower_052.wav`: or whatever, like set the page table entry to make it executable. We could do a bunch of evil stuff, right? The end goal here is that we're able to run code in the console.
- `small` / `bug-lower_053.wav`: text of a bootloader that is doing signature verification without a valid signature, right? We are exploiting the code that is doing signature verification and this
- `small` / `bug-lower_054.wav`: This could invalidate an entire secure boot like process. I want to highlight that this in and of itself is not secure boot. This image would have to be signed by a secure boot key like the main.
- `small` / `bug-lower_055.wav`: that the actual motherboard has, but that being said, right? It's a really interesting primitive in the world of U-boot, of bootloader vulnerabilities. Not gonna dive super deep into a ton of these, but you have another.
- `small` / `bug-lower_056.wav`: bunch of vulnerabilities like, you know, the same kind of bug, denial of service in UBoot using an FIT image signature because of its unchecked size value. There are other parts of the code that use a
- `small` / `bug-lower_057.wav`: name pointer where that name pointer can be no pointer. And because of that, it's gonna do a bunch of other stuff. There's a whole bunch of interesting bugs on this right up. I'll put it in the description below. But it's an interesting case study in the world of
- `small` / `bug-lower_058.wav`: of U-boot of bootloader vulnerabilities. And the question for the class, the question that everyone probably wants to know the answer to, would Rust have fixed this? Uh, sort of. So again, U-boot, the whole
- `small` / `bug-lower_059.wav`: point of this is to have the CPU be brought up, the CPU runs a bootloader, the bootloader then enables the OS, right? We are at this super, super low level, name of the channel.
- `small` / `bug-lower_060.wav`: by the way, um, in the boot process. Okay. Now doing this in rust is actually like, there are these things called peripheral access crates or these things called hardware abstraction like
- `small` / `bug-lower_061.wav`: creates that allow you to write code that is not unsafe for the board in question. That being said, doing things like raw MMIO that may be there
- `small` / `bug-lower_062.wav`: isn't a peripheral extraction crate written for, it's very hard to do and it always does depend on unsafe code, even inside of the peripheral abstraction crates.
- `small` / `bug-lower_063.wav`: and access crates, there has to be by the nature of how embedded software works, right? It's global mutability, which is what Rust is designed to get rid of inside of even this code.
- `small` / `bug-lower_064.wav`: there has to be a piece of unsafe code, unfortunately. But that being said, is possible, just not easy. And yes, Rust would have fixed bugs like this, right? You would, well, actually.
- `small` / `bug-lower_065.wav`: Think about it. Yeah, I don't think you're able to fix this bug because all you're doing here is writing out to a pointer and Value right and then from there it's causing the underflow. So I'm not necessarily
- `small` / `bug-lower_066.wav`: if that's the case. You can't do raw pointers on Rust. So there you go. That's the answer. Actually, you know, the Rust error and not error, the okay and error type, the result type would fix this. Because what the...
- `small` / `bug-lower_067.wav`: the classical issue in C, where you're using the error code in the error state as the actual value slot, right? Or this is like the entire problem that
- `small` / `bug-lower_068.wav`: the Rust T and E or Rust result type fixes. And before we leave, by the way, in the code here, what we're showing you, so what I did here is I wrote, I compiled UBoot, the vulnerable version, which there is no patch.
- `small` / `bug-lower_069.wav`: by the way yet. I compiled UBOO to run in QMU. QMU is like a system emulator. It emulates an arm chip. And then I ran UBOO and I tried to signature validate with the
- `small` / `bug-lower_070.wav`: the FIT image that has the vulnerable structures in it. And then by using this, I was able to take control of the registers that are put on the stack, right? So R10, the frame pointer, and then ultimately,
- `small` / `bug-lower_071.wav`: currently PC, where PC is the return address that we're going to execute next, right? And by doing that, this proves that I have at least the ability to point the CPU to other places.
- `small` / `bug-lower_072.wav`: in the code that I want to run my my evil stuff right now obviously the question of like nx and aslar comes up um but that is a different question for a different video anyway thank you for watching guys I appreciate it if you like the stuff
- `small` / `bug-lower_073.wav`: check out my other stuff, and then give me a little kiss on the cheek. Okay, we'll see you later, goodbye.
- `small` / `mercado-libre_000.wav`: Mercado pago acaba de empeorar y para colmo nos lo hará ver como algo bueno. Dos cambios relevantes, ahora las condiciones para mantener el 12%
- `small` / `mercado-libre_001.wav`: de rendimiento van a cambiar dependiendo de la persona. A mí, por ejemplo, me sigue pidiendo lo de depositar 3 mil pesos, pero varias personas me han compartido que a ellas les pide
- `small` / `mercado-libre_002.wav`: gastar. Distintos montos, mil, dos mil pesos, son los que me llegaron a contar. Si a ti te pide más o alguna condición diferente, por favor cuéntanos en los comentarios.
- `small` / `mercado-libre_003.wav`: No cambio, regrese el 15% en su sección de apartados, pero para esto pide si o si suscribirse a MeliPlus, para lo cual hay paquetes desde 49 hasta casi 400.
- `small` / `mercado-libre_004.wav`: los pesos. Y te adelanto, creo que esto solo vale la pena si ya usaras los otros beneficios de esta suscripción, de lo contrario paso sin ver. Veamos entonces a
- `small` / `mercado-libre_005.wav`: aclaraciones y condiciones importantes rápidamente. Esto de condiciones distintas por cada persona no parece que sea un error ni algo que se vaya desplegando. En mi caso, depositar
- `small` / `mercado-libre_006.wav`: los 3000 y ya me marcó la condición como cumplida. Tómalo con pinzas, pero preguntándole a su asistente de inteligencia artificial, directamente me dijo que si hay personas a las que les
- `small` / `mercado-libre_007.wav`: de gastar, pero más importante, dice que la condición puede cambiar de un mes a otro y que no hay una regla clara para definir qué requisito te van a pedir, entonces
- `small` / `mercado-libre_008.wav`: Si como a mi te dejó este mes una de depósito y piensas que nada cambió que sigue igual, pues toca pensar de nuevo. Cuéntame por favor en los comentarios a ti que te esta pidiendo.
- `small` / `mercado-libre_009.wav`: y ya quiere que gastes qué monto pide, él si te avisó o no por correo o alguna notificación al menos. Luego el 15% solo va a aplicar a su sección de apartados y a ver.
- `small` / `mercado-libre_010.wav`: Pero esto no está tan mal, sigue siendo dinero siempre disponible, solo que está en otra parte de la aplicación, lo puedes retirar cuando gustes. La aclaración importante es que no importa.
- `small` / `mercado-libre_011.wav`: la modalidad en la que te encuentres, el tope de 25 mil pesos para recibir la mejor tasa, ese sigue estando vigente. Por ejemplo, yo ya tenía topados mis apartados eso
- `small` / `mercado-libre_012.wav`: no me lo marca al 15% contra tmeli plus para este video, deposite 3000 adicionales a la vista y eso no me lo marca al 12 sino al 5.4%, por lo tanto
- `small` / `mercado-libre_013.wav`: esto complica un poco la explicación completa. Vamos por pasos. Parece ser que si no complies ninguna condición te quedas con el 5.4% base, que incluso puede
- `small` / `mercado-libre_014.wav`: ser menor. Si únicamente cumples la condición de gasto o depósito, depende lo que te piden, subes al 12%, esta tasa tanto a la vista como en apartados.
- `small` / `mercado-libre_015.wav`: Y puedes depositar más, pero el excedente ya baja de nuevo a la tasa base, 5% poco más. Finalmente si tienes MeliPlus es donde más opciones hay.
- `small` / `mercado-libre_016.wav`: es elegir o 12% a la vista o 15% en apartados, aunque obviamente esta última opción es la preferible, pero entre ambos lo más que pueden sumar son 25 mil...
- `small` / `mercado-libre_017.wav`: invertidos. También puedes depositar más, pero entonces bajas al 5.4% base. El asterisco, en todas las partes de esta tabla, que dice Sintope, es que puedes depositar...
- `small` / `mercado-libre_018.wav`: citar lo que gustes, pero recuerda que tienen esa condición rara de que solo los primeros 25 mil en el mes se pueden invertir, eso parece que no cambia, solo enreda las cosas.
- `small` / `mercado-libre_019.wav`: al menos así es como está funcionando en este momento en mi aplicación y a ver mercadupago me parece que está haciendo las cosas con las patas tener condiciones diferentes para
- `small` / `mercado-libre_020.wav`: cada quien y que puedan modificarse de un mes a otro es muy molesto. Hacer los cambios súbitos sin mayor aclaración es frustrante, pero sabes que es peor que en sus terrenos
- `small` / `mercado-libre_021.wav`: Por menos si condiciones, revisados hoy el primer día de septiembre, siguen pidiendo 3.000 de depósito. Sé que en la letra pequeña avisan que pueden cambiar en cualquier momento.
- `small` / `mercado-libre_022.wav`: pero no solo ahí dice que tienen que hacer esas modificaciones al menos 3 días antes de que entrenen vigor sino que además no es lo mismo cambiar los términos, avisarnos
- `small` / `mercado-libre_023.wav`: y después implementar los cambios que tener unos términos vigentes en este momento en su sitio, pero al mismo tiempo ande reaplicando otras condiciones a tus clientes y para
- `small` / `mercado-libre_024.wav`: rematar no ser claro en qué te vasas para decidir a quién le pides gastar a quién le pides depositar literal no encuentro forma de defenderlos y no sé si como banco podrían
- `small` / `mercado-libre_025.wav`: este tipo de movidas, pero bueno solo quería desahogarme, continuemos. Entonces combina la inversión en mercado pago con estas nuevas condiciones y ya te lo decía, la respuesta corte
- `small` / `mercado-libre_026.wav`: Si usarás el resto de beneficios de MeliPlus, especialmente si vas por el plan de al menos $99 pesos, entonces sí, de otra forma es un tajante no.
- `small` / `mercado-libre_027.wav`: rápidos, con el 12% de rendimiento y 25 mil topados, ganábamos unos 250 pesos de rendimiento al mes, con el 15% esta ganancia subiría
- `small` / `mercado-libre_028.wav`: a unos 314 pesos y por eso mismo el plan de 50 pesos no tiene mucho sentido, si a eso que vas a ganar le restas el costo de la membresía queda solo con unos 2.000 pesos.
- `small` / `mercado-libre_029.wav`: 264 pesos, son solo unos 14, más de lo que tenías ya con el 12%, así que si lo ves como pure inversión no es nada atractivo, digo
- `small` / `mercado-libre_030.wav`: Si te cambiaron la condición de depósito a una de gasto, entiendo que prefieras gastar 50 pesos de una vez y olvidarte de los mil, dos mil o más que te pidan, pero pagar por el...
- `small` / `mercado-libre_031.wav`: invertir eso no me parece bien, sobre todo teniendo otras opciones, solo por mencionar algunas rápidamente, el ahorro ultra de banco plata da 15% sin condición.
- `small` / `mercado-libre_032.wav`: por 60 días. Open Bank sigue con 13% sin condición y su tope de 30.000 también te deja ganar unos 300 pesos mensuales. La cajita turbueno sigue...
- `small` / `mercado-libre_033.wav`: con 13% pidiendo solo una compra al mes, pero regresando a mercado pago, ya si te vas por el plan de 99 pesos, tienes disney plus, aunque sea con comerciales.
- `small` / `mercado-libre_034.wav`: lo cual directamente con ellos costaría unos $129 pesos. Acá baja $99 y tienes más ventajas, envíos más rápidos si es que compras en la plataforma de...
- `small` / `mercado-libre_035.wav`: cuentos en otros servicios, un cashback medio feo, hay que decirlo, y que solo aplica si tienes su tarjeta de crédito, pero bueno, reitero, son cosas que ya debes querer o...
- `small` / `mercado-libre_036.wav`: te sirvan, porque si no, estas mejor con el 12%, aunque eso si, solo si te dejaron la condición como depositar no como gastar, eso de gastar tanto para no re...
- `small` / `mercado-libre_037.wav`: recibir ningún beneficio más que el 12% es una cachetada totalmente, hasta están peor que Revolute. Otro punto importante es que varias personas están reportando que ya no
- `small` / `mercado-libre_038.wav`: desaparece la opción de depositar a su cuenta de mercado pago con cargo a tarjeta de otro banco, lo cual parece impedirles hacer ese famoso hack de mercado pago igual a
- `small` / `mercado-libre_039.wav`: Yo te cuento que actualizando mi aplicación al día de hoy, todavía me aparece en la sección de ingresar dinero, en la parte de abajo. No obstante, si ahora el requisito del 12%
- `small` / `mercado-libre_040.wav`: va a depender de la persona, no me sorprendería que también existan funcionalidades que algunos tengan y otros no. De hecho no me parece descabellado pensar que justo este tipo de
- `small` / `mercado-libre_041.wav`: hacks hayan llevado al mercado pago a cambiar sus términos, pero bueno, sabíamos que vendrían cambios en la inversión de mercado pago, hace poco hicimos un video en el que te contaba
- `small` / `mercado-libre_042.wav`: como el no ser banco y el aliarse con GBM, les están poniendo el pie para ofrecer mejores condiciones. Te lo recomiendo por acá, porque ayuda a entender mucho mejor el cambio que hay.
- `small` / `mercado-libre_043.wav`: ser un gusto verte por allá, bye.
- `medium` / `bug-lower_000.wav`: Ladies and gentlemen boys and girls land me land me lend me your ears I want to show you this really neat vulnerability in you boot that everyone's talking about not everyone, but I am so if you
- `medium` / `bug-lower_001.wav`: If you run the script here, QEMU drive, Q-M-U, bada bing bada boom, you will see the magical values, the 41, 41, 41, 41, the 41, 41, 41, and the 42, 42, 42.
- `medium` / `bug-lower_002.wav`: 3E. What the hell is even going on? What are we talking about guys? We're talking about a vulnerability in U-Boot, the bootloader that allows you to bypass signature.
- `medium` / `bug-lower_003.wav`: verification by exploiting a vulnerability in the bootloader itself. Bugs like this are really, really neat because they actually invalidate an entire trust chain in the way that weird.
- `medium` / `bug-lower_004.wav`: Devices like this, like embedded ones and even ones that you're sitting in your pocket, validate if they use you boot. Obviously this one does not. This one might anyway, I'm going to break down the bug. What went wrong? What can you can do about it? And then also.
- `medium` / `bug-lower_005.wav`: So what the hell all this stuff means. The finding today was found by a company named Benarly, Binerly. I've done videos on their stuff before. They do a really good job on finding vulnerabilities in like lower level. It's the name of the channel, by the way.
- `medium` / `bug-lower_006.wav`: level low level systems like bootloaders or BMC board management controller stuff like that again, not an ad for this company just they do a lot of good work. So the vulnerability of the day
- `medium` / `bug-lower_007.wav`: is a stack buffer underflow kind of hard to say in a the in U-boot during the FIT image signature verification specifically in the FDT fine.
- `medium` / `bug-lower_008.wav`: Regions functions a lot of words said there. I'm gonna go into what all that means here a little bit Okay, so enter you boot right? What is you boot? Well you boot kind of like the name of this folder that I had I called it das boot
- `medium` / `bug-lower_009.wav`: U-Boot is a system that allows you to, in an embedded world, boot other OSs, right? So typically the way these weird devices work is you have to bring them up. You got to get the.
- `medium` / `bug-lower_010.wav`: or to be alive to bring the CPU to live. And then the first thing that you run on a router like this is this thing called a bootloader. A bootloader is a piece of code that allows you to run other code. The idea is
- `medium` / `bug-lower_011.wav`: You don't have to make that piece of code know how to boot against every other CPU. You just bring the CPU up to the bootloader and the bootloader does the rest of the work, right? You can use that.
- `medium` / `bug-lower_012.wav`: bootloader to run your OS like Linux or Windows or whatever. So if the job of the bootloader is to run code that we want it to run, why does RCE in a bootloader
- `medium` / `bug-lower_013.wav`: bootloader matter? Why does the vulnerability in U-Boot matter to anybody? Great question. What actually is interesting about U-Boot is its ability to facilitate this thing called verified boot, okay?
- `medium` / `bug-lower_014.wav`: There is this whole world of boot processes that the entire job is to make sure that code That is not meant to be ran does not run
- `medium` / `bug-lower_015.wav`: on the device and we do this thing where we use a bunch of cryptographical algorithms using asymmetric encryption with like RSA keys and public keys and stuff to
- `medium` / `bug-lower_016.wav`: sign the software image before it tries to get loaded, and then using a public key on the device, we verify if that manufacturer signed image is.
- `medium` / `bug-lower_017.wav`: actually what we want, right? Is it the proper thing that is allowed to run on this device, right? Because maybe we just don't want anyone, people to run any software they want on random piece of.
- `medium` / `bug-lower_018.wav`: of Chinese router, right? Maybe that's a thing that they don't want. Okay. So the issue that happens here is when you go to boot with a U-Boot image in this fit format, this flattened image tree for.
- `medium` / `bug-lower_019.wav`: It is signed with a signature. It is basically taking a private key that the manufacturer owns. We use that to embed a signature cryptographically that says, yep, it was signed by this.
- `medium` / `bug-lower_020.wav`: And then we use the public key on the device to verify the signature that it was manufactured. It is a proper image, but we can invalidate this entire signature.
- `medium` / `bug-lower_021.wav`: verification process, we can upload and execute a piece of code that is not intended by the manufacturer. If we can find an exploit a vulnerability in
- `medium` / `bug-lower_022.wav`: side of the bootloader. And this is exactly what binary Lee did. And I'm sorry if you're worth with binary Lee and I'm mispronouncing the company's name. I'm not very good at English. Okay. So, uh, stack buffer underflow and you.
- `medium` / `bug-lower_023.wav`: boot during the FIT image signature verification FDT find regions. Basically, there's code in the bootloader that is finding different regions of the actual image itself. And the vulnerability is based on the same issue.
- `medium` / `bug-lower_024.wav`: one above, where we rely on the fact that FTT get name, which is a call that happens above can fail. But this time we're interested in what it writes to the length argument upon failure.
- `medium` / `bug-lower_025.wav`: the error code, very interesting. So there's this function called FDT get name that if for any reason in this searching of the image during this FDT get name.
- `medium` / `bug-lower_026.wav`: process where it's getting the name of a leaf of this, uh, this image format, right? If for some reason it's searching and it finds that one of the leaves does not have a slash, right?
- `medium` / `bug-lower_027.wav`: care is a thread safe version of stir care, which basically looks for a token in a string. If that fails, we set error equal to some value and we go to.
- `medium` / `bug-lower_028.wav`: And then in the fail label, we say if the length pointer exists, we are going to write out that length pointer, which should be the output of the actual length of the name instead.
- `medium` / `bug-lower_029.wav`: we're going to output an error value and that error value is FTT error bad structure. And then notice that later on in the code we're going to do is we're going to say start copy on to end.
- `medium` / `bug-lower_030.wav`: the name that we found from that function. Oh, and also end plus equals length. Well, the issue here is that length holds a negative value. It is a large negative.
- `medium` / `bug-lower_031.wav`: of error code. So instead of actually moving the end of that cursor of parsing forward, the pointer moves backwards, it'll go backwards by the size or the value.
- `medium` / `bug-lower_032.wav`: you of error bad structure, which is negative 11th. And then it will increment that and add a slash as the amount of code generated by AI increases. One thing that scares me is the ability to.
- `medium` / `bug-lower_033.wav`: maintain that volume of code. And that's why today's video is sponsored by CodeRabbit. CodeRabbit is an AI code review tool that helps engineers manage the world of AI generated PRs. For one of my plat-
- `medium` / `bug-lower_034.wav`: I added a feature to add bookmarks to the site, right? A fairly simple feature, but adding new API endpoints like anything does create potential new security vulnerabilities. And someone at the end of the day
- `medium` / `bug-lower_035.wav`: it has to review this code. Now, CodeRabbit's new change stack feature makes this really, really easy. If you go to the PR overview page, you get a nice walkthrough of how the code changed, what the major changes are.
- `medium` / `bug-lower_036.wav`: And also it does some really nice things where it generates diagrams for you that you can easily put into your code's documentation. One of the hardest things about a growing code base is not only tech debt, but knowledge debt, right?
- `medium` / `bug-lower_037.wav`: making sure there's documentation that explains exactly how the code works. Now, if you go inside the change stack, you actually see that there's layers here. What CodeRabbit is doing is breaking down the PR into the separate.
- `medium` / `bug-lower_038.wav`: layers that it affects, right? We have the first layer, which is just the bookmark system, right? These single couple of Go files that maintain the bookmarks. But what's even more important is you get a very.
- `medium` / `bug-lower_039.wav`: clean view here of, okay, now how does this system integrate to the overall backend API? This gives you your semantic diff of the code base showing you what changes and how it
- `medium` / `bug-lower_040.wav`: changes as a function of the new feature. You know, then we have the last layer here. We have the TypeScript interface that shows you how the new webpage created for the bookmarks is integrated into the rest of the TypeScript.
- `medium` / `bug-lower_041.wav`: system. Breaking down the PR like this guys gives you a much better idea of exactly what the PR does. You can go through and review the code obviously, but knowing systematically how it
- `medium` / `bug-lower_042.wav`: the overall code base, is a much cleaner path to a secure development life cycle. And guys, CodeRabbit is used all over the world. You can actually try CodeRabbit for free at this URL below. Go try CodeRabbit out and see if your pull record
- `medium` / `bug-lower_043.wav`: need some more work and if CodeRabbit can help you get there. Thank you for sponsoring the video, CodeRabbit. Let's get back to it. So the end result is like actually beautiful, right? So what you have here is stack frame for the functioning.
- `medium` / `bug-lower_044.wav`: You have the stack frame for this function. And you have this end pointer. So it's end is this. And it's saying end plus equals length. So the pointer for end should go up and up and up. The stack grows.
- `medium` / `bug-lower_045.wav`: more positively down that is important for you to know. If you don't know that you should know that watching this channel. Damn it. But what's actually happening is we have another stack frame above us and every time we exploit this vulnerability.
- `medium` / `bug-lower_046.wav`: with the sections that have bad names that don't have a slash in them. We're actually subtracting the end pointer back and back and back 11 bytes at a time until eventually.
- `medium` / `bug-lower_047.wav`: the end pointer points to the return address of the previous stack frame. I know you're thinking, if you're like a binary exploiter person, you're like, wait, if this is its own stack frame here, isn't there nothing?
- `medium` / `bug-lower_048.wav`: Well, no, the actual, the contents of this buffer lives in another stack frame below it. So just trust me, this is how it works. So end goes up, up, up. And then using a new
- `medium` / `bug-lower_049.wav`: malformed section name that does have a slash, we can write arbitrary data we want to the program counter and get it to return to whatever address we want. Again, if this is
- `medium` / `bug-lower_050.wav`: 32-bit like ARM, we're going to have like A, A, A, B, right? And if you're new to the world of exploitation, what's happening here, by overriding the program counter value, we now have the ability to arbitrarily
- `medium` / `bug-lower_051.wav`: or at least point the CPU to a place to run other code, right? Like, we could have put code in, like, another part of the image, and we can, like, wrap around to, like, M protect or...
- `medium` / `bug-lower_052.wav`: or whatever, like set the page table entry to make it executable. We do a bunch of evil stuff, right? The end goal here is that we're able to run code in the content.
- `medium` / `bug-lower_053.wav`: of a bootloader that is doing signature verification without a valid signature, right? We are exploiting the code that is doing signature verification and this
- `medium` / `bug-lower_054.wav`: This could invalidate an entire secure boot like process. I want to highlight that this in and of itself is not secure boot. This image would have to be signed by a secure boot key, like the main.
- `medium` / `bug-lower_055.wav`: That's your key that the actual motherboard has but that being said, right? It's really interesting primitive in the world of of you boot of bootloader vulnerabilities Not gonna have super deep into a ton of these, but you have another
- `medium` / `bug-lower_056.wav`: bunch of vulnerabilities, like, you know, the same kind of bug denial of service in you boot using an FIT image signature because of an unchecked size value. There are other parts of the code that use a.
- `medium` / `bug-lower_057.wav`: where that name pointer can be null pointer. And because of that, it's going to do a bunch of other stuff. There's a whole bunch of interesting bugs on this write-up. I'll put it in the description below. But it's an interesting case study in the world of
- `medium` / `bug-lower_058.wav`: of U-Boot, of bootloader vulnerabilities. And the question for the class, the question that everyone probably wants to know the answer to would Rust have fixed this? Sort of. So again, U-Boot, the whole.
- `medium` / `bug-lower_059.wav`: point of this is to have the CPU be brought up. The CPU runs a bootloader. The bootloader then enables the OS, right? We are at this super, super low level, name of the champ.
- `medium` / `bug-lower_060.wav`: by the way, in the boot process. Okay. Now, doing this in Rust is actually like, there are these things called peripheral access crates or these things called hardware abstraction.
- `medium` / `bug-lower_061.wav`: creates that allow you to write code that is not unsafe for the board in question. That being said, doing things like raw MMIO that maybe they're
- `medium` / `bug-lower_062.wav`: isn't a peripheral extraction create written for is very hard to do. And it always does depend on unsafe code, even inside of the peripheral abstraction creator.
- `medium` / `bug-lower_063.wav`: access crates, there is, there has to be by the nature of how embedded software works, right? It's global mutability, which is what Rust is designed to get rid of inside of even this code.
- `medium` / `bug-lower_064.wav`: There has to be a piece of unsafe code, unfortunately. But that being said, it's possible, just not easy. And yes, Rust would have fixed bugs like this, right? You would, well, actually...
- `medium` / `bug-lower_065.wav`: I don't think you're able to fix this bug because all you're doing here is writing out to a pointer and a value right and then from there it's causing the underflow so I'm not necessarily
- `medium` / `bug-lower_066.wav`: I'm not sure if that's the case. You can't do raw pointers in Rust. So there you go. That's the answer. Actually, the Rust error and not error, the OK and error type, the result type would fix this.
- `medium` / `bug-lower_067.wav`: the classical issue in C, where you're using the error code in the error state as the actual value slot. Right. This is like the entire problem that.
- `medium` / `bug-lower_068.wav`: Rust T&E or Rust Result Type fixes. And before we leave, by the way, in the code here, what we're showing you. So what I did here is I wrote a compiled U-Boot, the vulnerable version, which there is no patch.
- `medium` / `bug-lower_069.wav`: for, by the way, yet I compiled you boot to run in QMU. QMU is like a system emulator. It emulates an arm chip. And then I ran UBOO and I tried to signature validate with the.
- `medium` / `bug-lower_070.wav`: the FIT image that has the vulnerable structures in it. And then by using this, I was able to take control of the registers that are put on the stack. So R10, the frame pointer, and then ultimate.
- `medium` / `bug-lower_071.wav`: where PC is the return address that we're going to execute next. By doing that, this proves that I have at least the ability to point the CPU to other places.
- `medium` / `bug-lower_072.wav`: is in the code that I want to run my evil stuff right now. Obviously, the question of NX and ASLR comes up, but that is a different question for a different video. Anyway, thank you for watching, guys. I appreciate it. If you like this stuff, share it with your friends.
- `medium` / `bug-lower_073.wav`: check out my other stuff, and then give me a little kiss on the cheek. Okay, we'll see you later, goodbye.
- `medium` / `mercado-libre_000.wav`: Mercado pago acaba de empeorar y para colmo nos lo hará ver como algo bueno, dos cambios relevantes, ahora las condiciones para mantener el 12 por ciento
- `medium` / `mercado-libre_001.wav`: de rendimiento van a cambiar dependiendo de la persona, a mí por ejemplo, me sigue pidiendo lo de depositar 3000 pesos, pero varias personas me han compartido que a ellas les pide.
- `medium` / `mercado-libre_002.wav`: gastar, distintos montos 1000, 2000 pesos son los que me llegaron a contar, si a ti te pide más o alguna condición diferente por favor cuéntanos en los comentarios.
- `medium` / `mercado-libre_003.wav`: cambio regrese el 15% en su sección de apartados, pero para esto pide sí o sí suscribirse a Meli Plus, para lo cual hay paquetes desde 49 hasta casi 400.
- `medium` / `mercado-libre_004.wav`: pesos. Y te adelanto, creo que esto solo vale la pena si ya usarás los otros beneficios de esta suscripción, de lo contrario paso sin ver. Veamos entonces a
- `medium` / `mercado-libre_005.wav`: claraciones y condiciones importantes rápidamente, esto de condiciones distintas por cada persona, no parece que sea un error ni algo que se vaya desplegando, en mi caso deposite
- `medium` / `mercado-libre_006.wav`: los 3000 y ya me marcó la condición como cumplida, tómalo con pinzas, pero preguntándole a su asistente de inteligencia artificial, directamente me dijo que si hay personas a las que les
- `medium` / `mercado-libre_007.wav`: de gastar, pero más importante dice que la condición puede cambiar de un mes a otro, y que no hay una regla clara para definir qué requisito te van a pedir, entonces…
- `medium` / `mercado-libre_008.wav`: si como a mi te dejo este mes una de depósito y pensas que nada cambió que sigue igual pues toca pensar de nuevo, cuéntame por favor en los comentarios a ti que te está pidiendo, si
- `medium` / `mercado-libre_009.wav`: si ya quiere que gastes, que monto pide, el si te aviso o no por correo o alguna notificación al menos. Luego el 15% solo va a aplicar a su sección de apartados, y a ver
- `medium` / `mercado-libre_010.wav`: esto no está tan mal, sigue siendo dinero siempre disponible, solo que está en otra parte de la aplicación, lo puedes retirar cuando gustes, la aclaración importante es que no importa
- `medium` / `mercado-libre_011.wav`: la modalidad en la que te encuentres, el tupe de 25 mil pesos para recibir la mejor tasa, ese sigue estando vigente. Por ejemplo, yo ya tenía topados mis apartados, eso…
- `medium` / `mercado-libre_012.wav`: lo marca al 15%, contrate melee plus para este video, deposite 3000 adicionales a la vista, y eso no me lo marca al 12, sino al 5.4%, por lo tanto,
- `medium` / `mercado-libre_013.wav`: esto complica un poco la explicación completa, vamos por pasos, parece ser que si no cumples ninguna condición, te quedas con el 5.4% base, que incluso puedes
- `medium` / `mercado-libre_014.wav`: ser menor, si únicamente cumples la condición de gasto o depósito depende de lo que te piden, subes al 12%, esta tasa tanto a la vista como en apartados.
- `medium` / `mercado-libre_015.wav`: y puedes depositar más, pero el excedente ya baja de nuevo a la tasa base, 5% o poco más. Si tienes Mary Plus, es donde más opciones hay.
- `medium` / `mercado-libre_016.wav`: es elegir o 12% a la vista o 15% en apartados, aunque obviamente esta última opción es la preferible, pero entre ambos lo más que pueden sumar son 25,000.
- `medium` / `mercado-libre_017.wav`: invertidos, también puedes depositar más, pero entonces bajas al 5.4 por ciento base, el asterisco en todas las partes de esta tabla que dice sin tope es que puedes
- `medium` / `mercado-libre_018.wav`: lo que gustes, pero recuerda que tienen esa condición rara de que solo los primeros 25.000 en el mes se pueden invertir, eso parece que no cambia, solo enreda las cosas.
- `medium` / `mercado-libre_019.wav`: al menos así es como está funcionando en este momento en mi aplicación, y a ver mercado pago me parece que está haciendo las cosas con las patas, tener condiciones diferentes para
- `medium` / `mercado-libre_020.wav`: cada quien y que puedan modificarse de un mes a otro es muy molesto, hacer los cambios súbitos sin mayor aclaración es frustrante, pero sabes que es peor, que en sus tres
- `medium` / `mercado-libre_021.wav`: menos y condiciones revisados hoy el primer día de septiembre siguen pidiendo 3000 de depósito, sé que en la letra pequeña avisan que pueden cambiar en cualquier momento.
- `medium` / `mercado-libre_022.wav`: pero no solo ahí dice que tienen que hacer esas modificaciones al menos tres días antes de que entren en vigor, sino que además no es lo mismo cambiar los términos, avisarnos
- `medium` / `mercado-libre_023.wav`: después de implementar los cambios, que tener unos términos vigentes en este momento en su sitio, pero al mismo tiempo ande replicando otras condiciones a tus clientes.
- `medium` / `mercado-libre_024.wav`: rematar no ser claro en qué te basas para decidir a quién le pides gastar, a quién le pides depositar, literal no encuentro forma de defenderlos y no sé si como banco podrían hacer
- `medium` / `mercado-libre_025.wav`: este tipo de movidas, pero bueno solo quería desahogarme continuemos, entonces combina la inversión en mercado pago con estas nuevas condiciones, ya te lo decía la respuesta corta
- `medium` / `mercado-libre_026.wav`: si usarás el resto de beneficios de Meli Plus, especialmente si vas por el plan de al menos 99 pesos, entonces sí, de otra forma es un tajante no. Número 3.
- `medium` / `mercado-libre_027.wav`: rápidos, con el 12% de rendimiento y 25 mil topados ganábamos unos 250 pesos de rendimiento al mes, con el 15% esta ganancia subiría.
- `medium` / `mercado-libre_028.wav`: unos 314 pesos, y por eso mismo el plan de 50 pesos no tiene mucho sentido, si a eso que vas a ganar le restas el costo de la membresía queda solo con unos 2.000 pesos.
- `medium` / `mercado-libre_029.wav`: 164 pesos, son sólo unos 14 más de lo que tenías ya con el 12%, así que si lo ves como pura inversión no es nada atractivo, digo…
- `medium` / `mercado-libre_030.wav`: Si te cambiaron la condición de depósito a una de gasto, entiendo que prefieras gastar 50 pesos de una vez y olvidarte de los 1000, 2000 o más que te pidan, pero pagar por
- `medium` / `mercado-libre_031.wav`: invertir eso no me parece bien, sobre todo teniendo otras opciones, solo por mencionar algunas rápidamente, el ahorro ultra de banco plata da 15% sin condiciones.
- `medium` / `mercado-libre_032.wav`: por 60 días, OpenBank sigue con 13% sin condición y su tope de 30.000 también te deja ganar unos 300 pesos mensuales, la cajita Turbueno sigue con 300 pesos mensuales, la cajita Turbueno sigue con
- `medium` / `mercado-libre_033.wav`: 13% pidiendo solo una compra al mes, pero regresando a mercado pago, ya si te vas por el plan de 99 pesos, tienes Disney Plus, aunque sea con comerciales.
- `medium` / `mercado-libre_034.wav`: cual directamente con ellos, costaría unos 129 pesos, acá baja 99 y tienes más ventajas, envíos más rápidos si es que compras en la plataforma, de
- `medium` / `mercado-libre_035.wav`: cuentos en otros servicios, un cashback medio feo hay que decirlo y que solo aplica si tienes su tarjeta de crédito, pero bueno reitero son cosas que ya debes querer o querer.
- `medium` / `mercado-libre_036.wav`: te sirvan, porque si no, estás mejor con el 12%, aunque eso sí, solo si te dejaron la condición como depositar no como gastar, eso de gastar tanto para no re…
- `medium` / `mercado-libre_037.wav`: ningún beneficio más que el 12% es una cachetada totalmente, hasta es tan peor que Revolute. Otro punto importante es que varias personas están reportando que ya no
- `medium` / `mercado-libre_038.wav`: les aparece la opción de depositar a su cuenta de mercado pago con cargo a tarjeta de otro banco, lo cual parece impedirles hacer ese famoso hack de mercado pago igual a.
- `medium` / `mercado-libre_039.wav`: Yo te cuento que actualizando mi aplicación al día de hoy todavía me aparece en la sección de ingresar dinero, en la parte de abajo, no obstante si abro el requisito del 12%
- `medium` / `mercado-libre_040.wav`: va a depender de la persona, no me sorprendería que también existan funcionalidades que algunos tengan y otros no, de hecho no me parece descabellado pensar que justo este tipo de
- `medium` / `mercado-libre_041.wav`: hayan llevado a mercado pago a cambiar sus términos, pero bueno sabíamos que vendrían cambios en la inversión de mercado pago, hace poco hicimos un vídeo en el que te contaba
- `medium` / `mercado-libre_042.wav`: el no ser banco y el aliarse con gbm les están poniendo el pie para ofrecer mejores condiciones, te lo recomiendo por acá porque ayuda a entender mucho mejor el cambio que
- `medium` / `mercado-libre_043.wav`: será un gusto verte por allá, bye.
