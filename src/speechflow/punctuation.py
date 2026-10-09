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
_CAPITALIZE_AFTER = {".", "?", "!", "\n", "\n\n"}
# Signos cuyo comando absorbe la puntuación final que Whisper pega a la palabra anterior.
_TRAILING = ".,;:!?…"


def _normalize(word: str) -> str:
    """Minúscula y sin signos en los extremos (`Punto.` -> `punto`)."""
    return word.lower().strip("".join(c for c in word if not c.isalnum()))


def _capitalize(word: str) -> str:
    """Pone en mayúscula la primera letra de `word`, si tiene alguna."""
    for i, c in enumerate(word):
        if c.isalpha():
            return word[:i] + c.upper() + word[i + 1 :]
    return word


def apply_voice_punctuation(text: str, language: str) -> str:
    """Sustituye los comandos de voz de `language` (es/en) por su signo y ajusta espacios y mayúsculas.

    Con otro idioma devuelve `text` sin cambios.
    """
    commands = COMMANDS.get(language)
    if not commands or not text:
        return text
    longest = max(len(phrase) for phrase in commands)
    escape = ESCAPE_WORDS[language]
    words = text.split()
    norm = [_normalize(w) for w in words]

    def match(i: int) -> tuple[str, tuple[str, ...]] | None:
        """Comando más largo que empieza en `i`: (símbolo, frase)."""
        for n in range(min(longest, len(words) - i), 0, -1):
            phrase = tuple(norm[i : i + n])
            if phrase in commands:
                return commands[phrase], phrase
        return None

    out = ""
    glued = True  # el siguiente elemento va pegado al anterior (inicio o tras un signo de apertura)
    prev_is_word = False
    capital = True  # mayúscula pendiente: inicio del texto y tras . ? ! y saltos
    i = 0
    while i < len(words):
        found = match(i)
        if found:
            symbol, phrase = found
            opening = phrase in _OPENING_QUOTES
            closing = symbol == '"' and not opening
            no_before = symbol in _NO_SPACE_BEFORE or closing
            no_after = symbol in _NO_SPACE_AFTER or opening
            if prev_is_word and symbol in (".", ",", ";", ":", "?", "!", "..."):
                out = out.rstrip(_TRAILING)
            i += len(phrase)
            out += symbol if glued or no_before else " " + symbol
            glued = no_after
            prev_is_word = False
            if symbol in _CAPITALIZE_AFTER:
                capital = True
            continue
        if norm[i] == escape and match(i + 1):
            i += 1  # el escape se descarta y la palabra siguiente va como texto normal
        word = words[i]
        i += 1
        if capital:
            capital = not any(c.isalpha() for c in word)  # sin letras, la mayúscula sigue pendiente
            word = _capitalize(word)
        out += word if glued else " " + word
        glued = False
        prev_is_word = True
    return out
