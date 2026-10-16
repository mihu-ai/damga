from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import text


def scores() -> pynini.Fst:
    """A score ``2-1`` → *zwei zu eins*: numbers below 100, the left one not smaller (a range runs upwards)."""
    small = [str(n) for n in range(100)]
    return pynini.union(*[pynini.accep(a) + "-" + pynini.union(*small[:int(a) + 1]) for a in small]).optimize()


class RangeReader(Rule):
    """``5–10`` → ``fünf bis zehn``; a score ``2-1`` → ``zwei zu eins``."""

    name = "range"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        dash = pynini.cross(pynini.union("-", "–", "—"), " bis ")
        span = number + dash + number
        score = scores()
        result = score @ (number + pynini.cross("-", " zu ") + number)
        span = pynini.difference(pynini.project(span, "input"), score) @ span
        return self.wrap(text(pynini.union(span, result))).optimize()
