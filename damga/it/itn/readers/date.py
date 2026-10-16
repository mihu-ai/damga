from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from .cardinal import text


class DateReader(Rule):
    """``due febbraio duemiladiciassette`` → ``2 febbraio 2017``, ``primo gennaio`` → ``1º gennaio``."""

    name = "date"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        day = pynini.union(number @ pynini.union(*[str(d) for d in range(2, 32)]),
                           pynini.cross(pynini.union("primo", "uno"), "1º"))
        month = pynini.union(*MONTHS)
        year = number @ pynini.union("1" + DIGIT + DIGIT + DIGIT, "20" + DIGIT + DIGIT)
        sp = pynini.accep(" ")
        with_year = pynini.closure(pynini.union(sp, pynini.cross(" del ", " ")) + year, 0, 1)
        days = day + pynini.closure(pynini.accep(" e ") + day, 0, 1)          # il 4 e 5 aprile
        day_month = days + pynutil.delete(pynini.closure(" di", 0, 1)) + sp + month + with_year
        month_year = month + sp + year
        return self.wrap(text(pynini.union(day_month, month_year))).optimize()
