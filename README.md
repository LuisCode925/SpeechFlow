# SpeechFlow
SpeechFlow es una herramienta para el dictado por voz, en la cual mediante un micrófono convierte nuestras voz en palabras,
su meta es poder ser utilizada en cualquier parte del sistema sin importar la herramienta. Solo actualmente disponible en 
Linux Debian 13. 

## FP16 en cuda 12.4 en GTX 1060 6GB
La arquitectura Pascal (Compute Capability 6.1) de la Nvidia GTX 1060 6GB soporta FP16 (precisión de 16 bits), pero carece de núcleos Tensor, por lo que su rendimiento en FP16 es lento (emulado o de baja velocidad en comparación con FP32). Además, CUDA 12.4 es compatible con la GTX 1060 a nivel de driver y ejecución, pero no acelerará de forma nativa ni eficiente el cálculo en FP16 como lo haría en tarjetas con arquitecturas más modernas (Volta, Turing, Ampere o posteriores).

## Comando para fragmentar los samples.
```bash
ffmpeg -i audio_original.wav -f segment -segment_time 10 -c copy segmento_%03d.wav
```