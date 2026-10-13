"""Tests de speechflow.log."""
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from speechflow import __version__, config, log
from speechflow.log import apply_log_levels, log_banner, setup_logging


@pytest.fixture(autouse=True)
def logger_limpio():
    """Deja el logger `speechflow` como estaba tras cada test."""
    logger = logging.getLogger(log.LOGGER_NAME)
    antes = (list(logger.handlers), logger.level, logger.propagate)
    logger.handlers.clear()
    yield logger
    for handler in logger.handlers:
        handler.close()
    logger.handlers[:] = antes[0]
    logger.setLevel(antes[1])
    logger.propagate = antes[2]


def test_devuelve_el_logger_speechflow():
    assert setup_logging() is logging.getLogger("speechflow")


def test_no_duplica_manejadores():
    logger = setup_logging()
    setup_logging()
    assert len(logger.handlers) == 3
    assert sum(isinstance(h, RotatingFileHandler) for h in logger.handlers) == 1


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


def emitir_todo(logger):
    logger.debug("d")
    logger.info("i")
    logger.warning("w")
    logger.error("e")


@pytest.mark.parametrize(
    "nivel, stdout, stderr",
    [
        ("debug", ["d", "i"], ["w", "e"]),
        ("info", ["i"], ["w", "e"]),
        ("warning", [], ["w", "e"]),
        ("error", [], ["e"]),
    ],
)
class TestNivelConsola:
    def lineas(self, texto):
        return [l.split(None, 3)[3] for l in texto.splitlines()]

    def test_nivel_inicial(self, capsys, nivel, stdout, stderr):
        emitir_todo(setup_logging(nivel))
        captura = capsys.readouterr()
        assert self.lineas(captura.out) == stdout and self.lineas(captura.err) == stderr

    def test_apply_log_levels(self, capsys, nivel, stdout, stderr):
        logger = setup_logging()
        apply_log_levels(nivel, "info")
        emitir_todo(logger)
        captura = capsys.readouterr()
        assert self.lineas(captura.out) == stdout and self.lineas(captura.err) == stderr


class TestNivelArchivo:
    def niveles_en_archivo(self):
        return [l.split(None, 3)[3] for l in config.log_path().read_text(encoding="utf-8").splitlines()]

    @pytest.mark.parametrize(
        "nivel, esperado",
        [("debug", ["d", "i", "w", "e"]), ("info", ["i", "w", "e"]), ("warning", ["w", "e"]), ("error", ["e"])],
    )
    def test_file_level(self, capsys, nivel, esperado):
        logger = setup_logging()
        apply_log_levels("info", nivel)
        emitir_todo(logger)
        assert self.niveles_en_archivo() == esperado

    def test_independiente_de_la_consola(self, capsys):
        logger = setup_logging("error")
        emitir_todo(logger)
        assert self.niveles_en_archivo() == ["i", "w", "e"]
        captura = capsys.readouterr()
        assert captura.out == "" and [l.split(None, 3)[3] for l in captura.err.splitlines()] == ["e"]

    def test_consola_debug_no_cambia_el_archivo(self, capsys):
        emitir_todo(setup_logging("debug"))
        assert self.niveles_en_archivo() == ["i", "w", "e"]

    def test_segunda_llamada_no_cambia_niveles(self, capsys):
        logger = setup_logging("error")
        setup_logging("debug")
        emitir_todo(logger)
        assert capsys.readouterr().out == ""


def modo(ruta):
    return ruta.stat().st_mode & 0o777


class TestArchivo:
    def test_recibe_info_warning_y_error_sin_debug(self, capsys):
        logger = setup_logging()
        logger.debug("ruido")
        logger.info("uno")
        logger.warning("dos")
        logger.error("tres")
        lineas = config.log_path().read_text(encoding="utf-8").splitlines()
        assert [l.split(None, 3)[2:] for l in lineas] == [["INFO", "uno"], ["WARNING", "dos"], ["ERROR", "tres"]]

    def test_mismo_formato_que_la_consola(self, capsys):
        setup_logging().warning("mensaje")
        consola = capsys.readouterr().err
        assert config.log_path().read_text(encoding="utf-8") == consola

    def test_no_recibe_el_banner(self, capsys):
        setup_logging()
        log_banner()
        assert config.log_path().read_text(encoding="utf-8") == ""

    def test_codificacion_utf8(self):
        setup_logging().info("Insertado (1.0 s): ñandú ✓")
        assert "ñandú ✓" in config.log_path().read_bytes().decode("utf-8")

    def test_crea_la_carpeta_con_modo_0600(self):
        assert not config.state_dir().exists()
        setup_logging()
        assert modo(config.log_path()) == 0o600

    def test_dos_llamadas_dejan_un_manejador_de_archivo(self):
        logger = setup_logging()
        setup_logging()
        assert sum(isinstance(h, RotatingFileHandler) for h in logger.handlers) == 1

    def test_rota_y_conserva_permisos_0600(self, monkeypatch):
        monkeypatch.setattr(log, "LOG_MAX_BYTES", 200)
        monkeypatch.setattr(log, "LOG_BACKUP_COUNT", 3)
        logger = setup_logging()
        for i in range(60):
            logger.info("linea %02d %s", i, "x" * 20)
        base = config.log_path()
        nombres = sorted(p.name for p in base.parent.iterdir())
        assert nombres == ["speechflow.log", "speechflow.log.1", "speechflow.log.2", "speechflow.log.3"]
        assert all(modo(p) == 0o600 for p in base.parent.iterdir())

    def test_umask_restrictiva_no_afloja_el_modo(self):
        anterior = os.umask(0o077)
        try:
            setup_logging()
        finally:
            os.umask(anterior)
        assert modo(config.log_path()) == 0o600

    def test_import_no_crea_archivos(self, tmp_path):
        import importlib

        importlib.reload(log)
        assert not (tmp_path / "xdg-state").exists()

    @pytest.mark.skipif(os.geteuid() == 0, reason="root ignora los permisos")
    def test_carpeta_no_escribible_avisa_y_sigue(self, tmp_path, capsys):
        estado = tmp_path / "xdg-state"
        estado.mkdir()
        estado.chmod(0o500)
        try:
            logger = setup_logging()
            logger.info("sigue")
        finally:
            estado.chmod(0o700)
        captura = capsys.readouterr()
        assert "No se puede escribir el log en" in captura.err
        assert "Solo habrá log por consola." in captura.err
        assert "sigue" in captura.out
        assert not any(isinstance(h, RotatingFileHandler) for h in logger.handlers)

    def test_sin_home_avisa_y_sigue(self, monkeypatch, capsys):
        monkeypatch.delenv("XDG_STATE_HOME")
        monkeypatch.delenv("HOME")

        def sin_home(self):
            raise RuntimeError("sin home")

        monkeypatch.setattr(Path, "expanduser", sin_home)
        logger = setup_logging()
        logger.info("sigue")
        captura = capsys.readouterr()
        assert "No se puede escribir el log en" in captura.err
        assert "sigue" in captura.out
        assert len(logger.handlers) == 2


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
