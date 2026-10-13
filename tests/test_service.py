"""Tests de speechflow.service."""
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
