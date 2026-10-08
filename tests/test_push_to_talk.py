"""Tests de PushToTalk con dobles de Recorder, Transcriber, notify e insert_text."""
import pytest
import sounddevice as sd
from pynput import keyboard

from speechflow.app import State

from conftest import TranscriberFalso, esperar

R = keyboard.KeyCode.from_char("r")  # tecla de dictado
F = keyboard.KeyCode.from_char("f")  # tecla de cambio de entrada
OTRA = keyboard.KeyCode.from_char("x")


def mensajes(caplog, nivel=None):
    return [r.getMessage() for r in caplog.records if nivel is None or r.levelname == nivel]


def esperar_idle(ptt):
    esperar(lambda: ptt.state is State.IDLE)


class TestDictation:
    def test_pulsar_y_soltar_inserta_el_texto(self, crear_ptt, dobles, caplog):
        """Pulsar graba, soltar transcribe e inserta el texto."""
        ptt = crear_ptt()
        ptt.on_press(R)
        assert ptt.state is State.RECORDING and ptt.recorder.inicios == 1
        ptt.on_release(R)
        esperar_idle(ptt)
        assert dobles.textos == ["hola mundo"]
        log = mensajes(caplog)
        assert "Grabando..." in log
        assert "Grabación terminada: 1.00 s. Transcribiendo con medium/es..." in log
        assert any(m.startswith("Insertado (0.10 s, 0.10x tiempo real, 10 caracteres, medium/es): hola mundo") for m in log)

    def test_repeticion_automatica_de_la_tecla(self, crear_ptt):
        """Las repeticiones de la tecla mantenida no reinician la grabación."""
        ptt = crear_ptt()
        ptt.on_press(R)
        ptt.on_press(R)
        ptt.on_press(R)
        assert ptt.recorder.inicios == 1
        ptt.on_release(R)
        esperar_idle(ptt)
        ptt.on_press(R)  # tras soltar se puede volver a grabar
        assert ptt.recorder.inicios == 2

    def test_otras_teclas_se_ignoran(self, crear_ptt):
        ptt = crear_ptt()
        ptt.on_press(OTRA)
        ptt.on_release(OTRA)
        assert ptt.state is State.IDLE and ptt.recorder.inicios == 0

    def test_descarta_grabacion_corta(self, crear_ptt, dobles, caplog):
        """Una grabación menor que min_seconds no se transcribe ni se escribe."""
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        ptt.recorder.segundos = 0.05
        ptt.on_press(R)
        ptt.on_release(R)
        assert ptt.state is State.IDLE
        assert "Grabación de 0.05 s descartada (mínimo 0.1 s)." in mensajes(caplog)
        assert transcriber.llamadas == 0 and dobles.textos == []

    def test_corta_por_max_seconds(self, crear_ptt, dobles, caplog):
        """Al vencer max_seconds la grabación se detiene sola y se transcribe."""
        ptt = crear_ptt(max_seconds=0.05)
        ptt.on_press(R)
        assert dobles.insertado.wait(2)
        assert ptt.recorder.paradas == 1
        assert "Límite de 0.05 s alcanzado; suelta la tecla y vuelve a pulsarla para otro dictado." in mensajes(caplog, "WARNING")
        esperar_idle(ptt)
        ptt.on_release(R)  # soltar después del corte no hace nada
        assert ptt.recorder.paradas == 1 and dobles.textos == ["hola mundo"]

    def test_soltar_cancela_el_temporizador_de_corte(self, crear_ptt, caplog):
        ptt = crear_ptt(max_seconds=0.2)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert ptt._timer is None
        assert not any("Límite" in m for m in mensajes(caplog))

    def test_texto_vacio_no_inserta(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto=""))
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert dobles.textos == []
        assert "Sin texto reconocido (0.10 s, medium/es)." in mensajes(caplog)

    def test_error_del_modelo(self, crear_ptt, dobles, caplog):
        """Un fallo al transcribir se registra, se notifica y deja el estado en IDLE."""
        transcriber = TranscriberFalso()
        transcriber.error = RuntimeError("boom")
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert "Error: boom" in mensajes(caplog, "ERROR")
        assert ("SpeechFlow", "Error: boom") in dobles.notificaciones
        assert dobles.textos == []

    def test_error_al_insertar(self, crear_ptt, dobles, caplog):
        dobles.error_insercion = OSError("xdotool falló")
        ptt = crear_ptt()
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert "Error: xdotool falló" in mensajes(caplog, "ERROR")

    @pytest.mark.parametrize("error", [sd.PortAudioError("sin acceso"), ValueError("sin acceso")])
    def test_error_al_abrir_el_microfono(self, crear_ptt, dobles, caplog, error):
        """Si el micrófono no se abre no se entra en RECORDING y se avisa."""
        ptt = crear_ptt()
        ptt.recorder.error_al_iniciar = error
        ptt.on_press(R)
        assert ptt.state is State.IDLE
        assert "Error al abrir el micrófono: sin acceso" in mensajes(caplog, "ERROR")
        assert ("SpeechFlow", "Error al abrir el micrófono: sin acceso") in dobles.notificaciones
        assert ptt._timer is None

    def test_microfono_desconectado_al_pulsar(self, crear_ptt, caplog):
        """Con el micrófono marcado como ausente, pulsar avisa y no graba."""
        ptt = crear_ptt(device="USB Mic")
        ptt._device_missing = True
        ptt.on_press(R)
        assert ptt.state is State.IDLE and ptt.recorder.inicios == 0
        assert (
            "El micrófono seleccionado no está conectado (USB Mic); "
            "reconéctalo o pulsa la tecla de cambio para elegir otro." in mensajes(caplog, "WARNING")
        )

    def test_no_se_graba_durante_la_transcripcion(self, crear_ptt):
        """Pulsar mientras se transcribe no inicia otra grabación."""
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        ptt.on_press(R)
        assert ptt.state is State.TRANSCRIBING and ptt.recorder.inicios == 1
        transcriber.liberar.set()
        esperar_idle(ptt)
