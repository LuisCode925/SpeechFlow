"""Tests de speechflow.audio con sounddevice falseado."""
import wave

import numpy as np
import pytest
import sounddevice as sd

from speechflow import audio
from speechflow.audio import Recorder
from speechflow.transcriber import SAMPLE_RATE

from conftest import InputStreamFalso, dispositivo


def test_parse_device_entero():
    assert audio.parse_device("3") == 3


def test_parse_device_nombre():
    assert audio.parse_device("Realtek") == "Realtek"


def test_list_devices_marca_el_defecto(capsys):
    audio.list_devices()
    salida = capsys.readouterr().out.splitlines()
    assert len(salida) == 2  # el dispositivo sin entrada no se lista
    assert salida[0].startswith(">") and "Realtek ALC" in salida[0]
    assert salida[1].startswith(" ") and "USB Mic" in salida[1]


def test_default_device_prefiere_realtek():
    assert audio.default_device() == 1


def test_default_device_sin_realtek(sounddevice_falso):
    sounddevice_falso.dispositivos[1]["name"] = "Otro"
    assert audio.default_device() is None


def test_input_devices_ignora_salidas():
    assert audio.input_devices() == [1, 2]


def test_input_devices_vacio(sounddevice_falso):
    sounddevice_falso.dispositivos.clear()
    assert audio.input_devices() == []


def test_refresh_devices_reinicia_portaudio(sounddevice_falso):
    audio.refresh_devices()
    assert sounddevice_falso.reinicios == 1


class TestDeviceIndex:
    def test_defecto(self):
        assert audio.device_index(None) == 1

    def test_entero(self):
        assert audio.device_index(2) == 2

    def test_nombre(self):
        assert audio.device_index("usb") == 2

    def test_sin_clave_index_entero(self, sounddevice_falso):
        sounddevice_falso.con_index = False
        assert audio.device_index(2) == 2

    def test_sin_clave_index_nombre(self, sounddevice_falso):
        sounddevice_falso.con_index = False
        assert audio.device_index("USB Mic") == 2

    def test_sin_clave_index_defecto(self, sounddevice_falso):
        sounddevice_falso.con_index = False
        assert audio.device_index(None) == 1

    def test_inexistente(self):
        assert audio.device_index(99) is None
        assert audio.device_index("nada") is None

    def test_solo_salida(self):
        assert audio.device_index(0) is None


class TestDeviceName:
    def test_defecto(self):
        assert audio.device_name(None) == "Realtek ALC"

    def test_entero_y_nombre(self):
        assert audio.device_name(2) == "USB Mic"
        assert audio.device_name("usb") == "USB Mic"

    def test_inexistente(self):
        assert audio.device_name(99) is None
        assert audio.device_name("nada") is None


class TestInputDeviceByName:
    def test_exacto(self):
        assert audio.input_device_by_name("USB Mic") == 2

    def test_parcial_no_vale(self):
        assert audio.input_device_by_name("USB") is None

    def test_salida_no_vale(self):
        assert audio.input_device_by_name("HDA Intel: salida") is None


class TestNextInputDevice:
    def test_siguiente(self):
        assert audio.next_input_device(1) == 2

    def test_vuelta_al_principio(self):
        assert audio.next_input_device(2) == 1

    def test_desde_defecto(self):
        assert audio.next_input_device(None) == 2

    def test_dispositivo_ausente_empieza_por_el_primero(self):
        assert audio.next_input_device(99) == 1
        assert audio.next_input_device("nada") == 1

    def test_sin_dispositivos(self, sounddevice_falso):
        sounddevice_falso.dispositivos.clear()
        assert audio.next_input_device(1) is None

    def test_un_solo_dispositivo(self, sounddevice_falso):
        del sounddevice_falso.dispositivos[2]
        assert audio.next_input_device(1) == 1


class TestResample:
    def test_misma_tasa_devuelve_el_mismo_array(self):
        datos = np.arange(10, dtype=np.int16)
        assert audio.resample(datos, SAMPLE_RATE) is datos

    def test_tasa_distinta(self):
        datos = np.zeros((48000, 1), dtype=np.int16)
        salida = audio.resample(datos, 48000)
        assert salida.dtype == np.int16
        assert salida.shape == (SAMPLE_RATE, 1)

    def test_satura_sin_desbordar(self):
        datos = np.full((4800, 1), 32767, dtype=np.int16)
        salida = audio.resample(datos, 48000)
        assert salida.max() <= 32767 and salida.min() >= -32768


class TestMeasure:
    def test_vacio(self):
        assert audio.measure(np.zeros(0, dtype=np.int16)) == (0.0, 0.0, 0.0)

    def test_duracion_pico_y_rms(self):
        datos = np.full(SAMPLE_RATE, 16384, dtype=np.int16)
        duracion, pico, rms = audio.measure(datos)
        assert duracion == pytest.approx(1.0)
        assert pico == pytest.approx(0.5) and rms == pytest.approx(0.5)


def test_save_wav_crea_carpeta_y_formato(tmp_path):
    ruta = tmp_path / "sub" / "a.wav"
    datos = np.arange(100, dtype=np.int16)
    audio.save_wav(ruta, datos)
    with wave.open(str(ruta)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()) == (1, 2, SAMPLE_RATE, 100)
        assert wav.readframes(100) == datos.tobytes()


class TestRecorder:
    def test_no_activo_al_inicio(self):
        assert not Recorder().active

    def test_start_abre_stream_a_tasa_nativa(self):
        grabador = Recorder(2)
        grabador.start()
        (stream,) = InputStreamFalso.instancias
        assert grabador.active and stream.active
        assert stream.kwargs["samplerate"] == 48000 and stream.kwargs["device"] == 2
        assert stream.kwargs["channels"] == 1 and stream.kwargs["dtype"] == "int16"

    def test_stop_devuelve_audio_remuestreado(self):
        grabador = Recorder()
        grabador.start()
        (stream,) = InputStreamFalso.instancias
        stream.alimentar(np.zeros((24000, 1), dtype=np.int16))
        stream.alimentar(np.zeros((24000, 1), dtype=np.int16))
        resultado = grabador.stop()
        assert resultado.shape == (SAMPLE_RATE, 1)
        assert stream.cerrado and not grabador.active

    def test_stop_sin_start_devuelve_vacio(self):
        assert Recorder().stop().shape == (0, 1)

    def test_stop_sin_datos_devuelve_vacio(self):
        grabador = Recorder()
        grabador.start()
        assert len(grabador.stop()) == 0

    def test_stop_tolera_stream_caido(self):
        grabador = Recorder()
        grabador.start()
        (stream,) = InputStreamFalso.instancias
        stream.falla_al_parar = True
        stream.alimentar(np.zeros((480, 1), dtype=np.int16))
        assert len(grabador.stop()) == 160
        assert not grabador.active

    def test_start_reinicia_acumulado(self):
        grabador = Recorder()
        grabador.start()
        InputStreamFalso.instancias[0].alimentar(np.ones((480, 1), dtype=np.int16))
        grabador.start()
        assert len(grabador.stop()) == 0

    def test_status_se_imprime_en_stderr(self, capsys):
        grabador = Recorder()
        grabador.start()
        InputStreamFalso.instancias[0].alimentar(np.zeros((10, 1), dtype=np.int16), status="overflow")
        assert "overflow" in capsys.readouterr().err

    def test_active_false_si_el_stream_se_para(self):
        grabador = Recorder()
        grabador.start()
        InputStreamFalso.instancias[0].active = False
        assert not grabador.active

    def test_start_con_dispositivo_inexistente_lanza(self):
        with pytest.raises(sd.PortAudioError):
            Recorder(99).start()
