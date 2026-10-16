"""English word lists shared by the grammars and the streaming wrapper.

Pure data, no pynini import: the streaming normalizer and the native runtime load this module
without the grammar toolchain installed.
"""
from __future__ import annotations

import re

from ..core.unicode import Casing

DIGITS: list[tuple[str, str]] = [("one", "1"), ("two", "2"), ("three", "3"), ("four", "4"), ("five", "5"),
                                 ("six", "6"), ("seven", "7"), ("eight", "8"), ("nine", "9")]
TEENS: list[tuple[str, str]] = [("ten", "10"), ("eleven", "11"), ("twelve", "12"), ("thirteen", "13"),
                                ("fourteen", "14"), ("fifteen", "15"), ("sixteen", "16"), ("seventeen", "17"),
                                ("eighteen", "18"), ("nineteen", "19")]
TIES: list[tuple[str, str]] = [("twenty", "2"), ("thirty", "3"), ("forty", "4"), ("fifty", "5"), ("sixty", "6"),
                               ("seventy", "7"), ("eighty", "8"), ("ninety", "9")]
ZERO = "zero"
# Scale words of the short scale, each a group of three digits.
SCALES: list[str] = ["thousand", "million", "billion", "trillion"]
QUANTITY_WORDS = ["million", "billion", "trillion"]

ORDINAL_DIGITS: list[tuple[str, str]] = [("first", "1"), ("second", "2"), ("third", "3"), ("fourth", "4"),
                                         ("fifth", "5"), ("sixth", "6"), ("seventh", "7"), ("eighth", "8"),
                                         ("ninth", "9")]
ORDINAL_TEENS: list[tuple[str, str]] = [("tenth", "10"), ("eleventh", "11"), ("twelfth", "12"),
                                        ("thirteenth", "13"), ("fourteenth", "14"), ("fifteenth", "15"),
                                        ("sixteenth", "16"), ("seventeenth", "17"), ("eighteenth", "18"),
                                        ("nineteenth", "19")]
ORDINAL_TIES: list[tuple[str, str]] = [("twentieth", "2"), ("thirtieth", "3"), ("fortieth", "4"), ("fiftieth", "5"),
                                       ("sixtieth", "6"), ("seventieth", "7"), ("eightieth", "8"), ("ninetieth", "9")]

NUMBER_WORDS: list[str] = ([ZERO, "oh", "hundred", "a", "and"] + [w for w, _ in DIGITS + TEENS + TIES] + SCALES
                           + ["point", "minus", "plus"])

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
CURRENCY_WORDS = ["dollar", "dollars", "euro", "euros", "pound", "pounds", "cent", "cents", "pence", "penny", "yen",
                  "franc", "francs"]
UNIT_WORDS = ["percent", "per", "cent", "kilometres", "kilometers", "metres", "meters", "kilograms", "tonnes", "tons",
              "litres", "liters", "degrees", "hours", "minutes", "seconds"]
SEPARATOR_WORDS = ["dot", "at", "underscore", "dash", "hyphen", "slash"]

# Pronoun "I" and the article "A" are words, not acronyms: they are lower-cased like any other word.
CASING = Casing(
    lower=str.lower,
    upper=str.upper,
    caps=re.compile(r"^([^\w]*)([A-Z]{1,3})([^\w]*)$"),
    caps_lower=frozenset({"I", "A", "OK", "AM", "PM", "AN", "AT", "OF", "TO", "IN", "ON", "IS", "IT", "BE", "BY",
                          "OR", "AND", "THE", "FOR", "NOT"}),
)

# Streaming commit policy (see docs/streaming.md).
STREAMING_TURKISH_SUFFIXES = False
STREAMING_CONTINUATION: frozenset[str] = frozenset(
    NUMBER_WORDS + MONTHS + CURRENCY_WORDS + SEPARATOR_WORDS
    + [w for w, _ in ORDINAL_DIGITS + ORDINAL_TEENS + ORDINAL_TIES]
    + ["o'clock", "past", "quarter", "half", "double", "triple"]
)
STREAMING_ATTACH_NEXT: frozenset[str] = frozenset(
    CURRENCY_WORDS + UNIT_WORDS + SEPARATOR_WORDS + SCALES
    + ["hundred", "point", "o'clock", "percent", "cent", "and", "oh"]
)

# Pre-hook mark (TN): a four-digit number that is a count, not a year.  Here so the run time needs no pynini.
NOT_YEAR = "⁣"
