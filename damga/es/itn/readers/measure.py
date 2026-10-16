from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import text


class PercentReader(Rule):
    """``cinco por ciento`` → ``5 %``, ``del cinco al diez por ciento`` → ``del 5 al 10 %``."""

    name = "percent"
    kind = "read"

    def build(self, written: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        sign = pynini.closure(pynini.cross("menos ", "-"), 0, 1)
        amount = pynini.union(written, decimal)
        percent = sign + amount + pynini.cross(" por ciento", " %")
        span = amount + pynini.union(" y ", " a ", " al ", " o ") + percent
        return self.wrap(text(pynini.union(percent, span))).optimize()
