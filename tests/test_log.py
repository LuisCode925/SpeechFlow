"""Tests de speechflow.log."""
import logging
import re

import pytest

from speechflow import __version__, log
from speechflow.log import log_banner, setup_logging


@pytest.fixture(autouse=True)
def logger_limpio():
    """Deja el logger `speechflow` como estaba tras cada test."""
    logger = logging.getLogger(log.LOGGER_NAME)
    antes = (list(logger.handlers), logger.level, logger.propagate)
    logger.handlers.clear()
    yield logger
    logger.handlers[:] = antes[0]
    logger.setLevel(antes[1])
    logger.propagate = antes[2]


def test_devuelve_el_logger_speechflow():
    assert setup_logging() is logging.getLogger("speechflow")


def test_no_duplica_manejadores():
    logger = setup_logging()
    setup_logging()
    assert len(logger.handlers) == 2


def test_info_va_a_stdout(capsys):
    setup_logging().info("hola")
    captura = capsys.readouterr()
    assert "hola" in captura.out and captura.err == ""


@pytest.mark.parametrize("nivel", ["warning", "error"])
def test_warning_y_error_van_a_stderr(capsys, nivel):
    getattr(setup_logging(), nivel)("problema")
    captura = capsys.readouterr()
    assert "problema" in captura.err and captura.out == ""


def test_debug_se_descarta(capsys):
    setup_logging().debug("ruido")
    captura = capsys.readouterr()
    assert captura.out == "" and captura.err == ""


def test_formato(capsys):
    setup_logging().info("mensaje")
    linea = capsys.readouterr().out.rstrip("\n")
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3} INFO    mensaje", linea)


def test_formato_warning_alinea_nivel(capsys):
    setup_logging().warning("mensaje")
    assert re.search(r"\.\d{3} WARNING mensaje$", capsys.readouterr().err.strip())


def test_no_propaga_al_root():
    assert setup_logging().propagate is False


class TestBanner:
    def test_imprime_arte_nombre_y_versiones(self, capsys, monkeypatch):
        monkeypatch.setattr(log, "version", lambda nombre: "9.9.9")
        log_banner()
        lineas = capsys.readouterr().out.splitlines()
        assert lineas[0] == log.BANNER_ART.strip("\n").splitlines()[0]
        assert f"SpeechFlow {__version__}" in lineas
        assert "Powered by faster-whisper 9.9.9" in lineas
        assert lineas[-1] == ""

    def test_sin_faster_whisper_instalado(self, capsys, monkeypatch):
        def falla(nombre):
            raise log.PackageNotFoundError(nombre)

        monkeypatch.setattr(log, "version", falla)
        log_banner()
        assert "Powered by faster-whisper\n" in capsys.readouterr().out

    def test_sin_formato_de_log(self, capsys):
        log_banner()
        assert not re.search(r"\d{4}-\d\d-\d\d \d\d:", capsys.readouterr().out)
