"""Tests de PushToTalk con dobles de Recorder, Transcriber, notify e insert_text."""
import threading
import time
from datetime import datetime
from types import SimpleNamespace

import pytest
import sounddevice as sd
from pynput import keyboard

from speechflow import app, config
from speechflow.app import State
from speechflow.replacements import compile_rules

from conftest import TranscriberFalso, dispositivo, esperar

R = keyboard.KeyCode.from_char("r")  # tecla de dictado
F = keyboard.KeyCode.from_char("f")  # tecla de cambio de entrada
OTRA = keyboard.KeyCode.from_char("x")
L = keyboard.KeyCode.from_char("l")  # tecla de idioma
A = keyboard.KeyCode.from_char("a")  # tecla de modo automático


def mensajes(caplog, nivel=None):
    return [r.getMessage() for r in caplog.records if nivel is None or r.levelname == nivel]


def esperar_idle(ptt):
    esperar(lambda: ptt.state is State.IDLE)


class TestIdioma:
    def test_pasa_el_idioma_vigente_a_transcribe(self, crear_ptt, dobles, caplog):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        ptt.language = "en"
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        esperar_idle(ptt)
        assert transcriber.idiomas == ["en"]
        log = mensajes(caplog)
        assert "Grabación terminada: 1.00 s. Transcribiendo con medium/en..." in log
        assert any("caracteres, medium/en):" in m for m in log)

    @pytest.mark.parametrize("detectado", ["es", "en"])
    def test_en_auto_el_log_muestra_el_idioma_detectado(self, crear_ptt, dobles, caplog, detectado):
        transcriber = TranscriberFalso(detectado=detectado)
        ptt = crear_ptt(transcriber=transcriber, language="auto")
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        esperar_idle(ptt)
        assert transcriber.idiomas == ["auto"]
        assert "Transcribiendo con medium/auto..." in " ".join(mensajes(caplog))
        assert any(f"caracteres, medium/auto→{detectado}):" in m for m in mensajes(caplog))

    def test_en_auto_sin_texto_muestra_el_idioma_detectado(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="", detectado="en"), language="auto")
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert "Sin texto reconocido (0.10 s, medium/auto→en)." in mensajes(caplog)


class TestCambioDeIdioma:
    def test_rota_es_en_es(self, crear_ptt, dobles, caplog):
        """f7 alterna es <-> en, registra el cambio, notifica y guarda."""
        ptt = crear_ptt(language="es")
        ptt.on_press(L)
        assert ptt.language == "en"
        assert "Idioma cambiado: en" in mensajes(caplog, "INFO")
        assert ("SpeechFlow", "Idioma: en") in dobles.notificaciones
        assert config.load_state_language() == "en"
        ptt.on_release(L)
        ptt.on_press(L)
        assert ptt.language == "es" and config.load_state_language() == "es"

    def test_otro_idioma_pasa_a_es(self, crear_ptt):
        ptt = crear_ptt(language="fr")
        ptt.on_press(L)
        assert ptt.language == "es"

    def test_auto_activa_y_vuelve_al_fijo(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(language="en")
        ptt.on_press(A)
        assert ptt.language == "auto" and config.load_state_language() == "auto"
        assert "Idioma cambiado: automático (es/en)" in mensajes(caplog, "INFO")
        assert ("SpeechFlow", "Idioma: automático (es/en)") in dobles.notificaciones
        ptt.on_release(A)
        ptt.on_press(A)
        assert ptt.language == "en" and config.load_state_language() == "en"

    def test_auto_recuerda_un_idioma_ajeno(self, crear_ptt):
        ptt = crear_ptt(language="fr")
        ptt.on_press(A)
        ptt.on_release(A)
        ptt.on_press(A)
        assert ptt.language == "fr"

    @pytest.mark.parametrize("fijo, esperado", [("es", "en"), ("en", "es"), ("fr", "es")])
    def test_tecla_de_idioma_desde_auto_fija_el_otro(self, crear_ptt, fijo, esperado):
        ptt = crear_ptt(language=fijo)
        ptt.on_press(A)
        ptt.on_release(A)
        ptt.on_press(L)
        assert ptt.language == esperado

    def test_arrancar_en_auto_recuerda_es(self, crear_ptt):
        ptt = crear_ptt(language="auto")
        ptt.on_press(A)
        assert ptt.language == "es"
        ptt.on_release(A)
        ptt.on_press(A)
        ptt.on_release(A)
        ptt.on_press(L)
        assert ptt.language == "en"

    def test_arrancar_en_auto_y_tecla_de_idioma_da_en(self, crear_ptt):
        ptt = crear_ptt(language="auto")
        ptt.on_press(L)
        assert ptt.language == "en"

    @pytest.mark.parametrize("tecla", [L, A])
    @pytest.mark.parametrize("estado", [State.RECORDING, State.TRANSCRIBING])
    def test_solo_cambia_en_idle(self, crear_ptt, dobles, caplog, tecla, estado):
        ptt = crear_ptt(language="es")
        ptt.state = estado
        ptt.on_press(tecla)
        assert ptt.language == "es"
        assert "No se cambia el idioma mientras se graba o se transcribe." in mensajes(caplog, "WARNING")
        assert dobles.notificaciones == [] and config.load_state_language() is None

    @pytest.mark.parametrize("tecla, esperado", [(L, "en"), (A, "auto")])
    def test_repeticion_de_tecla_se_ignora(self, crear_ptt, tecla, esperado):
        """Mantener pulsada la tecla cambia una sola vez."""
        ptt = crear_ptt(language="es")
        ptt.on_press(tecla)
        ptt.on_press(tecla)
        ptt.on_press(tecla)
        assert ptt.language == esperado

    def test_fallo_al_guardar_no_impide_el_cambio(self, crear_ptt, monkeypatch, caplog):
        def falla(language):
            raise OSError("disco lleno")

        monkeypatch.setattr(app, "save_state_language", falla)
        ptt = crear_ptt(language="es")
        ptt.on_press(L)
        assert ptt.language == "en"
        assert "No se pudo guardar el idioma en state.toml: disco lleno" in mensajes(caplog, "WARNING")

    def test_conserva_device_del_estado(self, crear_ptt):
        config.save_state_device("USB Mic")
        ptt = crear_ptt(language="es")
        ptt.on_press(L)
        assert config.load_state_device() == "USB Mic" and config.load_state_language() == "en"

    def test_cambio_de_micro_conserva_idioma(self, crear_ptt):
        ptt = crear_ptt(device=1, language="es")
        ptt.on_press(L)
        ptt.on_press(F)
        assert config.load_state_device() == "USB Mic" and config.load_state_language() == "en"

    def test_cambio_con_el_modelo_descargado(self, crear_ptt):
        ptt = crear_ptt(transcriber=None, language="es")
        ptt.on_press(L)
        assert ptt.language == "en" and ptt.transcriber is None

    def test_tras_cerrar_se_ignora(self, crear_ptt):
        ptt = crear_ptt(language="es")
        ptt.begin_shutdown()
        ptt.on_press(L)
        assert ptt.language == "es"

    def test_las_teclas_de_idioma_no_graban(self, crear_ptt):
        ptt = crear_ptt()
        ptt.on_press(L)
        ptt.on_press(A)
        assert ptt.state is State.IDLE and ptt.recorder.inicios == 0


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


class TestPuntuacionPorVoz:
    def dictar(self, ptt, dobles):
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        esperar_idle(ptt)

    def test_inserta_el_texto_procesado(self, crear_ptt, dobles):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hola coma mundo punto"), punctuation_commands=True)
        self.dictar(ptt, dobles)
        assert dobles.textos == ["Hola, mundo."]

    def test_con_la_clave_apagada_inserta_el_texto_intacto(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hola coma mundo punto"), punctuation_commands=False)
        self.dictar(ptt, dobles)
        assert dobles.textos == ["hola coma mundo punto"]
        assert not any(m.startswith("Texto original") for m in mensajes(caplog))

    def test_por_defecto_esta_apagada(self, crear_ptt):
        assert crear_ptt().punctuation_commands is False

    def test_en_auto_usa_el_idioma_detectado(self, crear_ptt, dobles):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hello comma world period", detectado="en"), language="auto", punctuation_commands=True)
        self.dictar(ptt, dobles)
        assert dobles.textos == ["Hello, world."]

    def test_idioma_sin_vocabulario_no_se_toca(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="bonjour point", detectado="fr"), language="auto", punctuation_commands=True)
        self.dictar(ptt, dobles)
        assert dobles.textos == ["bonjour point"]
        assert not any(m.startswith("Texto original") for m in mensajes(caplog))

    def test_log_muestra_el_original_antes_de_insertado(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hola punto"), punctuation_commands=True)
        self.dictar(ptt, dobles)
        log = mensajes(caplog)
        original = log.index("Texto original: hola punto")
        assert log[original + 1].startswith("Insertado (") and log[original + 1].endswith("): Hola.")
        assert "5 caracteres" in log[original + 1]

    def test_sin_cambios_no_hay_linea_de_texto_original(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="Hola mundo"), punctuation_commands=True)
        self.dictar(ptt, dobles)
        assert dobles.textos == ["Hola mundo"]
        assert not any(m.startswith("Texto original") for m in mensajes(caplog))

    def test_sin_texto_no_se_procesa(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto=""), punctuation_commands=True)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert dobles.textos == []
        assert "Sin texto reconocido (0.10 s, medium/es)." in mensajes(caplog)


class TestReemplazos:
    def reglas(self, plano=(), por_idioma=None):
        """Compila como main(): (dict idioma -> reglas, reglas planas)."""
        return {l: compile_rules(p) for l, p in (por_idioma or {}).items()}, compile_rules(plano)

    def dictar(self, ptt):
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)

    def test_se_aplican_tras_la_puntuacion(self, crear_ptt, dobles):
        reglas = self.reglas([("^hola,", "Hello,")])  # solo casa si la puntuación ya se aplicó
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hola coma mundo punto"), punctuation_commands=True, replacements=reglas)
        self.dictar(ptt)
        assert dobles.textos == ["Hello, mundo."]

    def test_subtabla_del_idioma_antes_que_la_plana(self, crear_ptt, dobles):
        reglas = self.reglas([("b", "c")], {"es": [("a", "b")], "en": [("a", "z")]})
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="a"), replacements=reglas)
        self.dictar(ptt)
        assert dobles.textos == ["c"]  # a -> b (es) -> c (plana); la de en no se aplica

    def test_en_auto_usa_el_idioma_detectado(self, crear_ptt, dobles):
        reglas = self.reglas([], {"es": [("a", "ES")], "en": [("a", "EN")]})
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="a", detectado="en"), language="auto", replacements=reglas)
        self.dictar(ptt)
        assert dobles.textos == ["EN"]

    def test_idioma_sin_subtabla_solo_aplica_la_plana(self, crear_ptt, dobles):
        reglas = self.reglas([("a", "P")], {"en": [("a", "EN")]})
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="a"), replacements=reglas)
        self.dictar(ptt)
        assert dobles.textos == ["P"]

    def test_historial_guarda_final_y_original(self, crear_ptt, dobles, caplog):
        history = HistoryFalso()
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="sube a git hub"), history=history, replacements=self.reglas([("git ?hub", "GitHub")]))
        self.dictar(ptt)
        assert (history.entradas[0]["text"], history.entradas[0]["original"]) == ("sube a GitHub", "sube a git hub")
        assert "Texto original: sube a git hub" in mensajes(caplog)

    def test_sin_reglas_nada_cambia(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="sube a git hub"))
        self.dictar(ptt)
        assert dobles.textos == ["sube a git hub"]
        assert not any(m.startswith("Texto original") for m in mensajes(caplog))

    def test_texto_vacio_tras_reemplazar_no_inserta_ni_guarda(self, crear_ptt, dobles, caplog):
        history = HistoryFalso()
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="eh eh"), history=history, replacements=self.reglas([("eh+", "")]))
        self.dictar(ptt)
        assert dobles.textos == [] and history.entradas == []
        assert "Sin texto tras los reemplazos (0.10 s, medium/es)." in mensajes(caplog)
        assert not any(m.startswith("Insertado") for m in mensajes(caplog))


class TestModoToggle:
    def test_primera_pulsacion_graba_y_soltar_no_para(self, crear_ptt, caplog):
        ptt = crear_ptt(mode="toggle")
        ptt.on_press(R)
        assert ptt.state is State.RECORDING and ptt.recorder.inicios == 1
        ptt.on_release(R)
        assert ptt.state is State.RECORDING and ptt.recorder.paradas == 0
        assert "Grabando..." in mensajes(caplog)

    def test_segunda_pulsacion_para_y_transcribe(self, crear_ptt, dobles, caplog):
        ptt = crear_ptt(mode="toggle")
        ptt.on_press(R)
        ptt.on_release(R)
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        esperar_idle(ptt)
        assert ptt.recorder.paradas == 1 and dobles.textos == ["hola mundo"]
        assert "Grabación terminada: 1.00 s. Transcribiendo con medium/es..." in mensajes(caplog)

    def test_repeticion_de_tecla_se_ignora(self, crear_ptt):
        """Mantener la tecla pulsada es un solo cambio de estado."""
        ptt = crear_ptt(mode="toggle")
        ptt.on_press(R)
        ptt.on_press(R)
        ptt.on_press(R)
        assert ptt.state is State.RECORDING and ptt.recorder.inicios == 1 and ptt.recorder.paradas == 0
        ptt.on_release(R)
        ptt.on_press(R)
        ptt.on_press(R)
        assert ptt.recorder.paradas == 1

    def test_pulsar_transcribiendo_da_warning(self, crear_ptt, caplog):
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber, mode="toggle")
        ptt.on_press(R)
        ptt.on_release(R)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        ptt.on_press(R)
        assert ptt.state is State.TRANSCRIBING and ptt.recorder.inicios == 1
        assert any("transcribiendo" in m for m in mensajes(caplog, "WARNING"))
        ptt.on_release(R)
        transcriber.liberar.set()
        esperar_idle(ptt)

    def test_grabacion_corta_se_descarta(self, crear_ptt, dobles, caplog):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, mode="toggle")
        ptt.recorder.segundos = 0.05
        ptt.on_press(R)
        ptt.on_release(R)
        ptt.on_press(R)
        ptt.on_release(R)
        assert ptt.state is State.IDLE
        assert "Grabación de 0.05 s descartada (mínimo 0.1 s)." in mensajes(caplog)
        assert transcriber.llamadas == 0 and dobles.textos == []

    def test_corte_por_max_seconds_y_pulsacion_posterior(self, crear_ptt, dobles, caplog):
        """Tras el corte automático, la pulsación siguiente empieza un dictado nuevo sin romper el estado."""
        ptt = crear_ptt(max_seconds=0.05, mode="toggle")
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert "Límite de 0.05 s alcanzado; pulsa la tecla para otro dictado." in mensajes(caplog, "WARNING")
        esperar_idle(ptt)
        assert ptt.recorder.paradas == 1
        ptt.on_press(R)
        assert ptt.state is State.RECORDING and ptt.recorder.inicios == 2
        ptt.on_release(R)

    def test_microfono_desconectado_no_graba(self, crear_ptt, caplog):
        ptt = crear_ptt(device="USB Mic", mode="toggle")
        ptt._device_missing = True
        ptt.on_press(R)
        assert ptt.state is State.IDLE and ptt.recorder.inicios == 0
        assert any("no está conectado" in m for m in mensajes(caplog, "WARNING"))

    @pytest.mark.parametrize("tecla", [F, L, A])
    def test_teclas_de_cambio_rechazadas_grabando(self, crear_ptt, caplog, tecla):
        ptt = crear_ptt(mode="toggle")
        ptt.on_press(R)
        ptt.on_release(R)
        ptt.on_press(tecla)
        assert ptt.state is State.RECORDING
        assert mensajes(caplog, "WARNING")

    def test_hold_sin_cambios(self, crear_ptt, dobles):
        ptt = crear_ptt(mode="hold")
        ptt.on_press(R)
        ptt.on_release(R)
        assert ptt.recorder.paradas == 1
        assert dobles.insertado.wait(2)
        esperar_idle(ptt)


DESCRIPCION_REALTEK = "[1] Realtek ALC | 48000 Hz nativos a 16000 Hz mono"
DESCRIPCION_USB = "[2] USB Mic | 48000 Hz nativos a 16000 Hz mono"


class TestSwitchAndWatch:
    def test_cambia_al_siguiente_dispositivo(self, crear_ptt, dobles, caplog):
        """En IDLE la tecla de cambio pasa al siguiente micrófono, lo notifica y lo guarda en state.toml."""
        ptt = crear_ptt(device=1)
        ptt.on_press(F)
        assert ptt.recorder.device == 2
        assert f"Entrada de audio cambiada: {DESCRIPCION_USB}" in mensajes(caplog)
        assert ("SpeechFlow", "Entrada de audio: USB Mic") in dobles.notificaciones
        assert ptt._watched_name == "USB Mic"
        assert config.load_state_device() == "USB Mic"

    def test_da_la_vuelta_al_principio(self, crear_ptt):
        ptt = crear_ptt(device=2)
        ptt.on_press(F)
        assert ptt.recorder.device == 1

    def test_repeticion_de_la_tecla_de_cambio(self, crear_ptt):
        """Mantener la tecla no encadena cambios; soltar y pulsar otra vez sí."""
        ptt = crear_ptt(device=1)
        ptt.on_press(F)
        ptt.on_press(F)
        assert ptt.recorder.device == 2
        ptt.on_release(F)
        ptt.on_press(F)
        assert ptt.recorder.device == 1

    @pytest.mark.parametrize("estado", [State.RECORDING, State.TRANSCRIBING])
    def test_solo_cambia_en_idle(self, crear_ptt, caplog, estado):
        ptt = crear_ptt(device=1)
        ptt.state = estado
        ptt.switch_device()
        assert ptt.recorder.device == 1
        assert "No se cambia la entrada de audio mientras se graba o se transcribe." in mensajes(caplog, "WARNING")

    def test_un_unico_dispositivo(self, crear_ptt, sounddevice_falso, caplog):
        del sounddevice_falso.dispositivos[2]
        ptt = crear_ptt(device=1)
        ptt.switch_device()
        assert ptt.recorder.device == 1
        assert f"Solo hay un dispositivo de entrada: {DESCRIPCION_REALTEK}" in mensajes(caplog)
        assert config.load_state_device() is None

    def test_un_unico_dispositivo_ausente_lo_recupera(self, crear_ptt, sounddevice_falso):
        """Si el único micrófono estaba marcado como ausente, el cambio lo vuelve a seleccionar."""
        del sounddevice_falso.dispositivos[2]
        ptt = crear_ptt(device=1)
        ptt._device_missing = True
        ptt.switch_device()
        assert ptt._device_missing is False

    def test_sin_dispositivos_de_entrada(self, crear_ptt, sounddevice_falso, caplog):
        sounddevice_falso.dispositivos.clear()
        ptt = crear_ptt(device=1)
        ptt.switch_device()
        assert "No hay dispositivos de entrada disponibles; se mantiene 1." in mensajes(caplog, "ERROR")
        assert ptt.recorder.device == 1

    def test_error_al_releer_los_dispositivos(self, crear_ptt, monkeypatch, caplog):
        def falla():
            raise RuntimeError("PortAudio roto")

        monkeypatch.setattr(app, "refresh_devices", falla)
        ptt = crear_ptt(device=1)
        ptt.switch_device()
        assert (
            f"Error al releer los dispositivos de audio: PortAudio roto; se mantiene {DESCRIPCION_REALTEK}."
            in mensajes(caplog, "ERROR")
        )
        assert ptt.recorder.device == 1

    def test_fallo_al_guardar_el_estado(self, crear_ptt, monkeypatch, caplog):
        def falla(nombre):
            raise OSError("disco lleno")

        monkeypatch.setattr(app, "save_state_device", falla)
        ptt = crear_ptt(device=1)
        ptt.switch_device()
        assert ptt.recorder.device == 2  # el cambio se mantiene
        assert "No se pudo guardar la entrada de audio en state.toml: disco lleno" in mensajes(caplog, "WARNING")

    def test_tras_begin_shutdown_no_cambia(self, crear_ptt):
        ptt = crear_ptt(device=1)
        ptt.begin_shutdown()
        ptt.switch_device()
        assert ptt.recorder.device == 1

    # --- vigilante ---

    def test_avisa_una_sola_vez_de_la_desconexion(self, crear_ptt, dobles, sounddevice_falso, caplog):
        ptt = crear_ptt(device=2)
        del sounddevice_falso.dispositivos[2]
        ptt.start_watcher(0.01)
        esperar(lambda: "El micrófono seleccionado se desconectó: USB Mic." in mensajes(caplog, "WARNING"))
        time.sleep(0.1)  # varias vueltas más del vigilante
        assert mensajes(caplog, "WARNING").count("El micrófono seleccionado se desconectó: USB Mic.") == 1
        assert dobles.notificaciones == [("SpeechFlow", "Micrófono desconectado: USB Mic")]
        assert ptt._device_missing is True

    def test_avisa_de_la_reconexion_y_actualiza_el_indice(self, crear_ptt, dobles, sounddevice_falso, caplog):
        """Al volver, el micrófono puede tener otro índice: el grabador lo adopta."""
        ptt = crear_ptt(device=2)
        usb = sounddevice_falso.dispositivos.pop(2)
        ptt.start_watcher(0.01)
        esperar(lambda: ptt._device_missing)
        sounddevice_falso.dispositivos.extend([dispositivo("Otro"), usb])
        esperar(lambda: not ptt._device_missing)
        assert ptt.recorder.device == 3
        assert "Micrófono reconectado: [3] USB Mic | 48000 Hz nativos a 16000 Hz mono" in mensajes(caplog, "INFO")
        assert dobles.notificaciones[-1] == ("SpeechFlow", "Micrófono reconectado: USB Mic")

    def test_no_avisa_si_sigue_conectado(self, crear_ptt, dobles, sounddevice_falso):
        ptt = crear_ptt(device=2)
        ptt.start_watcher(0.01)
        esperar(lambda: sounddevice_falso.reinicios >= 3)
        assert dobles.notificaciones == [] and ptt._device_missing is False

    def test_perdida_durante_la_grabacion(self, crear_ptt, dobles, caplog):
        """Si el stream cae grabando, se avisa y se transcribe lo capturado."""
        ptt = crear_ptt(device=2)
        ptt.on_press(R)
        ptt.recorder.caer()
        ptt.start_watcher(0.01)
        assert dobles.insertado.wait(2)
        assert "El micrófono seleccionado se desconectó durante la grabación: USB Mic." in mensajes(caplog, "WARNING")
        assert ("SpeechFlow", "Micrófono desconectado: USB Mic") in dobles.notificaciones
        assert ptt._device_missing is True and ptt.recorder.paradas == 1
        assert dobles.textos == ["hola mundo"]

    def test_no_refresca_portaudio_mientras_graba(self, crear_ptt, sounddevice_falso):
        """Con un stream abierto y activo el vigilante no reinicia PortAudio."""
        ptt = crear_ptt(device=2)
        ptt.on_press(R)
        ptt.start_watcher(0.01)
        time.sleep(0.1)
        assert sounddevice_falso.reinicios == 0 and ptt.state is State.RECORDING

    def test_no_vigila_sin_nombre_de_dispositivo(self, crear_ptt, sounddevice_falso):
        ptt = crear_ptt(device=99)  # no se resuelve: no hay nombre que vigilar
        ptt.start_watcher(0.01)
        time.sleep(0.1)
        assert sounddevice_falso.reinicios == 0

    def test_error_al_refrescar_se_registra_una_vez(self, crear_ptt, monkeypatch, caplog):
        llamadas = []

        def falla():
            llamadas.append(1)
            raise RuntimeError("PortAudio roto")

        monkeypatch.setattr(app, "refresh_devices", falla)
        ptt = crear_ptt(device=2)
        ptt.start_watcher(0.01)
        esperar(lambda: len(llamadas) >= 4)
        assert mensajes(caplog, "ERROR").count("Error al comprobar el micrófono: PortAudio roto") == 1

    def test_stop_watcher_detiene_las_comprobaciones(self, crear_ptt, sounddevice_falso):
        ptt = crear_ptt(device=2)
        ptt.start_watcher(0.01)
        esperar(lambda: sounddevice_falso.reinicios >= 1)
        ptt.stop_watcher()
        time.sleep(0.05)  # deja terminar una vuelta en curso
        antes = sounddevice_falso.reinicios
        time.sleep(0.1)
        assert sounddevice_falso.reinicios == antes


@pytest.fixture
def carga(monkeypatch):
    """Sustituye load_transcriber: bloquea en `puerta` y devuelve un TranscriberFalso o lanza `error`."""
    estado = SimpleNamespace(puerta=threading.Event(), llamadas=[], dispositivos=[], prompts=[], error=None, creados=[])

    def cargar(model, language, vad, device="auto", cpu_threads=0, initial_prompt=""):
        estado.llamadas.append((model, language, vad))
        estado.dispositivos.append((device, cpu_threads))
        estado.prompts.append(initial_prompt)
        estado.puerta.wait(2)
        if estado.error is not None:
            raise estado.error
        transcriber = TranscriberFalso()
        estado.creados.append(transcriber)
        return transcriber

    monkeypatch.setattr(app, "load_transcriber", cargar)
    yield estado
    estado.puerta.set()


class TestIdleAndReload:
    def test_idle_timeout_libera_el_modelo(self, crear_ptt, caplog):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0.05)
        esperar(lambda: ptt.transcriber is None)
        assert transcriber.cierres == 1
        assert "Modelo medium liberado por inactividad (0.05 s sin uso)." in mensajes(caplog, "INFO")

    def test_idle_timeout_cero_no_libera(self, crear_ptt):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0)
        assert ptt._idle_timer is None
        time.sleep(0.1)
        assert ptt.transcriber is transcriber and transcriber.cierres == 0

    def test_idle_timeout_cero_tras_dictar_no_libera(self, crear_ptt, dobles):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert ptt._idle_timer is None and ptt.transcriber is transcriber

    def test_grabando_no_se_libera_el_modelo(self, crear_ptt):
        """Pulsar cancela la cuenta de inactividad."""
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0.05)
        ptt.on_press(R)
        time.sleep(0.15)  # tres veces el idle_timeout
        assert ptt.transcriber is transcriber and transcriber.cierres == 0

    def test_tras_dictar_se_rearma_la_cuenta(self, crear_ptt, dobles):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0.05)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar(lambda: ptt.transcriber is None)
        assert transcriber.cierres == 1 and dobles.textos == ["hola mundo"]

    def test_grabacion_descartada_rearma_la_cuenta(self, crear_ptt):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0.05)
        ptt.recorder.segundos = 0.01
        ptt.on_press(R)
        ptt.on_release(R)
        esperar(lambda: ptt.transcriber is None)
        assert transcriber.cierres == 1

    def test_pulsar_con_el_modelo_descargado_recarga_en_paralelo(self, crear_ptt, carga, dobles, caplog):
        """Se graba al instante mientras el modelo se recarga; al soltar se espera a la carga."""
        ptt = crear_ptt(transcriber=None)
        ptt.on_press(R)
        assert ptt.state is State.RECORDING and ptt.recorder.inicios == 1
        assert ptt._loader.is_alive()
        assert "Modelo descargado: se carga medium mientras grabas." in mensajes(caplog)
        ptt.on_release(R)
        assert dobles.textos == []  # la carga sigue bloqueada
        carga.puerta.set()
        assert dobles.insertado.wait(2)
        assert dobles.textos == ["hola mundo"] and carga.llamadas == [("medium", "es", True)]
        esperar_idle(ptt)
        assert ptt.transcriber is carga.creados[0]

    def test_recarga_usa_el_idioma_vigente(self, crear_ptt, carga, dobles):
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None)
        ptt.language = "en"
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert carga.llamadas == [("medium", "en", True)]
        esperar_idle(ptt)

    def test_recarga_usa_el_dispositivo_resuelto(self, crear_ptt, carga, dobles):
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None, compute_device="cpu", cpu_threads=4)
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert carga.dispositivos == [("cpu", 4)]
        esperar_idle(ptt)

    def test_recarga_en_auto_pasa_auto(self, crear_ptt, carga, dobles):
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None, language="auto")
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert carga.llamadas == [("medium", "auto", True)]
        esperar_idle(ptt)

    def test_recarga_conserva_el_initial_prompt(self, crear_ptt, carga, dobles):
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None, initial_prompt="Hablo de Kubernetes.")
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert carga.prompts == ["Hablo de Kubernetes."]
        esperar_idle(ptt)

    def test_recarga_conserva_el_ajuste_vad(self, crear_ptt, carga, dobles):
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None, vad=False)
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert carga.llamadas == [("medium", "es", False)]
        esperar_idle(ptt)

    def test_fallo_de_recarga_descarta_el_audio(self, crear_ptt, carga, dobles, caplog):
        carga.error = RuntimeError("sin VRAM")
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        assert "Error al recargar el modelo: sin VRAM" in mensajes(caplog, "ERROR")
        assert ("SpeechFlow", "Error al recargar el modelo: sin VRAM") in dobles.notificaciones
        assert "Audio descartado: el modelo no se pudo recargar." in mensajes(caplog, "INFO")
        assert dobles.textos == [] and ptt.transcriber is None

    def test_tras_un_fallo_la_siguiente_pulsacion_reintenta(self, crear_ptt, carga, dobles):
        carga.error = RuntimeError("sin VRAM")
        carga.puerta.set()
        ptt = crear_ptt(transcriber=None)
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)
        carga.error = None
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert len(carga.llamadas) == 2 and dobles.textos == ["hola mundo"]

    def test_recarga_con_grabacion_descartada_rearma_la_cuenta(self, crear_ptt, carga):
        """Si la grabación corta se descarta mientras carga, el modelo recién publicado se libera por inactividad."""
        ptt = crear_ptt(transcriber=None, idle_timeout=0.05)
        ptt.recorder.segundos = 0.01
        ptt.on_press(R)
        ptt.on_release(R)
        assert ptt.state is State.IDLE
        carga.puerta.set()
        esperar(lambda: carga.creados and carga.creados[0].cierres == 1)
        assert ptt.transcriber is None


def liberar_en(evento, segundos=0.05):
    """Activa `evento` desde otro hilo tras `segundos`, para desbloquear un shutdown que espera."""
    temporizador = threading.Timer(segundos, evento.set)
    temporizador.daemon = True
    temporizador.start()


class TestShutdown:
    def test_begin_shutdown_descarta_la_grabacion(self, crear_ptt, dobles, caplog):
        """Una grabación en curso se detiene sin transcribir ni insertar nada."""
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.begin_shutdown()
        assert ptt.state is State.IDLE and ptt.recorder.paradas == 1 and ptt._timer is None
        assert "Grabación descartada por cierre." in mensajes(caplog)
        assert transcriber.llamadas == 0 and dobles.textos == []

    def test_begin_shutdown_en_reposo_no_descarta_nada(self, crear_ptt, caplog):
        ptt = crear_ptt()
        ptt.begin_shutdown()
        assert ptt.recorder.paradas == 0
        assert "Grabación descartada por cierre." not in mensajes(caplog)

    def test_begin_shutdown_ignora_las_teclas(self, crear_ptt):
        ptt = crear_ptt(device=1)
        ptt.begin_shutdown()
        ptt.on_press(R)
        ptt.on_release(R)
        ptt.on_press(F)
        ptt.on_release(F)
        assert ptt.recorder.inicios == 0 and ptt.state is State.IDLE
        assert ptt.recorder.device == 1

    def test_begin_shutdown_no_interrumpe_la_transcripcion(self, crear_ptt, dobles):
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        ptt.begin_shutdown()
        assert ptt.state is State.TRANSCRIBING
        transcriber.liberar.set()
        assert dobles.insertado.wait(2)
        esperar_idle(ptt)

    def test_begin_shutdown_cancela_la_cuenta_de_inactividad(self, crear_ptt):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0.05)
        ptt.begin_shutdown()
        time.sleep(0.15)
        assert ptt.transcriber is transcriber and transcriber.cierres == 0 and ptt._idle_timer is None

    def test_la_cuenta_no_se_rearma_tras_begin_shutdown(self, crear_ptt):
        """Al terminar una transcripción en curso durante el cierre no se vuelve a armar el temporizador."""
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=0.05)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        ptt.begin_shutdown()
        transcriber.liberar.set()
        esperar_idle(ptt)
        assert ptt._idle_timer is None

    def test_shutdown_libera_el_modelo(self, crear_ptt):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        assert ptt.shutdown(1) is True
        assert transcriber.cierres == 1 and ptt.transcriber is None

    def test_shutdown_repetido_no_cierra_dos_veces(self, crear_ptt):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        assert ptt.shutdown(1) is True
        assert ptt.shutdown(1) is False
        assert transcriber.cierres == 1

    def test_shutdown_cancela_la_cuenta_de_inactividad(self, crear_ptt):
        ptt = crear_ptt(idle_timeout=30.0)
        assert ptt._idle_timer is not None
        ptt.shutdown(1)
        assert ptt._idle_timer is None

    def test_shutdown_espera_a_la_transcripcion(self, crear_ptt, dobles, caplog):
        """Con una transcripción en curso, espera a que termine y después libera el modelo."""
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        ptt.begin_shutdown()
        liberar_en(transcriber.liberar)
        assert ptt.shutdown(2) is True
        assert dobles.textos == ["hola mundo"] and transcriber.cierres == 1
        assert "Esperando a la transcripción en curso (máximo 2 s)..." in mensajes(caplog)

    def test_shutdown_con_la_transcripcion_bloqueada_vence_el_tope(self, crear_ptt, dobles, caplog):
        """Si la transcripción no termina en el plazo: False, WARNING y sin llamar a close()."""
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        ptt.begin_shutdown()
        inicio = time.monotonic()
        assert ptt.shutdown(0.05) is False
        assert time.monotonic() - inicio < 1
        assert "La transcripción no terminó en 0.05 s; se sale sin liberar el modelo." in mensajes(caplog, "WARNING")
        assert transcriber.cierres == 0 and ptt.transcriber is transcriber
        transcriber.liberar.set()

    def test_shutdown_espera_a_la_recarga(self, crear_ptt, carga):
        """Una recarga en curso se espera, y el modelo recién publicado se libera."""
        ptt = crear_ptt(transcriber=None)
        ptt.on_press(R)
        ptt.begin_shutdown()
        assert ptt._loader.is_alive()
        liberar_en(carga.puerta)
        assert ptt.shutdown(2) is True
        assert len(carga.creados) == 1 and carga.creados[0].cierres == 1
        assert ptt.transcriber is None

    def test_shutdown_con_la_recarga_bloqueada_devuelve_false(self, crear_ptt, carga):
        ptt = crear_ptt(transcriber=None)
        ptt.on_press(R)
        ptt.begin_shutdown()
        assert ptt.shutdown(0.05) is False
        assert carga.creados == []

    def test_shutdown_con_el_modelo_ya_descargado(self, crear_ptt):
        """Sin modelo cargado no hay nada que cerrar: devuelve False sin error."""
        ptt = crear_ptt(transcriber=None)
        assert ptt.shutdown(1) is False
        assert ptt.transcriber is None


class TestInsercionConfigurada:
    def test_pasa_metodo_y_terminales_a_insert_text(self, crear_ptt, dobles):
        ptt = crear_ptt(insert_method="type", terminal_classes=("myterm",))
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert dobles.opciones == [("type", ("myterm",))]

    def test_defectos(self, crear_ptt, dobles):
        ptt = crear_ptt()
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)
        assert dobles.opciones == [("clipboard", ())]


class HistoryFalso:
    """Sustituye a History: guarda las entradas y puede fallar al escribir."""

    def __init__(self):
        self.entradas = []
        self.error = None
        self.eventos = None  # lista compartida con el doble de insert_text para comprobar el orden

    def add(self, entry):
        if self.error is not None:
            raise self.error
        self.entradas.append(entry)
        if self.eventos is not None:
            self.eventos.append("history")


class TestHistorial:
    def dictar(self, ptt):
        ptt.on_press(R)
        ptt.on_release(R)
        esperar_idle(ptt)

    def test_guarda_el_dictado_con_los_siete_campos(self, crear_ptt, dobles):
        history = HistoryFalso()
        ptt = crear_ptt(history=history)
        self.dictar(ptt)
        assert len(history.entradas) == 1
        e = history.entradas[0]
        assert set(e) == {"ts", "text", "original", "language", "model", "audio_seconds", "seconds"}
        assert (e["text"], e["original"], e["language"], e["model"]) == ("hola mundo", "hola mundo", "es", "medium")
        assert e["audio_seconds"] == 1.0 and e["seconds"] == 0.1
        assert datetime.fromisoformat(e["ts"]).utcoffset() is not None and e["ts"].count(".") == 1

    def test_text_con_puntuacion_y_original_de_whisper(self, crear_ptt):
        history = HistoryFalso()
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hola coma mundo punto"), punctuation_commands=True, history=history)
        self.dictar(ptt)
        assert (history.entradas[0]["text"], history.entradas[0]["original"]) == ("Hola, mundo.", "hola coma mundo punto")

    def test_sin_puntuacion_text_y_original_iguales(self, crear_ptt):
        history = HistoryFalso()
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hola coma mundo punto"), punctuation_commands=False, history=history)
        self.dictar(ptt)
        assert history.entradas[0]["text"] == history.entradas[0]["original"] == "hola coma mundo punto"

    def test_en_auto_guarda_el_idioma_detectado(self, crear_ptt):
        history = HistoryFalso()
        ptt = crear_ptt(transcriber=TranscriberFalso(texto="hello", detectado="en"), language="auto", history=history)
        self.dictar(ptt)
        assert history.entradas[0]["language"] == "en"

    def test_sin_texto_no_se_guarda(self, crear_ptt):
        history = HistoryFalso()
        ptt = crear_ptt(transcriber=TranscriberFalso(texto=""), history=history)
        self.dictar(ptt)
        assert history.entradas == []

    def test_audio_descartado_no_se_guarda(self, crear_ptt):
        history = HistoryFalso()
        ptt = crear_ptt(history=history)
        ptt.recorder.segundos = 0.05
        self.dictar(ptt)
        assert history.entradas == []

    def test_se_guarda_antes_de_insertar(self, crear_ptt, dobles):
        history = HistoryFalso()
        history.eventos = []
        original = dobles.opciones.append
        dobles.opciones = SimpleNamespace(append=lambda x: (history.eventos.append("insert"), original(x)))
        ptt = crear_ptt(history=history)
        self.dictar(ptt)
        assert history.eventos == ["history", "insert"]

    def test_se_guarda_aunque_insert_text_falle(self, crear_ptt, dobles, caplog):
        dobles.error_insercion = RuntimeError("xdotool falló")
        history = HistoryFalso()
        ptt = crear_ptt(history=history)
        self.dictar(ptt)
        assert len(history.entradas) == 1
        assert "Error: xdotool falló" in mensajes(caplog, "ERROR")

    def test_fallo_de_escritura_no_impide_la_insercion(self, crear_ptt, dobles, caplog):
        history = HistoryFalso()
        history.error = OSError("disco lleno")
        ptt = crear_ptt(history=history)
        self.dictar(ptt)
        assert dobles.textos == ["hola mundo"]
        assert mensajes(caplog, "WARNING") == ["No se pudo guardar el dictado en el historial: disco lleno"]

    def test_el_aviso_sale_una_sola_vez_y_se_rearma(self, crear_ptt, dobles, caplog):
        history = HistoryFalso()
        history.error = OSError("disco lleno")
        ptt = crear_ptt(history=history)
        self.dictar(ptt)
        self.dictar(ptt)
        assert len(mensajes(caplog, "WARNING")) == 1
        history.error = None  # una escritura correcta rearma el aviso
        self.dictar(ptt)
        assert len(history.entradas) == 1 and len(mensajes(caplog, "WARNING")) == 1
        history.error = OSError("otra vez")
        self.dictar(ptt)
        assert mensajes(caplog, "WARNING")[-1] == "No se pudo guardar el dictado en el historial: otra vez"
        assert len(mensajes(caplog, "WARNING")) == 2
        assert dobles.textos == ["hola mundo"] * 4

    def test_sin_historial_por_defecto(self, crear_ptt, dobles):
        ptt = crear_ptt()
        assert ptt.history is None
        self.dictar(ptt)
        assert dobles.textos == ["hola mundo"]


class TestPausaControl:
    def test_pause_libera_el_modelo_y_cancela_el_temporizador(self, crear_ptt, dobles, caplog):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber, idle_timeout=30.0)
        assert ptt._idle_timer is not None
        ptt.pause()
        assert ptt.paused and ptt.transcriber is None and transcriber.cierres == 1
        assert ptt._idle_timer is None
        assert ("SpeechFlow", "Dictado en pausa") in dobles.notificaciones
        assert any(m.startswith("Dictado en pausa") for m in mensajes(caplog, "INFO"))

    def test_pause_con_el_modelo_ya_descargado_solo_marca(self, crear_ptt):
        ptt = crear_ptt(transcriber=None)
        ptt.pause()
        assert ptt.paused and ptt.transcriber is None

    def test_pause_es_idempotente(self, crear_ptt, dobles):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        ptt.pause()
        ptt.pause()
        assert ptt.paused and transcriber.cierres == 1
        assert dobles.notificaciones.count(("SpeechFlow", "Dictado en pausa")) == 1

    def test_pause_grabando_se_rechaza_sin_alterar_la_grabacion(self, crear_ptt):
        transcriber = TranscriberFalso()
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        with pytest.raises(app.ControlError, match="^ocupado: grabando$"):
            ptt.pause()
        assert not ptt.paused and ptt.state is State.RECORDING and ptt.recorder.active
        assert transcriber.cierres == 0

    def test_pause_transcribiendo_se_rechaza(self, crear_ptt):
        transcriber = TranscriberFalso(bloquear=True)
        ptt = crear_ptt(transcriber=transcriber)
        ptt.on_press(R)
        ptt.on_release(R)
        assert transcriber.entro.wait(2)
        with pytest.raises(app.ControlError, match="^ocupado: transcribiendo$"):
            ptt.pause()
        assert not ptt.paused
        transcriber.liberar.set()
        esperar_idle(ptt)

    def test_pause_con_recarga_en_curso_se_rechaza(self, crear_ptt, carga):
        ptt = crear_ptt(transcriber=None)
        ptt.on_press(R)
        ptt.recorder.segundos = 0.01
        ptt.on_release(R)
        esperar_idle(ptt)
        assert ptt._loader.is_alive()
        with pytest.raises(app.ControlError, match="^ocupado: cargando el modelo$"):
            ptt.pause()
        assert not ptt.paused

    def test_pause_y_resume_en_cierre(self, crear_ptt):
        ptt = crear_ptt()
        ptt.begin_shutdown()
        with pytest.raises(app.ControlError, match="^cierre en curso$"):
            ptt.pause()
        with pytest.raises(app.ControlError, match="^cierre en curso$"):
            ptt.resume()

    def test_resume_lanza_la_recarga_sin_esperar(self, crear_ptt, carga, dobles, caplog):
        ptt = crear_ptt(transcriber=TranscriberFalso())
        ptt.pause()
        inicio = time.monotonic()
        ptt.resume()  # la carga sigue bloqueada en `puerta`
        assert time.monotonic() - inicio < 1
        assert not ptt.paused and ptt._loader.is_alive() and ptt.transcriber is None
        assert ("SpeechFlow", "Dictado reanudado") in dobles.notificaciones
        assert any(m.startswith("Dictado reanudado") for m in mensajes(caplog, "INFO"))
        carga.puerta.set()
        esperar(lambda: ptt.transcriber is carga.creados[0] if carga.creados else False)
        assert carga.llamadas == [("medium", "es", True)]

    def test_resume_es_idempotente(self, crear_ptt, carga):
        ptt = crear_ptt(transcriber=TranscriberFalso())
        ptt.resume()  # sin pausa previa: no hace nada
        assert carga.llamadas == [] and not ptt.paused
        ptt.pause()
        carga.puerta.set()
        ptt.resume()
        ptt.resume()
        esperar(lambda: ptt.transcriber is not None)
        assert len(carga.llamadas) == 1

    def test_resume_tras_fallo_de_recarga_deja_el_error_y_se_reintenta_al_pulsar(self, crear_ptt, carga, caplog):
        carga.puerta.set()
        carga.error = RuntimeError("sin VRAM")
        ptt = crear_ptt(transcriber=TranscriberFalso())
        ptt.pause()
        ptt.resume()
        esperar(lambda: "Error al recargar el modelo: sin VRAM" in mensajes(caplog, "ERROR"))
        assert ptt.transcriber is None and not ptt.paused
        carga.error = None
        ptt.on_press(R)
        assert ptt.state is State.RECORDING
        esperar(lambda: ptt.transcriber is not None)  # la pulsación reintentó la carga
        assert len(carga.llamadas) == 2
        ptt.on_release(R)
        esperar_idle(ptt)

    def test_en_pausa_la_tecla_no_graba_y_avisa(self, crear_ptt, caplog):
        ptt = crear_ptt()
        ptt.pause()
        ptt.on_press(R)
        ptt.on_release(R)
        assert ptt.state is State.IDLE and ptt.recorder.inicios == 0
        assert "Dictado en pausa; reanúdalo con: speechflow ctl resume." in mensajes(caplog, "WARNING")

    def test_en_pausa_con_modo_toggle_tampoco_graba(self, crear_ptt):
        ptt = crear_ptt(mode="toggle")
        ptt.pause()
        ptt.on_press(R)
        assert ptt.state is State.IDLE and ptt.recorder.inicios == 0

    def test_tras_resume_la_tecla_vuelve_a_grabar(self, crear_ptt, carga, dobles):
        carga.puerta.set()
        ptt = crear_ptt(transcriber=TranscriberFalso())
        ptt.pause()
        ptt.resume()
        esperar(lambda: ptt.transcriber is not None)
        ptt.on_press(R)
        ptt.on_release(R)
        assert dobles.insertado.wait(2)

    def test_en_pausa_siguen_activas_las_teclas_de_idioma_y_dispositivo(self, crear_ptt, sounddevice_falso):
        ptt = crear_ptt(language="es")
        ptt.pause()
        ptt.on_press(L)
        assert ptt.language == "en"
        ptt.on_press(A)
        assert ptt.language == "auto"
        antes = ptt.recorder.device
        ptt.on_press(F)
        assert ptt.recorder.device != antes
