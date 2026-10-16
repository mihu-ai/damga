from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule
from .decimal import number_body, optional_sign


class MeasureWriter(Rule):
    name = "measure"
    kind = "write"

    def build(self, variants: bool = False, **style: bool):
        glued = pynutil.delete(' units="') + pynini.accep("°") + pynini.closure(NON_QUOTE) + pynutil.delete('"')
        spaced = pynutil.delete(' units="') + pynutil.insert(" ") + pynini.difference(pynini.closure(NON_QUOTE, 1), pynini.accep("°") + pynini.closure(NON_QUOTE)) + pynutil.delete('"')
        return self.unwrap(optional_sign() + number_body(**style) + pynini.union(glued, spaced))
