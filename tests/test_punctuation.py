"""Tests de apply_voice_punctuation: función pura, sin audio ni GPU."""
import pytest

from speechflow.punctuation import apply_voice_punctuation


class TestEspanol:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("hola coma mundo punto", "Hola, mundo."),
            ("hola punto adiós", "Hola. Adiós"),
            ("uno punto y coma dos", "Uno; dos"),
            ("hola dos puntos", "Hola:"),
            ("hola puntos suspensivos", "Hola..."),
            ("abrir interrogación cómo estás cerrar interrogación", "¿Cómo estás?"),
            ("abrir exclamación hola cerrar exclamación", "¡Hola!"),
            ("hola interrogación", "Hola?"),
            ("hola exclamación", "Hola!"),
            ("hola nueva línea adiós", "Hola\nAdiós"),
            ("hola nuevo párrafo adiós", "Hola\n\nAdiós"),
            ("abrir paréntesis hola cerrar paréntesis", "(Hola)"),
            ("dijo abrir comillas hola cerrar comillas ayer", 'Dijo "hola" ayer'),
            ("uno guion dos", "Uno - dos"),
        ],
    )
    def test_tabla(self, texto, esperado):
        assert apply_voice_punctuation(texto, "es") == esperado

    def test_frase_mas_larga_gana(self):
        assert apply_voice_punctuation("uno punto y coma dos", "es") == "Uno; dos"
        assert apply_voice_punctuation("uno punto y dos", "es") == "Uno. Y dos"
        assert apply_voice_punctuation("uno dos puntos dos", "es") == "Uno: dos"
        assert apply_voice_punctuation("uno puntos suspensivos dos", "es") == "Uno... dos"

    def test_comillas_de_cierre_sin_apertura(self):
        assert apply_voice_punctuation("hola cerrar comillas", "es") == 'Hola"'

    def test_sin_comandos_solo_mayuscula_inicial(self):
        assert apply_voice_punctuation("hola Mundo cruel", "es") == "Hola Mundo cruel"


class TestNormalizacion:
    def test_puntuacion_de_whisper_no_se_duplica(self):
        assert apply_voice_punctuation("Hola, coma, mundo, punto.", "es") == "Hola, mundo."

    def test_comando_con_mayusculas_y_puntuacion_pegada(self):
        assert apply_voice_punctuation("Hola Punto. adiós", "es") == "Hola. Adiós"
        assert apply_voice_punctuation("hola Coma, mundo", "es") == "Hola, mundo"

    def test_frase_con_puntuacion_interna(self):
        assert apply_voice_punctuation("hola Nueva, línea. adiós", "es") == "Hola\nAdiós"

    def test_puntuacion_anterior_solo_se_quita_con_signos_de_puntuacion(self):
        assert apply_voice_punctuation("Hola, nueva línea adiós", "es") == "Hola,\nAdiós"

    def test_puntuacion_anterior_solo_de_la_palabra_inmediata(self):
        assert apply_voice_punctuation("Hola. Qué tal, coma", "es") == "Hola. Qué tal,"

    def test_dos_comandos_seguidos_no_borran_el_signo_anterior(self):
        assert apply_voice_punctuation("hola coma punto", "es") == "Hola,."


class TestMayusculas:
    def test_tras_salto_de_linea(self):
        assert apply_voice_punctuation("uno nueva línea dos", "es") == "Uno\nDos"

    def test_no_tras_coma_ni_dos_puntos(self):
        assert apply_voice_punctuation("uno coma dos dos puntos tres", "es") == "Uno, dos: tres"

    def test_atraviesa_signos_de_apertura(self):
        assert apply_voice_punctuation("hola punto abrir comillas adiós cerrar comillas", "es") == 'Hola. "Adiós"'
        assert apply_voice_punctuation("hola punto abrir paréntesis adiós cerrar paréntesis", "es") == "Hola. (Adiós)"

    def test_no_tras_puntos_suspensivos(self):
        assert apply_voice_punctuation("hola puntos suspensivos adiós", "es") == "Hola... adiós"

    def test_pendiente_atraviesa_palabra_sin_letras(self):
        assert apply_voice_punctuation("punto 123 adiós", "es") == ". 123 Adiós"


class TestEscape:
    def test_literal_deja_el_comando_como_palabra(self):
        assert apply_voice_punctuation("un literal punto de vista", "es") == "Un punto de vista"

    def test_literal_sin_comando_se_conserva(self):
        assert apply_voice_punctuation("literal mente", "es") == "Literal mente"
        assert apply_voice_punctuation("hola literal", "es") == "Hola literal"

    def test_literal_solo_afecta_a_una_palabra(self):
        assert apply_voice_punctuation("literal punto y coma", "es") == "Punto y,"

    def test_literal_con_mayuscula_y_puntuacion(self):
        assert apply_voice_punctuation("un Literal, coma", "es") == "Un coma"

    def test_literally_en_ingles(self):
        assert apply_voice_punctuation("a literally period of time", "en") == "A period of time"


class TestIngles:
    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("hello comma world period", "Hello, world."),
            ("one semicolon two", "One; two"),
            ("note colon yes", "Note: yes"),
            ("really question mark", "Really?"),
            ("wow exclamation mark", "Wow!"),
            ("wait ellipsis", "Wait..."),
            ("hi new line there", "Hi\nThere"),
            ("hi new paragraph there", "Hi\n\nThere"),
            ("open parenthesis hi close parenthesis", "(Hi)"),
            ("he said open quote hi close quote today", 'He said "hi" today'),
            ("one dash two", "One - two"),
            ("hi period there", "Hi. There"),
        ],
    )
    def test_tabla(self, texto, esperado):
        assert apply_voice_punctuation(texto, "en") == esperado

    def test_vocabulario_es_no_aplica_en_ingles(self):
        assert apply_voice_punctuation("hola punto", "en") == "Hola punto"


class TestIdiomaYVacio:
    @pytest.mark.parametrize("idioma", ["fr", "de", "", "ES"])
    def test_otro_idioma_no_se_toca(self, idioma):
        assert apply_voice_punctuation("hola punto adiós", idioma) == "hola punto adiós"

    def test_texto_vacio(self):
        assert apply_voice_punctuation("", "es") == ""

    def test_solo_comandos(self):
        assert apply_voice_punctuation("punto", "es") == "."
        assert apply_voice_punctuation("nueva línea", "es") == "\n"
        assert apply_voice_punctuation("coma punto", "es") == ",."
