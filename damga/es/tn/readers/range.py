from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import text


class RangeReader(Rule):
    """``2014-2020`` → ``dos mil catorce a dos mil veinte``, ``5-10`` → ``cinco a diez``."""

    name = "range"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        return self.wrap(text(number + pynini.cross(pynini.union("-", "–", "—"), " a ") + number)).optimize()
