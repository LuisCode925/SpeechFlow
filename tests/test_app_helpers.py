"""Tests de los helpers de speechflow.app: parse_key, describe_device, load_transcriber y resolve_config."""
import os
from pathlib import Path

import pytest
from pynput import keyboard

from speechflow import app, config
from speechflow.config import Config
from speechflow.transcriber import SAMPLE_RATE

sin_display = pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="con el backend dummy todas las teclas valen Key.alt")


class TestParseKey:
    @sin_display
    def test_nombre_de_tecla(self):
        assert app.parse_key("ctrl_r") == keyboard.Key.ctrl_r
        assert app.parse_key("f9") == keyboard.Key.f9

    @sin_display
    def test_teclas_distintas_no_son_iguales(self):
        assert app.parse_key("f8") != app.parse_key("ctrl_r")

    def test_caracter_suelto(self):
        assert app.parse_key("r") == keyboard.KeyCode.from_char("r")

    @sin_display
    def test_tecla_desconocida(self):
        with pytest.raises(ValueError, match="tecla desconocida 'nada'"):
            app.parse_key("nada")


class TestParseHotkeys:
    def test_cuatro_teclas_distintas(self):
        r, f8, f7, f6 = app.parse_hotkeys("ctrl_r", "f8", "f7", "f6")
        assert (r, f8, f7, f6) == (keyboard.Key.ctrl_r, keyboard.Key.f8, keyboard.Key.f7, keyboard.Key.f6)

    @pytest.mark.parametrize(
        "nombres, esperado",
        [
            (("a", "a", "f7", "f6"), "--key y --switch-key"),
            (("a", "f8", "a", "f6"), "--key y [keys] language"),
            (("a", "f8", "f7", "a"), "--key y [keys] auto"),
            (("ctrl_r", "f8", "f8", "f6"), "--switch-key y [keys] language"),
            (("ctrl_r", "f8", "f7", "f8"), "--switch-key y [keys] auto"),
            (("ctrl_r", "f8", "f7", "f7"), "[keys] language y [keys] auto"),
        ],
    )
    def test_teclas_repetidas_nombran_las_dos(self, nombres, esperado):
        with pytest.raises(ValueError, match="no pueden ser la misma tecla") as e:
            app.parse_hotkeys(*nombres)
        assert esperado in str(e.value)

    @pytest.mark.parametrize(
        "nombres, esperado",
        [
            (("nada", "f8", "f7", "f6"), "Error con --key"),
            (("ctrl_r", "nada", "f7", "f6"), "Error con --switch-key"),
            (("ctrl_r", "f8", "nada", "f6"), "Error con [keys] language: tecla desconocida 'nada'"),
            (("ctrl_r", "f8", "f7", "nada"), "Error con [keys] auto: tecla desconocida 'nada'"),
        ],
    )
    def test_tecla_desconocida_nombra_la_clave(self, nombres, esperado):
        with pytest.raises(ValueError, match="tecla desconocida") as e:
            app.parse_hotkeys(*nombres)
        assert esperado in str(e.value)


class TestResolveLanguage:
    def test_sin_nada_usa_el_de_config(self):
        assert app.resolve_language(None, "es") == "es"

    def test_estado_gana_sobre_config(self):
        config.save_state_language("auto")
        assert app.resolve_language(None, "es") == "auto"

    def test_cli_gana_sobre_estado_y_config(self):
        config.save_state_language("auto")
        assert app.resolve_language("en", "fr") == "en"

    def test_cli_auto(self):
        assert app.resolve_language("auto", "es") == "auto"

    def test_estado_invalido_se_ignora(self, caplog):
        config.state_path().parent.mkdir(parents=True)
        config.state_path().write_text("language = 3\n")
        with caplog.at_level("WARNING", logger="speechflow"):
            assert app.resolve_language(None, "fr") == "fr"
        assert "language debe ser texto" in caplog.text


class TestDescribeDevice:
    def test_defecto(self):
        assert app.describe_device(None) == f"[1] Realtek ALC | 48000 Hz nativos a {SAMPLE_RATE} Hz mono"

    def test_por_indice(self):
        assert app.describe_device(2).startswith("[2] USB Mic |")

    def test_por_nombre(self):
        assert app.describe_device("usb").startswith("[2] USB Mic |")

    def test_indice_no_resuelto(self, monkeypatch):
        monkeypatch.setattr(app, "device_index", lambda device: None)
        assert app.describe_device(2).startswith("[?] USB Mic |")


class TestLoadTranscriber:
    def test_registra_carga_y_devuelve_el_transcriber(self, monkeypatch, caplog):
        creados = []

        class TranscriberFalso:
            def __init__(self, model, language, vad, device, cpu_threads):
                creados.append((model, language, vad, device, cpu_threads))

        monkeypatch.setattr(app, "Transcriber", TranscriberFalso)
        with caplog.at_level("INFO", logger="speechflow"):
            resultado = app.load_transcriber("small", "en", False, "cuda", 0)
        assert isinstance(resultado, TranscriberFalso) and creados == [("small", "en", False, "cuda", 0)]
        mensajes = [r.getMessage() for r in caplog.records]
        assert mensajes[0] == "Cargando small (int8, GPU)..."
        assert mensajes[1].startswith("Modelo cargado en ") and mensajes[1].endswith(" s (incluye calentamiento)")

    def test_no_notifica(self, monkeypatch, subprocess_falso):
        monkeypatch.setattr(app, "Transcriber", lambda model, language, vad, device, cpu_threads: object())
        app.load_transcriber("small", "en")
        assert subprocess_falso == []

    @pytest.mark.parametrize("device, etiqueta", [("cpu", "CPU"), ("cuda", "GPU"), ("auto", "auto")])
    def test_registra_el_dispositivo(self, monkeypatch, caplog, device, etiqueta):
        monkeypatch.setattr(app, "Transcriber", lambda *args: object())
        with caplog.at_level("INFO", logger="speechflow"):
            app.load_transcriber("medium", "es", True, device)
        assert caplog.records[0].getMessage() == f"Cargando medium (int8, {etiqueta})..."

    @pytest.mark.parametrize("device, esperado", [("cpu", "small (int8, CPU)"), ("cuda", "medium (int8, GPU)"), ("auto", "el modelo por defecto (int8, auto)")])
    def test_sin_modelo_registra_el_defecto(self, monkeypatch, caplog, device, esperado):
        monkeypatch.setattr(app, "Transcriber", lambda *args: object())
        with caplog.at_level("INFO", logger="speechflow"):
            app.load_transcriber(None, "es", True, device)
        assert caplog.records[0].getMessage() == f"Cargando {esperado}..."

    def test_pasa_dispositivo_e_hilos_al_transcriber(self, monkeypatch):
        recibido = []
        monkeypatch.setattr(app, "Transcriber", lambda *args: recibido.append(args) or object())
        app.load_transcriber("small", "en", True, "cpu", 4)
        assert recibido == [("small", "en", True, "cpu", 4)]


class TestIsHeavyForCpu:
    @pytest.mark.parametrize("modelo", ["medium", "medium.en", "large-v3", "large-v3-turbo", "distil-large-v3"])
    def test_pesados(self, modelo):
        assert app.is_heavy_for_cpu(modelo)

    @pytest.mark.parametrize("modelo", ["tiny", "base", "small", "small.en"])
    def test_ligeros(self, modelo):
        assert not app.is_heavy_for_cpu(modelo)


EVENTOS_LOG = []  # setup_logging / resolve_config / apply_log_levels / log_banner, en orden de llamada


def ejecutar_main(monkeypatch, argumentos, transcriber=None, error=None, config=None):
    """Ejecuta app.main() con todo lo externo sustituido; devuelve las llamadas a load_transcriber."""
    llamadas = []
    EVENTOS_LOG.clear()

    def load(*args):
        llamadas.append(args)
        if error is not None:
            raise error
        return transcriber

    class Parada(Exception):
        pass

    monkeypatch.setattr(app, "load_transcriber", load)
    monkeypatch.setattr(app, "setup_logging", lambda nivel="info": EVENTOS_LOG.append(("setup_logging", nivel)))
    monkeypatch.setattr(app, "apply_log_levels", lambda consola, archivo: EVENTOS_LOG.append(("apply_log_levels", consola, archivo)))
    monkeypatch.setattr(app, "log_banner", lambda: EVENTOS_LOG.append(("log_banner",)))
    monkeypatch.setattr(app, "resolve_config", lambda explicit: EVENTOS_LOG.append(("resolve_config",)) or config or Config())
    monkeypatch.setattr(app.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(app.sd, "query_devices", lambda *a, **k: {"name": "mic", "default_samplerate": 16000})
    monkeypatch.setattr(app, "describe_device", lambda device: "mic")
    def crear_ptt(*a, **k):
        llamadas.append(("PushToTalk", a))
        raise Parada()

    monkeypatch.setattr(app, "PushToTalk", crear_ptt)
    monkeypatch.setattr("sys.argv", ["speechflow", "--device", "0", *argumentos])
    return llamadas, Parada


class TestMainNivelesDeLog:
    def correr(self, monkeypatch, argumentos, config=None):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        llamadas, Parada = ejecutar_main(monkeypatch, argumentos, t, config=config)
        with pytest.raises(Parada):
            app.main()
        return {l[0]: l[1:] for l in EVENTOS_LOG}

    def test_defecto(self, monkeypatch):
        r = self.correr(monkeypatch, [])
        assert r["setup_logging"] == ("info",) and r["apply_log_levels"] == ("info", "info") and "log_banner" in r

    @pytest.mark.parametrize(
        "opcion, nivel", [(["--quiet"], "warning"), (["--verbose"], "debug"), (["--log-level", "error"], "error")]
    )
    def test_cli_fija_el_nivel_inicial_y_final(self, monkeypatch, opcion, nivel):
        r = self.correr(monkeypatch, opcion, config=Config(log_level="debug", log_file_level="warning"))
        assert r["setup_logging"] == (nivel,) and r["apply_log_levels"] == (nivel, "warning")

    def test_toml_sin_cli(self, monkeypatch):
        r = self.correr(monkeypatch, [], config=Config(log_level="warning", log_file_level="debug"))
        assert r["setup_logging"] == ("info",) and r["apply_log_levels"] == ("warning", "debug")

    @pytest.mark.parametrize("nivel, banner", [("debug", True), ("info", True), ("warning", False), ("error", False)])
    def test_banner_segun_nivel_final(self, monkeypatch, nivel, banner):
        r = self.correr(monkeypatch, [], config=Config(log_level=nivel))
        assert ("log_banner" in r) is banner

    def test_orden_de_arranque(self, monkeypatch):
        self.correr(monkeypatch, [])
        assert [e[0] for e in EVENTOS_LOG] == ["setup_logging", "resolve_config", "apply_log_levels", "log_banner"]

    @pytest.mark.parametrize("opciones", [["--quiet", "--verbose"], ["--quiet", "--log-level", "info"], ["--verbose", "--log-level", "debug"]])
    def test_opciones_excluyentes(self, monkeypatch, opciones, capsys):
        _, Parada = ejecutar_main(monkeypatch, opciones)
        with pytest.raises(SystemExit) as salida:
            app.main()
        assert salida.value.code == 2 and "not allowed with" in capsys.readouterr().err

    def test_log_level_invalido(self, monkeypatch):
        ejecutar_main(monkeypatch, ["--log-level", "trace"])
        with pytest.raises(SystemExit) as salida:
            app.main()
        assert salida.value.code == 2

    def test_debug_de_comprobacion(self, monkeypatch, caplog):
        caplog.set_level("DEBUG", logger="speechflow")
        self.correr(monkeypatch, ["--verbose"], config=Config(log_file_level="warning"))
        assert any(r.levelname == "DEBUG" and r.getMessage() == "Niveles de log: consola=debug, archivo=warning" for r in caplog.records)


class TestMainDispositivo:
    def test_cli_gana_sobre_config(self, monkeypatch):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        llamadas, Parada = ejecutar_main(monkeypatch, ["--compute-device", "cpu"], t, config=Config(device_compute="cuda", cpu_threads=3))
        with pytest.raises(Parada):
            app.main()
        assert llamadas[0][3:] == ("cpu", 3)
        assert llamadas[1][1][14:16] == ("cpu", 3)

    def test_push_to_talk_recibe_el_dispositivo_resuelto_no_auto(self, monkeypatch):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        llamadas, Parada = ejecutar_main(monkeypatch, [], t, config=Config(cpu_threads=2))
        with pytest.raises(Parada):
            app.main()
        assert llamadas[0][3] == "auto" and llamadas[1][1][14:16] == ("cpu", 2)

    def test_sin_cli_usa_config(self, monkeypatch):
        t = type("T", (), {"device": "cuda", "model_name": "medium"})()
        llamadas, Parada = ejecutar_main(monkeypatch, [], t, config=Config(device_compute="cuda"))
        with pytest.raises(Parada):
            app.main()
        assert llamadas[0][3] == "cuda"

    def test_cuda_con_fallo_sale_con_1_y_sugiere_cpu(self, monkeypatch, caplog):
        llamadas, _ = ejecutar_main(monkeypatch, ["--compute-device", "cuda"], error=RuntimeError("sin driver"))
        with pytest.raises(SystemExit) as salida:
            app.main()
        assert salida.value.code == 1
        assert "--compute-device cpu" in caplog.text and "sin driver" in caplog.text

    def test_auto_que_cae_a_cpu_notifica(self, monkeypatch, subprocess_falso):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        _, Parada = ejecutar_main(monkeypatch, [], t)
        with pytest.raises(Parada):
            app.main()
        assert any("Sin GPU utilizable: se usa la CPU" in str(c) for c in subprocess_falso)

    def test_auto_con_gpu_no_notifica_caida(self, monkeypatch, subprocess_falso):
        t = type("T", (), {"device": "cuda", "model_name": "medium"})()
        _, Parada = ejecutar_main(monkeypatch, [], t)
        with pytest.raises(Parada):
            app.main()
        assert not any("Sin GPU utilizable" in str(c) for c in subprocess_falso)

    def test_cpu_explicito_no_notifica_caida(self, monkeypatch, subprocess_falso):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        _, Parada = ejecutar_main(monkeypatch, ["--compute-device", "cpu"], t)
        with pytest.raises(Parada):
            app.main()
        assert not any("Sin GPU utilizable" in str(c) for c in subprocess_falso)

    @pytest.mark.parametrize("modelo, avisa", [("medium", True), ("small", False)])
    def test_aviso_de_lentitud_en_cpu(self, monkeypatch, caplog, modelo, avisa):
        t = type("T", (), {"device": "cpu", "model_name": modelo})()
        _, Parada = ejecutar_main(monkeypatch, ["--compute-device", "cpu", "--model", modelo], t)
        with caplog.at_level("INFO", logger="speechflow"), pytest.raises(Parada):
            app.main()
        avisos = [r for r in caplog.records if r.levelname == "WARNING" and "small" in r.getMessage() and "lento" in r.getMessage()]
        assert bool(avisos) is avisa
        assert any("| CPU |" in r.getMessage() for r in caplog.records)

    def test_modelo_sin_fijar_se_pasa_como_none_y_se_usa_el_cargado(self, monkeypatch, caplog, subprocess_falso):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        llamadas, Parada = ejecutar_main(monkeypatch, [], t)
        with caplog.at_level("INFO", logger="speechflow"), pytest.raises(Parada):
            app.main()
        assert llamadas[0][0] is None and llamadas[1][1][4] == "small"
        textos = [str(c) for c in subprocess_falso]
        assert any("Cargando modelo..." in c for c in textos) and any("Modelo small cargado" in c for c in textos)
        assert any(r.getMessage().startswith("Modelo: small |") for r in caplog.records)

    def test_modelo_fijado_notifica_su_nombre(self, monkeypatch, subprocess_falso):
        t = type("T", (), {"device": "cpu", "model_name": "medium"})()
        llamadas, Parada = ejecutar_main(monkeypatch, ["--model", "medium"], t)
        with pytest.raises(Parada):
            app.main()
        assert llamadas[0][0] == "medium" and any("Cargando medium..." in str(c) for c in subprocess_falso)

    def test_medium_en_gpu_no_avisa(self, monkeypatch, caplog):
        t = type("T", (), {"device": "cuda", "model_name": "medium"})()
        _, Parada = ejecutar_main(monkeypatch, [], t)
        with caplog.at_level("INFO", logger="speechflow"), pytest.raises(Parada):
            app.main()
        assert not any("lento" in r.getMessage() for r in caplog.records)
        assert any("| GPU |" in r.getMessage() for r in caplog.records)


class TestReadyMessage:
    def test_hold(self):
        assert app.ready_message("ctrl_r", "hold") == "Listo. Mantén pulsada la tecla 'ctrl_r' para dictar. Ctrl+C para salir."

    def test_toggle(self):
        assert app.ready_message("ctrl_r", "toggle") == (
            "Listo. Pulsa la tecla 'ctrl_r' para empezar a dictar y púlsala de nuevo para parar. Ctrl+C para salir."
        )


class TestResolveConfig:
    def mensajes(self, caplog):
        return [(r.levelname, r.getMessage()) for r in caplog.records]

    def test_archivo_valido(self, caplog):
        ruta = config.user_config_path()
        ruta.parent.mkdir(parents=True)
        ruta.write_text('[model]\nname = "small"\n')
        with caplog.at_level("INFO", logger="speechflow"):
            resultado = app.resolve_config(None)
        assert resultado == Config(model="small")
        assert self.mensajes(caplog) == [("INFO", f"Configuración: {ruta}")]
        assert not config.emergency_path().exists()

    def test_config_explicito_valido(self, tmp_path, caplog):
        ruta = tmp_path / "otra.toml"
        ruta.write_text('[keys]\nrecord = "f9"\n')
        with caplog.at_level("INFO", logger="speechflow"):
            assert app.resolve_config(ruta).key == "f9"
        assert self.mensajes(caplog) == [("INFO", f"Configuración: {ruta}")]

    def test_archivo_invalido(self, caplog):
        ruta = config.user_config_path()
        ruta.parent.mkdir(parents=True)
        ruta.write_text("[foo]\n")
        with caplog.at_level("INFO", logger="speechflow"):
            resultado = app.resolve_config(None)
        assert resultado == Config()
        assert self.mensajes(caplog) == [
            (
                "WARNING",
                f"Configuración inválida en {ruta}: sección desconocida [foo]. "
                f"Se usan los valores por defecto; plantilla en {config.emergency_path()}.",
            ),
            ("INFO", "Configuración: valores por defecto"),
        ]
        assert config.load_config(config.emergency_path()) == Config()

    def test_archivo_ausente(self, caplog):
        with caplog.at_level("INFO", logger="speechflow"):
            resultado = app.resolve_config(None)
        assert resultado == Config()
        assert self.mensajes(caplog) == [
            (
                "WARNING",
                f"No se encontró {config.user_config_path()}. "
                f"Se usan los valores por defecto; plantilla en {config.emergency_path()}.",
            ),
            ("INFO", "Configuración: valores por defecto"),
        ]
        assert config.emergency_path().is_file()

    def test_config_explicito_inexistente(self, tmp_path, caplog):
        ruta = tmp_path / "no.toml"
        with caplog.at_level("INFO", logger="speechflow"), pytest.raises(SystemExit) as salida:
            app.resolve_config(ruta)
        assert salida.value.code == 1
        assert self.mensajes(caplog) == [("ERROR", f"No existe el archivo de configuración {ruta}.")]
        assert not config.emergency_path().exists()

    def test_sin_home(self, monkeypatch, caplog):
        monkeypatch.delenv("XDG_CONFIG_HOME")
        monkeypatch.setattr(Path, "expanduser", lambda self: (_ for _ in ()).throw(RuntimeError("no hay HOME")))
        with caplog.at_level("INFO", logger="speechflow"):
            resultado = app.resolve_config(None)
        assert resultado == Config()
        nivel, texto = self.mensajes(caplog)[0]
        assert nivel == "WARNING"
        assert texto == (
            "No se encontró el archivo de configuración: no hay HOME. "
            "Se usan los valores por defecto; no se pudo crear la plantilla de emergencia: no hay HOME."
        )

    def test_plantilla_de_emergencia_no_se_puede_escribir(self, monkeypatch, caplog):
        def falla():
            raise PermissionError("denegado")

        monkeypatch.setattr(app, "write_emergency", falla)
        with caplog.at_level("INFO", logger="speechflow"):
            assert app.resolve_config(None) == Config()
        assert "no se pudo crear la plantilla de emergencia: denegado." in caplog.records[0].getMessage()


class TestMainInsercion:
    def correr(self, monkeypatch, config=None, sin=()):
        t = type("T", (), {"device": "cpu", "model_name": "small"})()
        llamadas, Parada = ejecutar_main(monkeypatch, [], t, config=config)
        monkeypatch.setattr(app.shutil, "which", lambda name: None if name in sin else "/usr/bin/" + name)
        return llamadas, Parada

    def test_push_to_talk_recibe_la_configuracion(self, monkeypatch):
        llamadas, Parada = self.correr(monkeypatch, Config(insert_method="type", terminal_classes=("myterm",)))
        with pytest.raises(Parada):
            app.main()
        assert llamadas[1][1][16:18] == ("type", ("myterm",))

    def test_defectos_llegan_a_push_to_talk(self, monkeypatch):
        llamadas, Parada = self.correr(monkeypatch)
        with pytest.raises(Parada):
            app.main()
        assert llamadas[1][1][16:18] == ("clipboard", ())

    def test_sin_xclip_y_clipboard_sale_con_1(self, monkeypatch, caplog):
        llamadas, _ = self.correr(monkeypatch, Config(insert_method="clipboard"), sin=("xclip",))
        with pytest.raises(SystemExit) as salida:
            app.main()
        assert salida.value.code == 1
        assert "Falta xclip. Instálalo con: sudo apt install xclip" in caplog.text
        assert not any(l[0] == "PushToTalk" for l in llamadas)

    def test_sin_xclip_y_type_arranca(self, monkeypatch, caplog):
        _, Parada = self.correr(monkeypatch, Config(insert_method="type"), sin=("xclip",))
        with pytest.raises(Parada):
            app.main()
        assert "Falta xclip" not in caplog.text

    def test_xdotool_se_comprueba_antes_que_xclip(self, monkeypatch, caplog):
        self.correr(monkeypatch, sin=("xdotool", "xclip"))
        with pytest.raises(SystemExit):
            app.main()
        assert "Falta xdotool" in caplog.text and "Falta xclip" not in caplog.text
