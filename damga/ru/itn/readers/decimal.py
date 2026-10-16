from __future__ import annotations

import pynini

from ....core.rules import Rule
from .common import spoken_fraction, text


class DecimalReader(Rule):
    """``три целых и пять десятых`` → 3,5, ``одной целой и одной десятой`` → 1,1."""

    name = "decimal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = spoken_fraction()
        sign = pynini.closure(pynini.cross("минус ", "-"), 0, 1)
        return self.wrap(text(sign + self.number)).optimize()
