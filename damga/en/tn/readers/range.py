from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import text


class RangeReader(Rule):
    """``5-10`` → ``five to ten`` (hyphen or en dash); years stay years."""

    name = "range"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        dash = pynini.cross(pynini.union("-", "–", "—"), " to ")
        graph = number + dash + number
        return self.wrap(text(graph)).optimize()
