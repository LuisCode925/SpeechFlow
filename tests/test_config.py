"""Tests de speechflow.config."""
import tomllib
from pathlib import Path

import pytest

from speechflow import config
from speechflow.config import Config, ConfigError


def escribir(tmp_path, texto, nombre="config.toml"):
    ruta = tmp_path / nombre
    ruta.write_text(texto, encoding="utf-8")
    return ruta


class TestRutasXdg:
    def test_variable_ausente_usa_home(self, monkeypatch):
        """Sin XDG_CONFIG_HOME se usa ~/.config/speechflow."""
        monkeypatch.delenv("XDG_CONFIG_HOME")
        assert config.config_dir() == Path.home() / ".config" / "speechflow"

    def test_variable_vacia_usa_home(self, monkeypatch):
        """Una variable vacía se trata como ausente."""
        monkeypatch.setenv("XDG_STATE_HOME", "")
        assert config.state_dir() == Path.home() / ".local" / "state" / "speechflow"

    def test_variable_relativa_se_ignora(self, monkeypatch):
        """Una ruta relativa no es válida según XDG y se ignora."""
        monkeypatch.setenv("XDG_CONFIG_HOME", "relativa/dir")
        assert config.config_dir() == Path.home() / ".config" / "speechflow"

    def test_variable_absoluta(self, tmp_path, monkeypatch):
        """Una ruta absoluta se usa tal cual más 'speechflow'."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "x"))
        assert config.config_dir() == tmp_path / "x" / "speechflow"
        assert config.user_config_path() == tmp_path / "x" / "speechflow" / "config.toml"
        assert config.emergency_path().name == "config.emergency.toml"

    def test_state_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "s"))
        assert config.state_path() == tmp_path / "s" / "speechflow" / "state.toml"

    def test_sin_home_lanza_runtimeerror(self, monkeypatch):
        """Sin HOME ni variable XDG, expanduser falla con RuntimeError."""
        monkeypatch.delenv("XDG_CONFIG_HOME")
        monkeypatch.delenv("HOME")
        monkeypatch.setattr(Path, "expanduser", lambda self: (_ for _ in ()).throw(RuntimeError("sin home")))
        with pytest.raises(RuntimeError):
            config.config_dir()


class TestFindConfig:
    def test_explicito_existente(self, tmp_path):
        ruta = escribir(tmp_path, "")
        assert config.find_config(ruta) == ruta

    def test_explicito_inexistente(self, tmp_path):
        assert config.find_config(tmp_path / "no.toml") is None

    def test_usuario_existente(self):
        ruta = config.user_config_path()
        ruta.parent.mkdir(parents=True)
        ruta.write_text("")
        assert config.find_config(None) == ruta

    def test_usuario_ausente(self):
        assert config.find_config(None) is None

    def test_sin_home(self, monkeypatch):
        def falla():
            raise RuntimeError

        monkeypatch.setattr(config, "user_config_path", falla)
        assert config.find_config(None) is None


class TestLoadConfig:
    def test_archivo_vacio_da_defectos(self, tmp_path):
        assert config.load_config(escribir(tmp_path, "")) == Config()

    def test_valido_completo(self, tmp_path):
        ruta = escribir(
            tmp_path,
            '[model]\nname = "small"\nlanguage = "en"\nidle_timeout = 60\n'
            '[keys]\nrecord = "f9"\nswitch = "f10"\n'
            '[audio]\ndevice = "Realtek"\nwatch_interval = 2\n'
            "[recording]\nmin_seconds = 1\nmax_seconds = 10\n"
            "[notifications]\nenabled = false\n",
        )
        c = config.load_config(ruta)
        assert c == Config("small", "en", "f9", "f10", "Realtek", 1.0, 10.0, 2.0, False, 60.0)
        assert isinstance(c.min_seconds, float)

    def test_device_entero(self, tmp_path):
        assert config.load_config(escribir(tmp_path, "[audio]\ndevice = 3\n")).device == 3

    def test_omitido_toma_defecto(self, tmp_path):
        c = config.load_config(escribir(tmp_path, '[keys]\nrecord = "f9"\n'))
        assert c.key == "f9" and c.switch_key == Config().switch_key

    def test_archivo_inexistente(self, tmp_path):
        with pytest.raises(ConfigError, match="no se puede leer"):
            config.load_config(tmp_path / "no.toml")

    def test_toml_mal_formado(self, tmp_path):
        with pytest.raises(ConfigError, match="TOML mal formado"):
            config.load_config(escribir(tmp_path, "[model\n"))

    def test_seccion_desconocida(self, tmp_path):
        with pytest.raises(ConfigError, match=r"sección desconocida \[foo\]"):
            config.load_config(escribir(tmp_path, "[foo]\na = 1\n"))

    def test_seccion_no_tabla(self, tmp_path):
        with pytest.raises(ConfigError, match="debe ser una tabla"):
            config.load_config(escribir(tmp_path, "model = 1\n"))

    def test_clave_desconocida(self, tmp_path):
        with pytest.raises(ConfigError, match="clave desconocida model.foo"):
            config.load_config(escribir(tmp_path, "[model]\nfoo = 1\n"))

    def test_tipo_invalido(self, tmp_path):
        with pytest.raises(ConfigError, match="model.name debe ser str, no int"):
            config.load_config(escribir(tmp_path, "[model]\nname = 1\n"))

    def test_bool_no_vale_como_int(self, tmp_path):
        with pytest.raises(ConfigError, match="recording.min_seconds debe ser int o float, no bool"):
            config.load_config(escribir(tmp_path, "[recording]\nmin_seconds = true\n"))

    def test_bool_no_vale_como_device(self, tmp_path):
        with pytest.raises(ConfigError, match="audio.device"):
            config.load_config(escribir(tmp_path, "[audio]\ndevice = true\n"))

    def test_int_no_vale_como_bool(self, tmp_path):
        with pytest.raises(ConfigError, match="notifications.enabled debe ser bool, no int"):
            config.load_config(escribir(tmp_path, "[notifications]\nenabled = 1\n"))

    @pytest.mark.parametrize(
        "texto, mensaje",
        [
            ("[recording]\nmin_seconds = 0\n", "min_seconds debe ser mayor que 0"),
            ("[recording]\nmin_seconds = -1\n", "min_seconds debe ser mayor que 0"),
            ("[recording]\nmin_seconds = 5\nmax_seconds = 5\n", "max_seconds"),
            ("[recording]\nmax_seconds = 0.2\n", "max_seconds"),
            ("[audio]\nwatch_interval = 0.5\n", "watch_interval debe ser al menos 1.0"),
            ("[model]\nidle_timeout = 10\n", "idle_timeout debe ser 0 o al menos 30.0"),
            ("[model]\nidle_timeout = -5\n", "idle_timeout debe ser 0 o al menos 30.0"),
        ],
    )
    def test_rangos_invalidos(self, tmp_path, texto, mensaje):
        with pytest.raises(ConfigError, match=mensaje):
            config.load_config(escribir(tmp_path, texto))

    @pytest.mark.parametrize(
        "texto",
        ["[audio]\nwatch_interval = 1.0\n", "[model]\nidle_timeout = 30\n", "[model]\nidle_timeout = 0\n"],
    )
    def test_limites_validos(self, tmp_path, texto):
        config.load_config(escribir(tmp_path, texto))


class TestWriteEmergency:
    def test_crea_plantilla_y_carpeta(self):
        ruta = config.write_emergency()
        assert ruta == config.emergency_path() and ruta.is_file()

    def test_no_pisa_existente(self):
        ruta = config.emergency_path()
        ruta.parent.mkdir(parents=True)
        ruta.write_text("# mio\n")
        config.write_emergency()
        assert ruta.read_text() == "# mio\n"

    def test_plantilla_da_defectos(self):
        assert config.load_config(config.write_emergency()) == Config()


class TestEstado:
    def test_sin_archivo(self):
        assert config.load_state_device() is None

    def test_ida_y_vuelta(self):
        config.save_state_device('Mi "micro" ñ')
        assert config.load_state_device() == 'Mi "micro" ñ'

    def test_sobrescribe(self):
        config.save_state_device("a")
        config.save_state_device("b")
        assert config.load_state_device() == "b"

    def test_sin_clave_device(self):
        config.state_path().parent.mkdir(parents=True)
        config.state_path().write_text("otra = 1\n")
        assert config.load_state_device() is None

    def test_archivo_ilegible(self, caplog):
        config.state_path().parent.mkdir(parents=True)
        config.state_path().write_text("device = [\n")
        with caplog.at_level("WARNING", logger="speechflow"):
            assert config.load_state_device() is None
        assert "Archivo de estado ilegible" in caplog.text

    def test_tipo_invalido(self, caplog):
        config.state_path().parent.mkdir(parents=True)
        config.state_path().write_text("device = 3\n")
        with caplog.at_level("WARNING", logger="speechflow"):
            assert config.load_state_device() is None
        assert "device debe ser texto" in caplog.text

    def test_sin_home(self, monkeypatch):
        def falla():
            raise RuntimeError

        monkeypatch.setattr(config, "state_path", falla)
        assert config.load_state_device() is None

    def test_escritura_atomica(self, monkeypatch):
        """Se escribe un temporal y se reemplaza con os.replace; no queda temporal."""
        reemplazos = []
        real = config.os.replace
        monkeypatch.setattr(config.os, "replace", lambda a, b: (reemplazos.append((Path(a), Path(b))), real(a, b)))
        config.save_state_device("x")
        (origen, destino), = reemplazos
        assert destino == config.state_path() and origen != destino and origen.suffix == ".tmp"
        assert [p.name for p in destino.parent.iterdir()] == ["state.toml"]
        assert tomllib.loads(destino.read_text()) == {"device": "x"}
