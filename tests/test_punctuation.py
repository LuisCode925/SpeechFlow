"""Tests de apply_voice_punctuation: función pura, sin audio ni GPU."""
import pytest

from speechflow.punctuation import apply_voice_punctuation


class TestEspanol:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("hola coma mundo punto", "hola, mundo."),
            ("uno punto y coma dos", "uno; dos"),
            ("hola dos puntos", "hola:"),
            ("hola puntos suspensivos", "hola..."),
            ("abrir interrogación cómo estás cerrar interrogación", "¿cómo estás?"),
            ("abrir exclamación hola cerrar exclamación", "¡hola!"),
            ("hola interrogación", "hola?"),
            ("hola exclamación", "hola!"),
            ("hola nueva línea adiós", "hola\nadiós"),
            ("hola nuevo párrafo adiós", "hola\n\nadiós"),
            ("abrir paréntesis hola cerrar paréntesis", "(hola)"),
            ("dijo abrir comillas hola cerrar comillas ayer", 'dijo "hola" ayer'),
            ("uno guion dos", "uno - dos"),
        ],
    )
    def test_tabla(self, texto, esperado):
        assert apply_voice_punctuation(texto, "es") == esperado

    def test_frase_mas_larga_gana(self):
        assert apply_voice_punctuation("uno punto y coma dos", "es") == "uno; dos"
        assert apply_voice_punctuation("uno punto y dos", "es") == "uno. y dos"

    def test_sin_comandos_no_cambia(self):
        assert apply_voice_punctuation("hola mundo", "es") == "hola mundo"


class TestIngles:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("hello comma world period", "hello, world."),
            ("one semicolon two", "one; two"),
            ("note colon yes", "note: yes"),
            ("really question mark", "really?"),
            ("wow exclamation mark", "wow!"),
            ("wait ellipsis", "wait..."),
            ("hi new line there", "hi\nthere"),
            ("hi new paragraph there", "hi\n\nthere"),
            ("open parenthesis hi close parenthesis", "(hi)"),
            ("he said open quote hi close quote today", 'he said "hi" today'),
            ("one dash two", "one - two"),
        ],
    )
    def test_tabla(self, texto, esperado):
        assert apply_voice_punctuation(texto, "en") == esperado

    def test_vocabulario_es_no_aplica_en_ingles(self):
        assert apply_voice_punctuation("hola punto", "en") == "hola punto"
