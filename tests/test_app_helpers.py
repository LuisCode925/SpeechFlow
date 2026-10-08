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
            def __init__(self, model, language):
                creados.append((model, language))

        monkeypatch.setattr(app, "Transcriber", TranscriberFalso)
        with caplog.at_level("INFO", logger="speechflow"):
            resultado = app.load_transcriber("small", "en")
        assert isinstance(resultado, TranscriberFalso) and creados == [("small", "en")]
        mensajes = [r.getMessage() for r in caplog.records]
        assert mensajes[0] == "Cargando small (int8, GPU)..."
        assert mensajes[1].startswith("Modelo cargado en ") and mensajes[1].endswith(" s (incluye calentamiento)")

    def test_no_notifica(self, monkeypatch, subprocess_falso):
        monkeypatch.setattr(app, "Transcriber", lambda model, language: object())
        app.load_transcriber("small", "en")
        assert subprocess_falso == []


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
