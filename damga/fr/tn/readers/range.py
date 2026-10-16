from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL
from .cardinal import text


class RangeReader(Rule):
    """``5-10`` → ``cinq à dix``; two years are joined by *à* too, the reading without it is only a variant."""

    name = "range"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        dash = pynini.union("-", "–", "—")
        year = (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ CARDINAL
        years = year + pynini.cross(dash, " à ") + year
        year_inputs = pynini.project(years, "input")
        other = pynini.difference(pynini.project(number + dash + number, "input"), year_inputs) @ (
            number + pynini.cross(dash, " à ") + number)
        graph = pynini.union(years, other)
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(year + pynini.cross(dash, " ") + year, 0.5))
        return self.wrap(text(graph)).optimize()
