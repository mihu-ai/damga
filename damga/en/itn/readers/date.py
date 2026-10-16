from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS, TIES
from .cardinal import text


class DateReader(Rule):
    """``the sixth of december`` → ``6 December``, ``december sixth`` / ``december the sixth`` → ``December 6``,
    with a year: ``the sixth of december twenty twelve`` → ``6 December 2012``; ``december twenty twelve`` →
    ``December 2012``; ``the nineteen nineties`` → ``the 1990s``."""

    name = "date"
    kind = "read"

    def build(self, ordinal: pynini.Fst, year: pynini.Fst, variants: bool = False):
        day = ordinal @ (pynini.union(*[str(d) for d in range(1, 32)]) + pynutil.delete(pynini.union("st", "nd", "rd", "th")))
        month = pynini.union(*[pynini.cross(m, m.capitalize()) for m in MONTHS])
        sp = pynini.accep(" ")
        with_year = pynini.closure(sp + year, 0, 1)
        day_first = (pynutil.delete(pynini.closure("the ", 0, 1)) + day + pynutil.delete(" of") + sp + month
                     + with_year)
        month_first = month + sp + pynutil.delete(pynini.closure("the ", 0, 1)) + day + with_year
        month_year = month + sp + year
        plural = pynini.union(*[pynini.cross(w[:-1] + "ies", w) for w, _ in TIES],
                              pynini.cross("hundreds", "hundred"))
        letters = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz "))
        decade = (pynini.closure(letters + " ", 0, 1) + plural) @ year @ (pynini.closure(DIGIT, 3) + "0") + pynutil.insert("s")
        return self.wrap(text(pynini.union(day_first, month_first, month_year, decade))).optimize()
