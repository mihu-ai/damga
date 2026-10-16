from __future__ import annotations

import pynini

from ....core.rules import DIGIT, Rule
from .cardinal import text


class RangeReader(Rule):
    """``5-10`` → ``cinque dieci``: two short numbers said one after the other.  Two numbers of three digits or more do
    not run together: years take ``al`` (``1914-1918`` → ``millenovecentoquattordici al millenovecentodiciotto``),
    other numbers ``a``."""

    name = "range"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        dash = pynini.union("-", "–", "—")
        written = pynini.project(number, "input").optimize()
        short = pynini.closure(DIGIT, 1, 2)
        long = pynini.difference(written, short)
        year = pynini.union("1" + DIGIT + DIGIT + DIGIT, "20" + DIGIT + DIGIT)
        years = year + dash + year
        longs = pynini.difference(long + dash + long, years)
        others = pynini.difference(written + dash + written, long + dash + long)

        def said(connector: str) -> pynini.Fst:
            return number + pynini.cross(dash, connector) + number

        return self.wrap(text(pynini.union(years @ said(" al "), longs @ said(" a "),
                                           others @ said(" ")))).optimize()
