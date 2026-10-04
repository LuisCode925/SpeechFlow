"""Prueba de captura del micrófono: graba entre dos Enter y guarda un WAV mono 16 kHz.

`--list-devices` muestra los dispositivos de entrada disponibles.
"""
import argparse

import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"


def list_devices() -> None:
    default_input = sd.default.device[0]
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            mark = ">" if index == default_input else " "
            print(f"{mark} {index:2d} {device['name']} ({device['max_input_channels']} canales de entrada)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-devices", action="store_true", help="lista los dispositivos de entrada y termina")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return


if __name__ == "__main__":
    main()
