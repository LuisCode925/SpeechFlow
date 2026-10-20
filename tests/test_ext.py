"""Tests de speechflow.ext."""
import logging
import subprocess
import sys

import pytest

from speechflow import ext


@pytest.fixture(autouse=True)
def datos_temporales(tmp_path, monkeypatch):
    """El directorio de extensiones es temporal; nunca se toca el del usuario."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))


@pytest.fixture
def gnome_extensions(monkeypatch, subprocess_falso):
    """Hace visible gnome-extensions y devuelve la lista de llamadas del doble de subprocess.run."""
    monkeypatch.setattr(ext.shutil, "which", lambda nombre: f"/usr/bin/{nombre}")
    return subprocess_falso


@pytest.fixture
def sin_gnome_extensions(monkeypatch):
    monkeypatch.setattr(ext.shutil, "which", lambda nombre: None)


@pytest.fixture
def logger_limpio():
    """main() instala manejadores en el logger del paquete; se restauran al terminar."""
    logger = logging.getLogger("speechflow")
    antes = (list(logger.handlers), logger.propagate, logger.level)
    yield logger
    logger.handlers[:] = antes[0]
    logger.propagate, level = antes[1], antes[2]
    logger.setLevel(level)


class TestExtensionDir:
    def test_usa_xdg_data_home(self, tmp_path):
        assert ext.extension_dir() == tmp_path / "xdg-data" / "gnome-shell" / "extensions" / "speechflow@local"

    def test_defecto_en_home(self, monkeypatch):
        monkeypatch.delenv("XDG_DATA_HOME")
        assert ext.extension_dir() == ext.Path.home() / ".local" / "share" / "gnome-shell" / "extensions" / "speechflow@local"


class TestInstall:
    def test_copia_los_archivos(self, sin_gnome_extensions):
        assert ext.install() == 0
        for nombre in ext.FILES:
            assert (ext.extension_dir() / nombre).is_file()

    def test_imprime_los_pasos(self, sin_gnome_extensions, caplog):
        caplog.set_level("INFO", logger="speechflow")
        ext.install()
        assert "Alt+F2" in caplog.text
        assert "gnome-extensions enable speechflow@local" in caplog.text

    def test_no_activa_la_extension(self, gnome_extensions):
        ext.install()
        assert gnome_extensions == []

    def test_reinstalar_reemplaza(self, sin_gnome_extensions):
        ext.install()
        (ext.extension_dir() / "extension.js").write_text("modificado")
        (ext.extension_dir() / "sobrante.txt").write_text("x")
        assert ext.install() == 0
        assert (ext.extension_dir() / "extension.js").read_bytes() == ext._package_files()["extension.js"]
        assert not (ext.extension_dir() / "sobrante.txt").exists()

    def test_sin_home(self, monkeypatch, sin_gnome_extensions):
        monkeypatch.delenv("XDG_DATA_HOME")
        monkeypatch.setattr(ext.Path, "expanduser", lambda self: (_ for _ in ()).throw(RuntimeError("sin HOME")))
        assert ext.install() == 1


class TestUninstall:
    def test_borra_el_directorio(self, sin_gnome_extensions):
        ext.install()
        assert ext.uninstall() == 0
        assert not ext.extension_dir().exists()

    def test_idempotente(self, sin_gnome_extensions):
        assert ext.uninstall() == 0
        assert ext.uninstall() == 0

    def test_desactiva_si_existe_el_comando(self, gnome_extensions):
        ext.install()
        ext.uninstall()
        assert [args[0] for args, _ in gnome_extensions] == [["gnome-extensions", "disable", "speechflow@local"]]

    def test_sin_el_comando_no_lo_ejecuta(self, sin_gnome_extensions, subprocess_falso):
        ext.install()
        ext.uninstall()
        assert subprocess_falso == []


class TestStatus:
    def test_no_instalada(self, sin_gnome_extensions, caplog):
        caplog.set_level("INFO", logger="speechflow")
        assert ext.status() == 0
        assert "No instalada" in caplog.text

    def test_coincide(self, sin_gnome_extensions, caplog):
        ext.install()
        caplog.set_level("INFO", logger="speechflow")
        assert ext.status() == 0
        assert "Coincide con la del paquete" in caplog.text

    def test_difiere(self, sin_gnome_extensions, caplog):
        ext.install()
        (ext.extension_dir() / "extension.js").write_text("modificado")
        caplog.set_level("INFO", logger="speechflow")
        ext.status()
        assert "Difiere de la del paquete" in caplog.text

    def test_difiere_si_falta_un_archivo(self, sin_gnome_extensions, caplog):
        ext.install()
        (ext.extension_dir() / "stylesheet.css").unlink()
        caplog.set_level("INFO", logger="speechflow")
        ext.status()
        assert "Difiere" in caplog.text

    def test_muestra_gnome_extensions_info(self, gnome_extensions, monkeypatch, caplog):
        monkeypatch.setattr(subprocess, "run", lambda args, **kw: subprocess.CompletedProcess(args, 0, stdout="Estado: ACTIVE\n", stderr=""))
        caplog.set_level("INFO", logger="speechflow")
        ext.status()
        assert "Estado: ACTIVE" in caplog.text


class TestMain:
    def test_install(self, sin_gnome_extensions, logger_limpio):
        assert ext.main(["install"]) == 0
        assert ext.extension_dir().is_dir()

    def test_sin_subcomando(self, logger_limpio, capsys):
        assert ext.main([]) == 2
        assert "install" in capsys.readouterr().err

    def test_subcomando_desconocido(self, logger_limpio):
        assert ext.main(["borrar"]) == 2

    def test_ayuda(self, logger_limpio, capsys):
        assert ext.main(["--help"]) == 0
        assert "uninstall" in capsys.readouterr().out


class TestPaquete:
    def test_metadata(self):
        import json

        datos = json.loads(ext._package_files()["metadata.json"])
        assert datos["uuid"] == ext.UUID
        assert datos["shell-version"] == ["48"]

    def test_importar_no_arrastra_dependencias_pesadas(self, tmp_path):
        """El doble de subprocess.run no ejecuta nada: se usa Popen."""
        codigo = "import sys, speechflow.ext; print([m for m in ('sounddevice', 'pynput', 'faster_whisper') if m in sys.modules])"
        proceso = subprocess.Popen([sys.executable, "-c", codigo], stdout=subprocess.PIPE, text=True, cwd=tmp_path)
        salida, _ = proceso.communicate()
        assert salida.strip() == "[]"
