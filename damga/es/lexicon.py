"""Spanish word lists shared by the grammars and the streaming wrapper.

Pure data, no pynini import: the streaming normalizer and the native runtime load this module
without the grammar toolchain installed.
"""
from __future__ import annotations

import re

from ..core.unicode import Casing

DIGITS: list[tuple[str, str]] = [("uno", "1"), ("dos", "2"), ("tres", "3"), ("cuatro", "4"), ("cinco", "5"),
                                 ("seis", "6"), ("siete", "7"), ("ocho", "8"), ("nueve", "9")]
TEENS: list[tuple[str, str]] = [("diez", "10"), ("once", "11"), ("doce", "12"), ("trece", "13"), ("catorce", "14"),
                                ("quince", "15"), ("dieciséis", "16"), ("diecisiete", "17"), ("dieciocho", "18"),
                                ("diecinueve", "19")]
TWENTIES: list[tuple[str, str]] = [("veinte", "20"), ("veintiuno", "21"), ("veintidós", "22"), ("veintitrés", "23"),
                                   ("veinticuatro", "24"), ("veinticinco", "25"), ("veintiséis", "26"),
                                   ("veintisiete", "27"), ("veintiocho", "28"), ("veintinueve", "29")]
TIES: list[tuple[str, str]] = [("treinta", "3"), ("cuarenta", "4"), ("cincuenta", "5"), ("sesenta", "6"),
                               ("setenta", "7"), ("ochenta", "8"), ("noventa", "9")]
HUNDREDS: list[tuple[str, str]] = [("ciento", "1"), ("doscientos", "2"), ("trescientos", "3"), ("cuatrocientos", "4"),
                                   ("quinientos", "5"), ("seiscientos", "6"), ("setecientos", "7"),
                                   ("ochocientos", "8"), ("novecientos", "9")]
ZERO = "cero"

ORDINALS: list[tuple[str, str]] = [
    ("primero", "1"), ("segundo", "2"), ("tercero", "3"), ("cuarto", "4"), ("quinto", "5"), ("sexto", "6"),
    ("séptimo", "7"), ("octavo", "8"), ("noveno", "9"), ("décimo", "10"), ("undécimo", "11"), ("duodécimo", "12"),
    ("decimotercero", "13"), ("decimocuarto", "14"), ("decimoquinto", "15"), ("decimosexto", "16"),
    ("decimoséptimo", "17"), ("decimoctavo", "18"), ("decimonoveno", "19"), ("vigésimo", "20"),
]
ORDINAL_TENS: list[tuple[str, str]] = [("vigésimo", "2"), ("trigésimo", "3"), ("cuadragésimo", "4"),
                                       ("quincuagésimo", "5"), ("sexagésimo", "6"), ("septuagésimo", "7"),
                                       ("octogésimo", "8"), ("nonagésimo", "9")]
ORDINAL_UNITS = ORDINALS[:9]

NUMBER_WORDS: list[str] = ([ZERO, "un", "una", "y", "cien", "mil", "millón", "millones", "billón", "billones"]
                           + [w for w, _ in DIGITS + TEENS + TWENTIES + TIES + HUNDREDS]
                           + ["veintiún", "veintiuna", "doscientas", "trescientas", "cuatrocientas", "quinientas",
                              "seiscientas", "setecientas", "ochocientas", "novecientas", "coma", "punto", "menos",
                              "más"])

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]
CURRENCY_WORDS = ["euro", "euros", "céntimo", "céntimos", "dólar", "dólares", "libra", "libras", "centavos"]
UNIT_WORDS = ["por", "ciento", "kilómetros", "metros", "kilos", "kilogramos", "toneladas", "litros", "grados",
              "horas", "minutos", "hectáreas"]
SEPARATOR_WORDS = ["arroba", "punto", "guion", "barra"]

CASING = Casing(
    lower=str.lower,
    upper=str.upper,
    caps=re.compile(r"^([^\w]*)([A-ZÁÉÍÓÚÑÜ]{1,3})([^\w]*)$"),
    caps_lower=frozenset({"A", "Y", "O", "E", "U", "EL", "LA", "LOS", "LAS", "DE", "DEL", "EN", "UN", "UNA", "ES",
                          "SE", "NO", "SI", "SÍ", "YA", "QUE", "POR", "CON", "SIN", "MÁS", "LO", "LE", "MI", "TU", "SU"}),
)

STREAMING_TURKISH_SUFFIXES = False
STREAMING_CONTINUATION: frozenset[str] = frozenset(
    NUMBER_WORDS + MONTHS + CURRENCY_WORDS + SEPARATOR_WORDS + [w for w, _ in ORDINALS]
    + ["media", "cuarto", "horas"]
)
STREAMING_ATTACH_NEXT: frozenset[str] = frozenset(
    CURRENCY_WORDS + UNIT_WORDS + SEPARATOR_WORDS
    + ["mil", "millón", "millones", "y", "coma", "punto", "ciento", "media", "cuarto"]
)

# Pre-hook marks (TN): a feminine number, a number before its noun.  Here so the run time needs no pynini.
FEMININE = "⁤"
BEFORE_NOUN = "⁢"

# Punctuation tokens: the shared set plus the opening ¿ ¡, the « » quotes, typographic quotes and dashes.
MARKS = '.,;:!?()[]…¿¡«»“”‘’—–'
_AFTER_OPEN = re.compile(r"([¿¡«“‘]) +")
_BEFORE_CLOSE = re.compile(r" +([»”’])")


def reattach(text: str) -> str:
    """``« dos mil »`` → ``«dos mil»``, ``¿ cuántos?`` → ``¿cuántos?``: Spanish marks that hug the word."""
    return _BEFORE_CLOSE.sub(r"\1", _AFTER_OPEN.sub(r"\1", text))
