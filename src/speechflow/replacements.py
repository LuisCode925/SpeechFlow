"""Diccionario de reemplazos: corrige el texto dictado con expresiones regulares."""
import re
from collections.abc import Iterable

Rule = tuple[re.Pattern[str], str]  # (patrón compilado con IGNORECASE, reemplazo)


def compile_rules(pairs: Iterable[tuple[str, str]]) -> tuple[Rule, ...]:
    """Compila pares (patrón, reemplazo); ValueError con la causa si alguno no es válido."""
    rules = []
    for pattern, replacement in pairs:
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            raise ValueError(f"regex inválida: {exc}") from exc
        try:
            # Valida las referencias (\1, \g<nombre>) contra el patrón; sub() no expande sin coincidencia.
            re._parser.parse_template(replacement, compiled)
        except re.error as exc:
            raise ValueError(f"reemplazo inválido: {exc}") from exc
        if compiled.search(""):
            raise ValueError("el patrón coincide con la cadena vacía")
        rules.append((compiled, replacement))
    return tuple(rules)


def apply_replacements(text: str, rules: Iterable[Rule]) -> str:
    """Aplica las reglas en orden (cada una ve la salida de la anterior) y recorta el resultado."""
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
    return text.strip()
