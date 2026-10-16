from __future__ import annotations

import pynini

from ....core.rules import Rule
from ...lexicon import CASES, GNUM, ORD_UNITS, adjective
from .common import spoken_ordinal, text


class OrdinalReader(Rule):
    """``двадцать первого`` → 21-го, ``тысяча девятьсот тридцатых`` → 1930-х.  Ordinals below ten stay words
    (``второе место``)."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        number = spoken_ordinal()
        small = pynini.union(*{adjective(w, c, g) for w in ORD_UNITS.values() for c in CASES for g in GNUM})
        big = pynini.difference(pynini.project(number, "input"), small) @ number
        return self.wrap(text(big)).optimize()
