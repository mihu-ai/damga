from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from ...numbers import CARDINAL
from .cardinal import text


def _capital(word: str) -> str:
    return word[0].upper() + word[1:]


class DateReader(Rule):
    """``2 febbraio 2017`` → ``due febbraio duemiladiciassette``, ``1º gennaio`` → ``primo gennaio``.  The day is said
    without "di"."""

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        day_digits = pynini.union(*[str(d) for d in range(2, 32)], *[f"0{d}" for d in range(2, 10)])
        first = pynini.cross(pynini.union("1", "01", "1º", "1°", "1o"), "primo")
        day = pynini.union(first, (day_digits @ pynini.union(pynutil.delete("0") + DIGIT, pynini.closure(DIGIT, 1, 2))) @ CARDINAL)
        month = pynini.union(*[pynini.union(m, _capital(m)) for m in MONTHS])
        year = (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ CARDINAL
        sp = pynini.accep(" ")
        written = day + sp + month + pynini.closure(sp + year, 0, 1)
        slashed_said: list[tuple[pynini.Fst, str]] = []
        for m in range(1, 13):
            for d in range(1, 32):
                said = "primo" if d == 1 else pynini.shortestpath(pynini.accep(str(d)) @ CARDINAL).string()
                slashed = pynini.union(f"{d:02d}/{m:02d}/", f"{d}/{m}/", f"{d:02d}/{m}/", f"{d}/{m:02d}/")
                slashed_said.append((slashed, f"{said} {MONTHS[m - 1]} "))
        numeric = pynini.union(*[pynini.cross(a, b) for a, b in slashed_said]) + year
        return self.wrap(text(pynini.union(written, numeric))).optimize()
