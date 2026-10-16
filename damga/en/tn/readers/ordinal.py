from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import ORDINAL, ORDINAL_WRITTEN, strip_thousands
from .cardinal import text


def ordinal_words() -> pynini.Fst:
    """``21st`` → ``twenty first``; only a suffix that fits the number (not ``21th``)."""
    suffix = pynini.union("st", "nd", "rd", "th")
    digits = pynini.closure(DIGIT, 1) + pynutil.delete(suffix)
    written = (strip_thousands() + suffix) @ ORDINAL_WRITTEN
    return pynini.union(written @ digits @ ORDINAL, pynini.cross("0th", "zeroth")).optimize()


class OrdinalReader(Rule):
    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = ordinal_words()
        return self.wrap(text(self.number)).optimize()
