from __future__ import annotations

import pynini

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from .cardinal import text


class DateReader(Rule):
    """``diecisiete de febrero de dos mil ocho`` → ``17 de febrero de 2008``, ``siglo diecinueve`` → ``siglo
    XIX``."""

    name = "date"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        day = pynini.union(number @ pynini.union(*[str(d) for d in range(1, 32)]), pynini.cross("primero", "1"))
        month = pynini.union(*MONTHS)
        year = number @ (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT)
        graph = day + pynini.accep(" de ") + month + pynini.closure(pynini.union(" de ", " del ") + year, 0, 1)
        # centuries in Roman numerals: "el siglo diecinueve" → "el siglo XIX"
        roman = pynini.string_map([(str(n), _roman(n)) for n in range(1, 31)])
        century = pynini.union("siglo ", "siglos ") + (number @ roman)
        # "doscientos tres antes de Cristo" → "203 a. C."
        era = (number @ pynini.closure(DIGIT, 1)) + pynini.union(pynini.cross(" antes de cristo", " a. C."),
                                                                 pynini.cross(" después de cristo", " d. C."))
        return self.wrap(text(pynini.union(graph, century, era))).optimize()


def _roman(n: int) -> str:
    out = ""
    for value, numeral in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out, n = out + numeral, n - value
    return out
