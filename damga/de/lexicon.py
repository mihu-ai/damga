"""German word lists shared by the grammars and the streaming wrapper.

Pure data, no pynini import: the streaming normalizer and the native runtime load this module
without the grammar toolchain installed.
"""
from __future__ import annotations

import re

from ..core.unicode import Casing

# digit → the form used inside a compound (ein-, zwei-, …); a number that ends in 1 alone says "eins"
DIGITS: list[tuple[str, str]] = [("ein", "1"), ("zwei", "2"), ("drei", "3"), ("vier", "4"), ("fünf", "5"),
                                 ("sechs", "6"), ("sieben", "7"), ("acht", "8"), ("neun", "9")]
TEENS: list[tuple[str, str]] = [("zehn", "10"), ("elf", "11"), ("zwölf", "12"), ("dreizehn", "13"),
                                ("vierzehn", "14"), ("fünfzehn", "15"), ("sechzehn", "16"), ("siebzehn", "17"),
                                ("achtzehn", "18"), ("neunzehn", "19")]
TIES: list[tuple[str, str]] = [("zwanzig", "2"), ("dreißig", "3"), ("vierzig", "4"), ("fünfzig", "5"),
                               ("sechzig", "6"), ("siebzig", "7"), ("achtzig", "8"), ("neunzig", "9")]
ZERO = "null"
# (singular, plural) of the scale words written apart from the number
BIG_SCALES: list[tuple[str, str]] = [("Million", "Millionen"), ("Milliarde", "Milliarden"), ("Billion", "Billionen"),
                                     ("Billiarde", "Billiarden")]

MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
          "Dezember"]

NUMBER_WORDS: list[str] = ([ZERO, "eins", "zwo", "hundert", "tausend", "komma", "minus", "plus"]
                           + [w for w, _ in DIGITS + TEENS + TIES]
                           + [w.lower() for s in BIG_SCALES for w in s])

CURRENCY_WORDS = ["euro", "cent", "dollar", "pfund", "franken"]
UNIT_WORDS = ["prozent", "kilometer", "meter", "kilogramm", "tonnen", "hektar", "liter", "grad", "uhr", "stunden"]
SEPARATOR_WORDS = ["punkt", "at", "ät", "unterstrich", "bindestrich", "schrägstrich"]

# Lower-casing before the grammars is undone afterwards (preserve_case); short all-capital tokens are acronyms.
CASING = Casing(
    lower=str.lower,
    upper=str.upper,
    caps=re.compile(r"^([^\w]*)([A-ZÄÖÜ]{1,3})([^\w]*)$"),
    caps_lower=frozenset({"A", "I", "O", "U", "DIE", "DER", "DAS", "UND", "IN", "AN", "AM", "IM", "ZU", "ES", "ER",
                          "SIE", "WIR", "IST"}),
)

# Streaming commit policy (see docs/streaming.md).
STREAMING_TURKISH_SUFFIXES = False
STREAMING_CONTINUATION: frozenset[str] = frozenset(
    NUMBER_WORDS + [m.lower() for m in MONTHS] + CURRENCY_WORDS + SEPARATOR_WORDS + ["uhr"]
)
STREAMING_ATTACH_NEXT: frozenset[str] = frozenset(
    CURRENCY_WORDS + UNIT_WORDS + SEPARATOR_WORDS + ["komma", "uhr", "millionen", "milliarden", "million", "milliarde"]
)

# Pre-hook mark (TN): a four-digit number that is a count, not a year.  Here so the run time needs no pynini.
NOT_YEAR = "⁣"

# Country codes are prefix-free (ITU E.164), so a glued "+493012345678" splits in one way only.
COUNTRY_CODES: tuple[str, ...] = (
    "1", "7", "20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41", "43", "44", "45", "46", "47", "48",
    "49", "90", "351", "352", "353", "358", "359", "370", "371", "372", "380", "381", "385", "386", "420", "421",
)
# German area codes without the trunk "0" (also prefix-free)
AREA_CODES: tuple[str, ...] = (
    "30", "40", "69", "89",
    "201", "202", "203", "208", "209", "211", "212", "221", "228", "231", "234", "241", "251", "261", "271", "331",
    "335", "340", "341", "345", "351", "355", "361", "365", "371", "381", "385", "391", "395", "421", "431", "441",
    "451", "461", "471", "481", "511", "521", "531", "541", "551", "561", "611", "621", "631", "641", "651", "661",
    "681", "711", "721", "731", "751", "761", "821", "831", "841", "851", "871", "911", "921", "931", "941", "951",
)
MOBILE_PREFIXES: tuple[str, ...] = ("15", "16", "17")      # + one digit: 0151, 0160, 0171, 0176 …
