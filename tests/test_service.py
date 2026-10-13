"""Tests de speechflow.service."""
import logging
import subprocess
from pathlib import Path

import pytest

from speechflow import service


class TestRenderUnit:
    def test_contiene_exec_start(self):
        """ExecStart usa el Python indicado con -m speechflow."""
        assert "ExecStart=/ruta/python -m speechflow\n" in service.render_unit("/ruta/python", "/ruta")

    def test_contiene_ld_library_path(self):
        """LD_LIBRARY_PATH apunta a <prefix>/lib."""
        assert "Environment=LD_LIBRARY_PATH=/ruta/lib\n" in service.render_unit("/ruta/python", "/ruta")

    def test_reinicio_e_instalacion(self):
        """Reinicia solo ante fallos y cuelga de graphical-session.target."""
        unidad = service.render_unit("/ruta/python", "/ruta")
        assert "Restart=on-failure" in unidad
        assert "WantedBy=graphical-session.target" in unidad
        assert "PartOf=graphical-session.target" in unidad
        assert "TimeoutStopSec=40" in unidad

    @pytest.mark.parametrize("caracter", [" ", "\t", "\n", "%"])
    def test_python_invalido(self, caracter):
        """Un carácter con significado en la unidad en `python` lanza ValueError."""
        with pytest.raises(ValueError):
            service.render_unit(f"/ruta{caracter}python", "/ruta")

    @pytest.mark.parametrize("caracter", [" ", "\t", "\n", "%"])
    def test_prefix_invalido(self, caracter):
        """Un carácter con significado en la unidad en `prefix` lanza ValueError."""
        with pytest.raises(ValueError):
            service.render_unit("/ruta/python", f"/ruta{caracter}env")


class TestUnitPath:
    def test_respeta_xdg_config_home(self, tmp_path, monkeypatch):
        """Con XDG_CONFIG_HOME absoluta la unidad vive bajo ella."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        assert service.unit_path() == tmp_path / "cfg" / "systemd" / "user" / "speechflow.service"

    def test_por_defecto_usa_home(self, monkeypatch):
        """Sin XDG_CONFIG_HOME se usa ~/.config/systemd/user."""
        monkeypatch.delenv("XDG_CONFIG_HOME")
        assert service.unit_path() == Path.home() / ".config" / "systemd" / "user" / "speechflow.service"


@pytest.fixture
def systemctl(monkeypatch, subprocess_falso):
    """Hace visible systemctl y devuelve la lista de llamadas registradas por el doble de subprocess.run."""
    monkeypatch.setattr(service.shutil, "which", lambda nombre: f"/usr/bin/{nombre}")
    return subprocess_falso


@pytest.fixture
def logger_limpio():
    """main() instala manejadores en el logger del paquete; se restauran al terminar."""
    logger = logging.getLogger("speechflow")
    antes = (list(logger.handlers), logger.propagate, logger.level)
    yield logger
    logger.handlers[:] = antes[0]
    logger.propagate, level = antes[1], antes[2]
    logger.setLevel(level)


def comandos(llamadas):
    return [args[0][2:] for args, _ in llamadas]


def hacer_fallar(monkeypatch, codigo=1, stderr="Failed to connect to bus"):
    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, codigo, "", stderr)

    monkeypatch.setattr(subprocess, "run", run)


class TestInstall:
    def test_escribe_unidad_y_ejecuta_en_orden(self, systemctl):
        """install escribe la unidad y llama a daemon-reload y luego a enable --now."""
        assert service.install() == 0
        unidad = service.unit_path().read_text(encoding="utf-8")
        assert unidad.startswith("[Unit]")
        assert comandos(systemctl) == [["daemon-reload"], ["enable", "--now", "speechflow.service"]]
        assert all(args[0][:2] == ["systemctl", "--user"] for args, _ in systemctl)
        assert all(not kwargs.get("shell") for _, kwargs in systemctl)

    def test_usa_el_python_del_entorno(self, systemctl):
        """La unidad apunta a sys.executable y sys.prefix."""
        import sys

        service.install()
        unidad = service.unit_path().read_text(encoding="utf-8")
        assert f"ExecStart={sys.executable} -m speechflow" in unidad
        assert f"LD_LIBRARY_PATH={sys.prefix}/lib" in unidad

    def test_idempotente(self, systemctl):
        """Dos install seguidos no fallan y dejan un único archivo."""
        assert service.install() == 0
        assert service.install() == 0
        assert len(list(service.unit_path().parent.iterdir())) == 1
        assert not any(c[0] == "restart" for c in comandos(systemctl))

    def test_mensaje_indica_restart(self, systemctl, caplog):
        """El mensaje final indica cómo aplicar una unidad cambiada."""
        caplog.set_level("INFO", logger="speechflow")
        service.install()
        assert "systemctl --user restart speechflow" in caplog.text

    def test_sin_systemctl(self, monkeypatch, subprocess_falso, caplog):
        """Sin systemctl devuelve 1, no escribe nada y no ejecuta nada."""
        monkeypatch.setattr(service.shutil, "which", lambda nombre: None)
        assert service.install() == 1
        assert not service.unit_path().exists()
        assert subprocess_falso == []

    def test_systemctl_falla(self, systemctl, monkeypatch, caplog):
        """Si systemctl devuelve error, install devuelve 1 y muestra su salida de error."""
        hacer_fallar(monkeypatch)
        assert service.install() == 1
        assert "Failed to connect to bus" in caplog.text

    def test_systemctl_no_ejecutable(self, systemctl, monkeypatch):
        """Un OSError al lanzar systemctl devuelve 1."""

        def run(*args, **kwargs):
            raise FileNotFoundError("systemctl")

        monkeypatch.setattr(subprocess, "run", run)
        assert service.install() == 1

    def test_sin_home(self, systemctl, monkeypatch):
        """Sin HOME devuelve 1 en vez de lanzar la excepción."""
        monkeypatch.delenv("XDG_CONFIG_HOME")

        def sin_home():
            raise RuntimeError("HOME no definido")

        monkeypatch.setattr(service, "unit_path", sin_home)
        assert service.install() == 1
        assert systemctl == []


class TestUninstall:
    def test_desactiva_borra_y_recarga(self, systemctl):
        """uninstall desactiva, borra la unidad y recarga, en ese orden."""
        service.install()
        systemctl.clear()
        assert service.uninstall() == 0
        assert not service.unit_path().exists()
        assert comandos(systemctl) == [["disable", "--now", "speechflow.service"], ["daemon-reload"]]

    def test_unidad_ausente(self, systemctl, caplog):
        """Con la unidad ausente informa y devuelve 0 sin llamar a systemctl."""
        caplog.set_level("INFO", logger="speechflow")
        assert service.uninstall() == 0
        assert "El servicio no está instalado." in caplog.text
        assert systemctl == []

    def test_falla_disable_conserva_unidad(self, systemctl, monkeypatch):
        """Si disable falla devuelve 1 y no borra la unidad."""
        service.install()
        hacer_fallar(monkeypatch)
        assert service.uninstall() == 1
        assert service.unit_path().exists()


class TestStatus:
    @pytest.mark.parametrize("codigo", [0, 3, 4])
    def test_devuelve_codigo_de_systemctl(self, systemctl, monkeypatch, codigo):
        """status devuelve el código de salida de systemctl --user status."""
        llamadas = []

        def run(args, **kwargs):
            llamadas.append(args)
            return subprocess.CompletedProcess(args, codigo)

        monkeypatch.setattr(subprocess, "run", run)
        assert service.status() == codigo
        assert llamadas == [["systemctl", "--user", "status", "speechflow.service", "--no-pager"]]

    def test_sin_systemctl(self, monkeypatch):
        """Sin systemctl devuelve 1."""
        monkeypatch.setattr(service.shutil, "which", lambda nombre: None)
        assert service.status() == 1


class TestMain:
    def test_install(self, systemctl, logger_limpio):
        """main(['install']) instala y devuelve 0."""
        assert service.main(["install"]) == 0
        assert service.unit_path().exists()

    def test_uninstall_ausente(self, systemctl, logger_limpio):
        """main(['uninstall']) con la unidad ausente devuelve 0."""
        assert service.main(["uninstall"]) == 0

    def test_status(self, systemctl, logger_limpio, monkeypatch):
        """main(['status']) devuelve el código de systemctl."""
        monkeypatch.setattr(subprocess, "run", lambda args, **kw: subprocess.CompletedProcess(args, 3))
        assert service.main(["status"]) == 3

    def test_sin_subcomando(self, logger_limpio, capsys):
        """Sin subcomando imprime la ayuda y devuelve 2."""
        assert service.main([]) == 2
        assert "install" in capsys.readouterr().err

    def test_subcomando_desconocido(self, logger_limpio, capsys):
        """Un subcomando desconocido devuelve 2."""
        assert service.main(["borrar"]) == 2

    def test_ayuda(self, logger_limpio, capsys):
        """--help muestra la ayuda y devuelve 0."""
        assert service.main(["--help"]) == 0
        assert "uninstall" in capsys.readouterr().out

    def test_no_crea_log_de_archivo(self, systemctl, logger_limpio):
        """El subcomando no abre el log rotativo."""
        from logging.handlers import RotatingFileHandler

        service.main(["uninstall"])
        assert not any(isinstance(h, RotatingFileHandler) for h in logger_limpio.handlers)
        assert not (Path.home().parent / "xdg-state" / "speechflow").exists()
