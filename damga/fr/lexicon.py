"""French word lists shared by the grammars and the streaming wrapper.

Pure data, no pynini import: the streaming normalizer and the native runtime load this module
without the grammar toolchain installed.
"""
from __future__ import annotations

import re

from ..core.unicode import Casing

UNITS: list[tuple[str, str]] = [("un", "1"), ("deux", "2"), ("trois", "3"), ("quatre", "4"), ("cinq", "5"),
                                ("six", "6"), ("sept", "7"), ("huit", "8"), ("neuf", "9")]
TEENS: list[tuple[str, str]] = [("dix", "10"), ("onze", "11"), ("douze", "12"), ("treize", "13"),
                                ("quatorze", "14"), ("quinze", "15"), ("seize", "16"), ("dix-sept", "17"),
                                ("dix-huit", "18"), ("dix-neuf", "19")]
# tens digit → word, 2..6 (70, 80 and 90 are built from soixante and quatre-vingt)
TIES: list[tuple[str, str]] = [("vingt", "2"), ("trente", "3"), ("quarante", "4"), ("cinquante", "5"),
                               ("soixante", "6")]
ZERO = "zéro"
QUANTITY_WORDS = ["million", "millions", "milliard", "milliards", "billion", "billions"]

NUMBER_WORDS: list[str] = ([ZERO, "et", "cent", "cents", "mille", "quatre-vingt", "quatre-vingts", "soixante-dix",
                            "septante", "huitante", "octante", "nonante", "virgule", "moins", "plus", "une"]
                           + [w for w, _ in UNITS + TEENS + TIES] + QUANTITY_WORDS)

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]
CURRENCY_WORDS = ["euro", "euros", "centime", "centimes", "dollar", "dollars", "livre", "livres", "franc", "francs"]
UNIT_WORDS = ["pour", "cent", "pourcent", "kilomètres", "mètres", "tonnes", "hectares", "degrés", "heures", "heure",
              "minutes", "kilos", "kilogrammes", "litres"]
SEPARATOR_WORDS = ["point", "arobase", "tiret", "slash"]

_UPPER = "A-ZÀÂÄÆÇÉÈÊËÎÏÔŒÙÛÜŸ"
# Short words written in capitals at the start of a shouted line are words, not acronyms.
CASING = Casing(
    lower=str.lower,
    upper=str.upper,
    caps=re.compile(rf"^([^\w]*)([{_UPPER}]{{1,3}})([^\w]*)$"),
    caps_lower=frozenset({"A", "À", "Y", "LA", "LE", "LES", "DE", "DU", "DES", "ET", "EN", "UN", "UNE", "ON", "NE",
                          "IL", "ELLE", "SI", "OU", "OÙ", "AU", "AUX", "SA", "SON", "SES", "CE", "CES", "QUI", "QUE",
                          "NOUS", "VOUS", "EST", "PAS", "PAR", "POUR", "SUR", "MAIS", "OUI", "NON"}),
)

# Streaming commit policy (see docs/streaming.md).
STREAMING_TURKISH_SUFFIXES = False
STREAMING_CONTINUATION: frozenset[str] = frozenset(
    NUMBER_WORDS + MONTHS + CURRENCY_WORDS + SEPARATOR_WORDS
    + ["premier", "première", "heures", "heure", "demi", "demie", "quart", "pour"]
)
STREAMING_ATTACH_NEXT: frozenset[str] = frozenset(
    CURRENCY_WORDS + UNIT_WORDS + SEPARATOR_WORDS + QUANTITY_WORDS
    + ["cent", "cents", "mille", "virgule", "d'euros"]
)

# Pre-hook mark (TN) put before a feminine number; defined here so the runtime needs no pynini.
FEM = "⁤"
