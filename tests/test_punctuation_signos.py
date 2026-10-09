"""Casos de apply_voice_punctuation organizados por signo (SPEC 21).

Cada clase cubre un signo con cuatro grupos de casos:
  - COMANDO: el dictado de la tabla de la spec, en es y en.
  - WHISPER: cómo suele devolver Whisper el comando (mayúsculas, puntuación pegada, coma antes).
  - NO_COMANDO: palabras parecidas que NO deben sustituirse (falsos positivos).
  - ESCAPE: `literal` / `literally` para dejar el comando como palabra.
Al final, `TestLimitacionesConocidas` recoge los fallos de reconocimiento que la spec deja fuera
(tildes omitidas, guiones, numerales...). Van como xfail estricto: si alguna spec futura los arregla,
el test pasa a XPASS y falla, avisando de que hay que quitar la marca.
"""
import pytest

from speechflow.punctuation import apply_voice_punctuation


def aplica(idioma, texto, esperado):
    assert apply_voice_punctuation(texto, idioma) == esperado


def casos(idioma, tabla):
    return [pytest.param(idioma, texto, esperado, id=f"{idioma}:{texto!r}") for texto, esperado in tabla]


def parametrizar(*grupos):
    return pytest.mark.parametrize("idioma, texto, esperado", [c for grupo in grupos for c in grupo])


# --------------------------------------------------------------------------- .
class TestPunto:
    @parametrizar(
        casos("es", [
            ("punto", "."),
            ("hola punto", "Hola."),
            ("hola punto adiós", "Hola. Adiós"),
            ("hola punto y aparte", "Hola. Y aparte"),
            ("uno punto dos punto", "Uno. Dos."),
        ]),
        casos("en", [
            ("period", "."),
            ("hello period", "Hello."),
            ("hello period bye", "Hello. Bye"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Hola punto.", "Hola."),
            ("Hola, punto.", "Hola."),
            ("HOLA PUNTO", "HOLA."),
            ("hola Punto, adiós", "Hola. Adiós"),
            ("hola punto. adiós", "Hola. Adiós"),
            ("hola. punto", "Hola."),
            ("hola punto punto", "Hola.."),
        ]),
        casos("en", [
            ("Hello, period.", "Hello."),
            ("hello Period, bye", "Hello. Bye"),
        ]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("los puntos de la lista", "Los puntos de la lista"),
            ("puntocom", "Puntocom"),
            ("puntuación", "Puntuación"),
            ("el puntero", "El puntero"),
        ]),
        casos("en", [
            ("periodic table", "Periodic table"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("un literal punto de vista", "Un punto de vista"),
            ("literal punto", "Punto"),
            ("Literal, punto", "Punto"),
        ]),
        casos("en", [
            ("a literally period of time", "A period of time"),
        ]),
    )
    def test_escape(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)


# --------------------------------------------------------------------------- ,
class TestComa:
    @parametrizar(
        casos("es", [
            ("coma", ","),
            ("hola coma mundo", "Hola, mundo"),
            ("uno coma dos coma tres", "Uno, dos, tres"),
        ]),
        casos("en", [
            ("comma", ","),
            ("hello comma world", "Hello, world"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Hola, coma, mundo", "Hola, mundo"),
            ("Hola, coma, mundo, punto.", "Hola, mundo."),
            ("hola Coma. mundo", "Hola, mundo"),
            ("hola COMA mundo", "Hola, mundo"),
            ("hola coma, mundo", "Hola, mundo"),
        ]),
        casos("en", [
            ("Hello, comma, world", "Hello, world"),
            ("hello Comma. world", "Hello, world"),
        ]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("las comas del texto", "Las comas del texto"),
            ("comando", "Comando"),
            ("comer", "Comer"),
        ]),
        casos("en", [
            ("commas and dots", "Commas and dots"),
            ("command", "Command"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [("la literal coma de la frase", "La coma de la frase")]),
        casos("en", [("the literally comma", "The comma")]),
    )
    def test_escape(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)


# --------------------------------------------------------------------------- ;
class TestPuntoYComa:
    @parametrizar(
        casos("es", [
            ("punto y coma", ";"),
            ("uno punto y coma dos", "Uno; dos"),
        ]),
        casos("en", [
            ("semicolon", ";"),
            ("one semicolon two", "One; two"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("uno Punto y coma, dos", "Uno; dos"),
            ("uno, punto y coma dos", "Uno; dos"),
            ("Uno. Punto y coma. Dos", "Uno; Dos"),
            ("uno PUNTO Y COMA dos", "Uno; dos"),
        ]),
        casos("en", [("one, semicolon. two", "One; two")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("uno punto y dos", "Uno. Y dos"),
            ("uno punto y", "Uno. Y"),
            ("uno punto coma dos", "Uno., Dos"),
            ("uno y coma dos", "Uno y, dos"),
        ]),
    )
    def test_no_confundir_con_punto_o_coma(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape_solo_afecta_a_una_palabra(self):
        aplica("es", "literal punto y coma", "Punto y,")


# --------------------------------------------------------------------------- :
class TestDosPuntos:
    @parametrizar(
        casos("es", [
            ("dos puntos", ":"),
            ("hola dos puntos", "Hola:"),
            ("hola dos puntos adiós", "Hola: adiós"),
        ]),
        casos("en", [
            ("colon", ":"),
            ("note colon yes", "Note: yes"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Hola, dos puntos.", "Hola:"),
            ("hola Dos Puntos, adiós", "Hola: adiós"),
        ]),
        casos("en", [("Note, colon. yes", "Note: yes")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("dos", "Dos"),
            ("dos personas", "Dos personas"),
            ("los puntos", "Los puntos"),
            ("dos punto", "Dos."),
        ]),
        casos("en", [("colony", "Colony")]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape_dos_puntos_de_ventaja(self):
        aplica("es", "tengo literal dos puntos de ventaja", "Tengo dos puntos de ventaja")

    def test_escape_ante_puntos_no_protege(self):
        # `literal` solo salva si lo que sigue empieza un comando; "puntos" suelto no lo es.
        aplica("es", "tengo dos literal puntos", "Tengo dos literal puntos")


# --------------------------------------------------------------------------- ...
class TestPuntosSuspensivos:
    @parametrizar(
        casos("es", [
            ("puntos suspensivos", "..."),
            ("hola puntos suspensivos", "Hola..."),
            ("hola puntos suspensivos adiós", "Hola... adiós"),
        ]),
        casos("en", [
            ("ellipsis", "..."),
            ("wait ellipsis", "Wait..."),
            ("wait ellipsis then", "Wait... then"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Hola, puntos suspensivos.", "Hola..."),
            ("hola Puntos Suspensivos, adiós", "Hola... adiós"),
        ]),
        casos("en", [("Wait, ellipsis.", "Wait...")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("puntos", "Puntos"),
            ("suspensivos", "Suspensivos"),
            ("suspenso", "Suspenso"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_gana_a_dos_puntos_y_a_punto(self):
        aplica("es", "uno puntos suspensivos dos", "Uno... dos")

    def test_no_pone_mayuscula_despues(self):
        aplica("es", "hola puntos suspensivos adiós", "Hola... adiós")


# --------------------------------------------------------------------------- ? ¿
class TestInterrogacion:
    @parametrizar(
        casos("es", [
            ("hola interrogación", "Hola?"),
            ("hola cerrar interrogación", "Hola?"),
            ("abrir interrogación", "¿"),
            ("abrir interrogación cómo estás cerrar interrogación", "¿Cómo estás?"),
            ("abrir interrogación qué hora es cerrar interrogación gracias", "¿Qué hora es? Gracias"),
        ]),
        casos("en", [
            ("question mark", "?"),
            ("really question mark", "Really?"),
            ("how are you question mark thanks", "How are you? Thanks"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Abrir interrogación, cómo estás, cerrar interrogación.", "¿Cómo estás?"),
            ("abrir interrogación cómo estás Cerrar Interrogación?", "¿Cómo estás?"),
            ("Hola, interrogación.", "Hola?"),
            ("ABRIR INTERROGACIÓN cómo CERRAR INTERROGACIÓN", "¿Cómo?"),
        ]),
        casos("en", [("Really, question mark?", "Really?")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("abrir", "Abrir"),
            ("cerrar", "Cerrar"),
            ("interrogatorio", "Interrogatorio"),
            ("una pregunta", "Una pregunta"),
        ]),
        casos("en", [
            ("question", "Question"),
            ("mark", "Mark"),
            ("a question for mark", "A question for mark"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape(self):
        aplica("es", "la literal interrogación", "La interrogación")

    def test_la_mayuscula_atraviesa_la_apertura(self):
        aplica("es", "hola punto abrir interrogación cómo estás cerrar interrogación", "Hola. ¿Cómo estás?")


# --------------------------------------------------------------------------- ! ¡
class TestExclamacion:
    @parametrizar(
        casos("es", [
            ("hola exclamación", "Hola!"),
            ("hola cerrar exclamación", "Hola!"),
            ("abrir exclamación", "¡"),
            ("abrir exclamación hola cerrar exclamación", "¡Hola!"),
            ("abrir exclamación hola cerrar exclamación adiós", "¡Hola! Adiós"),
        ]),
        casos("en", [
            ("exclamation mark", "!"),
            ("wow exclamation mark", "Wow!"),
            ("wow exclamation mark nice", "Wow! Nice"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Abrir exclamación, hola, cerrar exclamación.", "¡Hola!"),
            ("Hola, exclamación.", "Hola!"),
            ("HOLA EXCLAMACIÓN", "HOLA!"),
        ]),
        casos("en", [("Wow, exclamation mark!", "Wow!")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("exclamar", "Exclamar"),
            ("una exclamativa", "Una exclamativa"),
        ]),
        casos("en", [
            ("exclamation", "Exclamation"),
            ("exclamations", "Exclamations"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape(self):
        aplica("es", "la literal exclamación", "La exclamación")


# --------------------------------------------------------------------------- \n
class TestNuevaLinea:
    @parametrizar(
        casos("es", [
            ("nueva línea", "\n"),
            ("hola nueva línea adiós", "Hola\nAdiós"),
            ("hola nueva línea nueva línea adiós", "Hola\n\nAdiós"),
        ]),
        casos("en", [
            ("new line", "\n"),
            ("hi new line there", "Hi\nThere"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Hola. Nueva línea. Adiós", "Hola.\nAdiós"),
            ("hola, nueva línea, adiós", "Hola,\nAdiós"),
            ("hola NUEVA LÍNEA adiós", "Hola\nAdiós"),
            ("hola Nueva, línea. adiós", "Hola\nAdiós"),
        ]),
        casos("en", [("Hi. New line. There", "Hi.\nThere")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("una nueva casa", "Una nueva casa"),
            ("la línea recta", "La línea recta"),
            ("nueva", "Nueva"),
            ("línea", "Línea"),
            ("nueva cuenta", "Nueva cuenta"),
        ]),
        casos("en", [
            ("a new house", "A new house"),
            ("new", "New"),
            ("line", "Line"),
            ("online", "Online"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [("la literal nueva línea", "La nueva línea")]),
    )
    def test_escape(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_sin_espacios_alrededor_del_salto(self):
        resultado = apply_voice_punctuation("hola nueva línea adiós", "es")
        assert " \n" not in resultado and "\n " not in resultado

    def test_mayuscula_tras_salto(self):
        aplica("es", "uno nueva línea dos", "Uno\nDos")


# --------------------------------------------------------------------------- \n\n
class TestNuevoParrafo:
    @parametrizar(
        casos("es", [
            ("nuevo párrafo", "\n\n"),
            ("hola nuevo párrafo adiós", "Hola\n\nAdiós"),
        ]),
        casos("en", [
            ("new paragraph", "\n\n"),
            ("hi new paragraph there", "Hi\n\nThere"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Hola. Nuevo párrafo. Adiós", "Hola.\n\nAdiós"),
            ("hola NUEVO PÁRRAFO adiós", "Hola\n\nAdiós"),
            ("hola Nuevo, párrafo. adiós", "Hola\n\nAdiós"),
        ]),
        casos("en", [("Hi, new paragraph. There", "Hi,\n\nThere")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("un nuevo plan", "Un nuevo plan"),
            ("el párrafo", "El párrafo"),
            ("nuevo", "Nuevo"),
            ("párrafo", "Párrafo"),
        ]),
        casos("en", [
            ("a new plan", "A new plan"),
            ("paragraph", "Paragraph"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape(self):
        aplica("es", "el literal nuevo párrafo", "El nuevo párrafo")


# --------------------------------------------------------------------------- ( )
class TestParentesis:
    @parametrizar(
        casos("es", [
            ("abrir paréntesis", "("),
            ("cerrar paréntesis", ")"),
            ("abrir paréntesis hola cerrar paréntesis", "(Hola)"),
            ("dijo abrir paréntesis hola cerrar paréntesis ayer", "Dijo (hola) ayer"),
            ("hola abrir paréntesis nota cerrar paréntesis punto", "Hola (nota)."),
            ("hola cerrar paréntesis", "Hola)"),
        ]),
        casos("en", [
            ("open parenthesis", "("),
            ("close parenthesis", ")"),
            ("open parenthesis hi close parenthesis", "(Hi)"),
            ("said open parenthesis hi close parenthesis today", "Said (hi) today"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Abrir paréntesis, hola cerrar paréntesis.", "(Hola)"),
            ("ABRIR PARÉNTESIS hola CERRAR PARÉNTESIS", "(Hola)"),
            ("abrir paréntesis hola Cerrar paréntesis, adiós", "(Hola) adiós"),
        ]),
        casos("en", [("Open parenthesis, hi close parenthesis.", "(Hi)")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("abrir", "Abrir"),
            ("cerrar", "Cerrar"),
            ("el paréntesis", "El paréntesis"),
            ("abrir la puerta", "Abrir la puerta"),
            ("cerrar la puerta", "Cerrar la puerta"),
        ]),
        casos("en", [
            ("open", "Open"),
            ("close", "Close"),
            ("open the door", "Open the door"),
            ("the parenthesis", "The parenthesis"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape(self):
        aplica("es", "el literal abrir paréntesis", "El abrir paréntesis")

    def test_sin_espacio_tras_apertura_ni_antes_de_cierre(self):
        resultado = apply_voice_punctuation("abrir paréntesis hola cerrar paréntesis", "es")
        assert "( " not in resultado and " )" not in resultado


# --------------------------------------------------------------------------- "
class TestComillas:
    @parametrizar(
        casos("es", [
            ("abrir comillas hola cerrar comillas", '"Hola"'),
            ("dijo abrir comillas hola cerrar comillas ayer", 'Dijo "hola" ayer'),
            ("abrir comillas hola cerrar comillas punto", '"Hola".'),
            ("abrir comillas", '"'),
            ("cerrar comillas", '"'),
            ("hola cerrar comillas", 'Hola"'),
        ]),
        casos("en", [
            ("open quote hi close quote", '"Hi"'),
            ("he said open quote hi close quote today", 'He said "hi" today'),
            ("open quote", '"'),
            ("close quote", '"'),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("Abrir comillas, hola cerrar comillas.", '"Hola"'),
            ("ABRIR COMILLAS hola CERRAR COMILLAS", '"Hola"'),
            ("abrir comillas hola Cerrar comillas, adiós", '"Hola" adiós'),
        ]),
        casos("en", [("Open quote, hi close quote.", '"Hi"')]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("comillas", "Comillas"),
            ("las comillas", "Las comillas"),
            ("abrir", "Abrir"),
        ]),
        casos("en", [
            ("quote", "Quote"),
            ("a quote from him", "A quote from him"),
            ("open", "Open"),
            ("close", "Close"),
            ("close to me", "Close to me"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_escape(self):
        aplica("es", "las literal abrir comillas", "Las abrir comillas")

    def test_apertura_y_cierre_se_distinguen_por_la_frase(self):
        assert apply_voice_punctuation("abrir comillas", "es") == apply_voice_punctuation("cerrar comillas", "es") == '"'
        assert apply_voice_punctuation("a abrir comillas b", "es") == 'A "b'
        assert apply_voice_punctuation("a cerrar comillas b", "es") == 'A" b'

    def test_la_mayuscula_atraviesa_la_apertura(self):
        aplica("es", 'hola punto abrir comillas adiós cerrar comillas', 'Hola. "Adiós"')


# --------------------------------------------------------------------------- -
class TestGuion:
    @parametrizar(
        casos("es", [
            ("guion", "-"),
            ("uno guion dos", "Uno - dos"),
            ("uno guion dos guion tres", "Uno - dos - tres"),
        ]),
        casos("en", [
            ("dash", "-"),
            ("one dash two", "One - two"),
        ]),
    )
    def test_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("uno GUION dos", "Uno - dos"),
            ("uno guion, dos", "Uno - dos"),
            ("Uno, guion, dos", "Uno, - dos"),
        ]),
        casos("en", [("one Dash, two", "One - two")]),
    )
    def test_whisper(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [
            ("los guiones", "Los guiones"),
            ("un guionista", "Un guionista"),
        ]),
        casos("en", [
            ("dashboard", "Dashboard"),
            ("dashes", "Dashes"),
        ]),
    )
    def test_no_comando(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    @parametrizar(
        casos("es", [("el literal guion de la película", "El guion de la película")]),
        casos("en", [("a literally dash of salt", "A dash of salt")]),
    )
    def test_escape(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)

    def test_un_espacio_a_cada_lado(self):
        assert apply_voice_punctuation("uno guion dos", "es") == "Uno - dos"
        assert "  " not in apply_voice_punctuation("uno guion dos", "es")


# --------------------------------------------------------------------------- transversales
class TestMayusculas:
    @parametrizar(
        casos("es", [
            ("hola mundo", "Hola mundo"),
            ("hola Mundo cruel", "Hola Mundo cruel"),
            ("uno punto dos", "Uno. Dos"),
            ("uno interrogación dos", "Uno? Dos"),
            ("uno exclamación dos", "Uno! Dos"),
            ("uno nueva línea dos", "Uno\nDos"),
            ("uno nuevo párrafo dos", "Uno\n\nDos"),
            ("uno coma dos", "Uno, dos"),
            ("uno punto y coma dos", "Uno; dos"),
            ("uno dos puntos dos", "Uno: dos"),
            ("uno puntos suspensivos dos", "Uno... dos"),
            ("uno guion dos", "Uno - dos"),
            ("punto 123 adiós", ". 123 Adiós"),
            ("¿hola", "¿Hola"),
        ]),
    )
    def test_mayusculas(self, idioma, texto, esperado):
        aplica(idioma, texto, esperado)


class TestSinCambios:
    @pytest.mark.parametrize("idioma", ["fr", "de", "pt", "it", "", "ES", "auto"])
    def test_otro_idioma_no_se_toca(self, idioma):
        aplica(idioma, "hola punto adiós coma", "hola punto adiós coma")

    def test_idioma_sin_vocabulario_ni_siquiera_la_mayuscula(self):
        aplica("fr", "bonjour le monde", "bonjour le monde")

    @pytest.mark.parametrize("idioma", ["es", "en"])
    def test_texto_vacio(self, idioma):
        aplica(idioma, "", "")

    def test_vocabulario_de_un_idioma_no_vale_en_el_otro(self):
        aplica("en", "hola punto", "Hola punto")
        aplica("es", "hello period", "Hello period")


class TestEscapeGeneral:
    def test_literal_sin_comando_se_conserva(self):
        aplica("es", "literal mente", "Literal mente")
        aplica("es", "hola literal", "Hola literal")
        aplica("en", "hello literally", "Hello literally")

    def test_literal_solo_afecta_a_una_palabra(self):
        aplica("es", "literal punto y coma", "Punto y,")

    def test_doble_literal_no_escapa_el_literal(self):
        aplica("es", "literal literal punto", "Literal punto")

    def test_vocabulario_de_escape_por_idioma(self):
        aplica("en", "a literal period", "A literal.")
        aplica("es", "un literally punto", "Un literally.")


# --------------------------------------------------------------------------- fuera de la spec
class TestLimitacionesConocidas:
    """Fallos de reconocimiento que la spec 21 deja fuera. xfail estricto: documentan el hueco.

    La spec solo normaliza mayúsculas y puntuación pegada (sección Riesgos); tildes omitidas,
    grafías antiguas, guiones, numerales y coma pegada antes de un cierre se tratarían en una spec posterior.
    """

    def _xfail(razon):
        return pytest.mark.xfail(strict=True, reason=razon)

    @pytest.mark.parametrize(
        "texto, esperado",
        [
            pytest.param("hola interrogacion", "Hola?", id="sin-tilde:interrogacion"),
            pytest.param("hola exclamacion", "Hola!", id="sin-tilde:exclamacion"),
            pytest.param("hola nueva linea adiós", "Hola\nAdiós", id="sin-tilde:linea"),
            pytest.param("hola nuevo parrafo adiós", "Hola\n\nAdiós", id="sin-tilde:parrafo"),
            pytest.param("abrir parentesis hola cerrar parentesis", "(Hola)", id="sin-tilde:parentesis"),
            pytest.param("uno guión dos", "Uno - dos", id="grafia-antigua:guión"),
            pytest.param("hola puntó", "Hola.", id="acento-espurio:puntó"),
            pytest.param("2 puntos", ":", id="numeral:2-puntos"),
            pytest.param("uno punto-y-coma dos", "Uno; dos", id="guiones:punto-y-coma"),
            pytest.param("abrir comillas hola, cerrar comillas", '"Hola"', id="coma-pegada-antes-de-cierre:comillas"),
            pytest.param("abrir paréntesis hola, cerrar paréntesis", "(Hola)", id="coma-pegada-antes-de-cierre:paréntesis"),
            pytest.param("abrir interrogación dos puntos suspensivos", "¿...", id="ambiguo:dos-puntos-suspensivos"),
        ],
    )
    @_xfail("reconocimiento fuera de la spec 21")
    def test_es(self, texto, esperado):
        aplica("es", texto, esperado)

    @pytest.mark.parametrize(
        "texto, esperado",
        [
            pytest.param("hi new-line there", "Hi\nThere", id="guion:new-line"),
            pytest.param("hi newline there", "Hi\nThere", id="junto:newline"),
            pytest.param("open quote hi, close quote", '"Hi"', id="coma-pegada-antes-de-cierre:quote"),
            pytest.param("hello full stop", "Hello.", id="sinonimo:full-stop"),
        ],
    )
    @_xfail("reconocimiento fuera de la spec 21")
    def test_en(self, texto, esperado):
        aplica("en", texto, esperado)
