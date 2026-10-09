"""Comandos de voz de puntuación: sustituye palabras dictadas ("punto", "coma"...) por su signo."""

# idioma -> frase (tupla de palabras en minúscula, sin signos) -> texto que la sustituye
COMMANDS: dict[str, dict[tuple[str, ...], str]] = {
    "es": {
        ("punto",): ".",
        ("coma",): ",",
        ("punto", "y", "coma"): ";",
        ("dos", "puntos"): ":",
        ("interrogación",): "?",
        ("cerrar", "interrogación"): "?",
        ("abrir", "interrogación"): "¿",
        ("exclamación",): "!",
        ("cerrar", "exclamación"): "!",
        ("abrir", "exclamación"): "¡",
        ("puntos", "suspensivos"): "...",
        ("nueva", "línea"): "\n",
        ("nuevo", "párrafo"): "\n\n",
        ("abrir", "paréntesis"): "(",
        ("cerrar", "paréntesis"): ")",
        ("abrir", "comillas"): '"',
        ("cerrar", "comillas"): '"',
        ("guion",): "-",
    },
    "en": {
        ("period",): ".",
        ("comma",): ",",
        ("semicolon",): ";",
        ("colon",): ":",
        ("question", "mark"): "?",
        ("exclamation", "mark"): "!",
        ("ellipsis",): "...",
        ("new", "line"): "\n",
        ("new", "paragraph"): "\n\n",
        ("open", "parenthesis"): "(",
        ("close", "parenthesis"): ")",
        ("open", "quote"): '"',
        ("close", "quote"): '"',
        ("dash",): "-",
    },
}
ESCAPE_WORDS = {"es": "literal", "en": "literally"}

# Las comillas comparten símbolo; apertura y cierre se distinguen por la frase.
_OPENING_QUOTES = {("abrir", "comillas"), ("open", "quote")}
_NO_SPACE_BEFORE = {".", ",", ";", ":", "?", "!", "...", ")", "\n", "\n\n"}
_NO_SPACE_AFTER = {"¿", "¡", "(", "\n", "\n\n"}


def apply_voice_punctuation(text: str, language: str) -> str:
    """Sustituye los comandos de voz de `language` (es/en) por su signo y ajusta los espacios.

    Con otro idioma devuelve `text` sin cambios.
    """
    commands = COMMANDS.get(language)
    if not commands or not text:
        return text
    longest = max(len(phrase) for phrase in commands)
    words = text.split()
    out = ""
    glued = True  # no hay que separar el siguiente elemento del anterior (inicio o tras un signo de apertura)
    i = 0
    while i < len(words):
        for n in range(min(longest, len(words) - i), 0, -1):
            phrase = tuple(w.lower() for w in words[i : i + n])
            if phrase in commands:
                symbol = commands[phrase]
                opening = phrase in _OPENING_QUOTES
                closing = symbol == '"' and not opening
                no_before = symbol in _NO_SPACE_BEFORE or closing
                no_after = symbol in _NO_SPACE_AFTER or opening
                i += n
                break
        else:
            symbol, no_before, no_after = words[i], False, False
            i += 1
        out += symbol if glued or no_before else " " + symbol
        glued = no_after
    return out
