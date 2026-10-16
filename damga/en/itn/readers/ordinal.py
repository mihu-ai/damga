from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import ORDINAL_SPOKEN, ORDINAL_WRITTEN
from .cardinal import text


def spoken_ordinal() -> pynini.Fst:
    """``twenty first`` → ``21st``, ``one hundred eleventh`` → ``111th``, every value."""
    strip = ORDINAL_WRITTEN @ (pynini.closure(DIGIT, 1) + pynutil.delete(pynini.union("st", "nd", "rd", "th")))
    return (pynini.invert(ORDINAL_SPOKEN) @ pynini.invert(strip)).optimize()


class OrdinalReader(Rule):
    """``twenty first`` → ``21st``, ``tenth`` → ``10th``; first to ninth stay words (``the first time``)."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = spoken_ordinal()
        small = pynini.union(*[w for w in ("first", "second", "third", "fourth", "fifth", "sixth", "seventh",
                                            "eighth", "ninth")])
        big = pynini.difference(pynini.project(self.number, "input"), small) @ self.number
        return self.wrap(text(big)).optimize()
