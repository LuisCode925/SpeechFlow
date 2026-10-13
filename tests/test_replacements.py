"""Tests de compile_rules y apply_replacements: funciones puras, sin audio ni GPU."""
import pytest

from speechflow.replacements import apply_replacements, compile_rules


def aplicar(texto, *pares):
    return apply_replacements(texto, compile_rules(pares))


class TestApplyReplacements:
    def test_sustitucion_simple(self):
        assert aplicar("sube a Git hub", ("git ?hub", "GitHub")) == "sube a GitHub"

    @pytest.mark.parametrize("texto", ["sube a git hub", "sube a GIT HUB", "sube a gitHub"])
    def test_sin_distinguir_mayusculas(self, texto):
        assert aplicar(texto, ("git ?hub", "GitHub")) == "sube a GitHub"

    def test_referencia_numerica(self):
        assert aplicar("subió 20 por ciento", (r"(\d+) por ciento", r"\1 %")) == "subió 20 %"

    def test_referencia_con_nombre(self):
        regla = (r"(?P<n>\d+) por ciento", r"\g<n> %")
        assert aplicar("subió 20 por ciento", regla) == "subió 20 %"

    def test_orden_secuencial(self):
        assert aplicar("a", ("a", "b"), ("b", "c")) == "c"
        assert aplicar("a", ("b", "c"), ("a", "b")) == "b"

    def test_sin_coincidencias_queda_intacto(self):
        assert aplicar("hola mundo", ("git ?hub", "GitHub")) == "hola mundo"

    def test_sin_reglas(self):
        assert apply_replacements("hola", ()) == "hola"

    def test_resultado_con_strip(self):
        assert aplicar("  hola eh  ", ("eh+", "")) == "hola"

    def test_puede_dejar_texto_vacio(self):
        assert aplicar("eh eh", ("eh+", ""), (" +", "")) == ""


class TestCompileRules:
    def test_devuelve_tupla_de_patrones_compilados(self):
        reglas = compile_rules([("a", "b")])
        assert isinstance(reglas, tuple)
        assert reglas[0][0].pattern == "a" and reglas[0][1] == "b"

    def test_regex_que_no_compila(self):
        with pytest.raises(ValueError, match="regex inválida"):
            compile_rules([("(", "x")])

    def test_grupo_inexistente_en_el_reemplazo(self):
        with pytest.raises(ValueError, match="reemplazo inválido"):
            compile_rules([("a", r"\1")])

    def test_patron_que_coincide_con_vacio(self):
        with pytest.raises(ValueError, match="cadena vacía"):
            compile_rules([("x*", "y")])
