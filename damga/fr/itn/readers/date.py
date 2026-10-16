from __future__ import annotations

import pynini

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from .cardinal import text


class DateReader(Rule):
    """``trois octobre deux mille douze`` → ``3 octobre 2012``, ``le premier janvier`` → ``le 1er janvier``,
    ``deux mille quatorze deux mille vingt`` → ``2014-2020``."""

    name = "date"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        day = pynini.union(number @ pynini.union(*[str(d) for d in range(2, 32)]), pynini.cross("premier", "1er"))
        month = pynini.union(*MONTHS)
        year = number @ (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT)
        sp = pynini.accep(" ")
        # Two years in a row are a period (2010-2015); not 2000, which is as often "deux mille" of something.
        period_year = number @ pynini.difference(pynini.union("19", "20") + DIGIT + DIGIT, "2000")
        period = period_year + pynini.cross(" ", "-") + period_year
        graph = pynini.union(day + sp + month + pynini.closure(sp + year, 0, 1), month + sp + year, period)
        return self.wrap(text(graph)).optimize()
