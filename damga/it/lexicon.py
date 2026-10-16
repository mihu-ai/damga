"""Italian word lists shared by the grammars and the streaming wrapper.

Pure data, no pynini import: the streaming normalizer and the native runtime load this module
without the grammar toolchain installed.
"""
from __future__ import annotations

import re

from ..core.unicode import Casing

UNITS: list[tuple[str, str]] = [("uno", "1"), ("due", "2"), ("tre", "3"), ("quattro", "4"), ("cinque", "5"),
                                ("sei", "6"), ("sette", "7"), ("otto", "8"), ("nove", "9")]
TEENS: list[tuple[str, str]] = [("dieci", "10"), ("undici", "11"), ("dodici", "12"), ("tredici", "13"),
                                ("quattordici", "14"), ("quindici", "15"), ("sedici", "16"), ("diciassette", "17"),
                                ("diciotto", "18"), ("diciannove", "19")]
TENS: list[tuple[str, str]] = [("venti", "2"), ("trenta", "3"), ("quaranta", "4"), ("cinquanta", "5"),
                               ("sessanta", "6"), ("settanta", "7"), ("ottanta", "8"), ("novanta", "9")]
ZERO = "zero"
QUANTITY_WORDS = ["milione", "milioni", "miliardo", "miliardi"]

ORDINAL_UNITS: list[tuple[str, str]] = [("primo", "1"), ("secondo", "2"), ("terzo", "3"), ("quarto", "4"),
                                        ("quinto", "5"), ("sesto", "6"), ("settimo", "7"), ("ottavo", "8"),
                                        ("nono", "9"), ("decimo", "10")]

MONTHS = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre",
          "novembre", "dicembre"]

NUMBER_WORDS: list[str] = ([ZERO, "un", "una", "e", "cento", "mille", "mila", "virgola", "meno", "più"]
                           + [w for w, _ in UNITS + TEENS + TENS] + QUANTITY_WORDS)
# A spoken number is written as one word (duemilasedici, ventitré): it is a run of these pieces.
_NUMBER_PIECES = sorted({w for w, _ in UNITS + TEENS + TENS} | {w[:-1] for w, _ in TENS}
                        | {"un", "una", "tré", "cento", "mille", "mila", "milione", "milioni", "miliardo", "miliardi"},
                        key=len, reverse=True)
_NUMBER_WORD = re.compile("(?:" + "|".join(_NUMBER_PIECES) + ")+")


def is_number_word(word: str) -> bool:
    """A number said in words (``ventitré``, ``cinque``); ``zero`` is left out, it is matched against a leading ``0``."""
    return word != ZERO and _NUMBER_WORD.fullmatch(word) is not None


CURRENCY_WORDS = ["euro", "dollari", "dollaro", "sterline", "sterlina", "centesimi", "centesimo", "franchi"]
UNIT_WORDS = ["percento", "per", "cento", "chilometri", "metri", "chili", "chilogrammi", "tonnellate", "ettari",
              "litri", "gradi", "ore", "minuti"]
SEPARATOR_WORDS = ["punto", "chiocciola", "trattino", "barra"]

# Articles and short words written in capitals inside a word in capitals are words, not acronyms.
CASING = Casing(
    lower=str.lower,
    upper=str.upper,
    caps=re.compile(r"^([^\w]*)([A-Z]{1,3})([^\w]*)$"),
    caps_lower=frozenset({"E", "A", "I", "O", "IL", "LA", "LO", "LE", "GLI", "DI", "DA", "IN", "UN", "CHE", "NON",
                          "PER", "CON", "SU", "DEL", "AL", "MA", "SE", "NE", "CI", "MI", "TI", "VI", "HA", "HO"}),
)

# Streaming commit policy (see docs/streaming.md).
STREAMING_TURKISH_SUFFIXES = False
STREAMING_CONTINUATION: frozenset[str] = frozenset(
    NUMBER_WORDS + MONTHS + CURRENCY_WORDS + SEPARATOR_WORDS + [w for w, _ in ORDINAL_UNITS]
    + ["mezzo", "mezza", "quarto", "alle"]
)
STREAMING_ATTACH_NEXT: frozenset[str] = frozenset(
    CURRENCY_WORDS + UNIT_WORDS + SEPARATOR_WORDS + QUANTITY_WORDS + ["virgola", "e", "mezzo", "mezza"]
)
