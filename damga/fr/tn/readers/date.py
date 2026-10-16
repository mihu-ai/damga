from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import MONTHS
from ...numbers import CARDINAL
from .cardinal import text


class DateReader(Rule):
    """``3 octobre 2012`` / ``03/10/2012`` → ``trois octobre deux mille douze``, ``les 17/18 juin`` → ``les
    dix-sept et dix-huit juin``.  The pre-hook reorders ISO dates."""

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        day_digits = pynini.union(*[str(d) for d in range(1, 32)], *[f"0{d}" for d in range(1, 10)])
        day = pynini.union(
            pynini.cross(pynini.union("1", "01", "1er", "1ᵉʳ"), "premier"),
            (pynini.difference(day_digits, pynini.union("1", "01"))
             @ pynini.union(pynutil.delete("0") + NONZERO_DIGIT, NONZERO_DIGIT, NONZERO_DIGIT + DIGIT) @ CARDINAL),
        )
        month = pynini.union(*[pynini.union(m, m.capitalize()) for m in MONTHS])
        year = (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ CARDINAL
        sp = pynini.accep(" ")
        written = day + sp + month + pynini.closure(sp + year, 0, 1)
        # Several days of one month: 17/18 juin, 17/18/19 mars, 17-18-19 juin (two days with a dash are a range).
        dash = pynini.union("/", "-")
        days = pynini.union(day + pynini.cross("/", " et ") + day,
                            day + pynini.closure(pynini.cross(dash, ", ") + day, 1) + pynini.cross(dash, " et ") + day)
        listed = days + sp + month + pynini.closure(sp + year, 0, 1)
        numeric = []
        for m in range(1, 13):
            for sep in ("/", ".", "-"):
                numeric.append(day + pynini.cross(pynini.union(f"{sep}{m:02d}{sep}", f"{sep}{m}{sep}"), f" {MONTHS[m - 1]} ")
                               + year)
        return self.wrap(text(pynini.union(written, listed, *numeric))).optimize()
