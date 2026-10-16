from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule
from .cardinal import optional_sign, optional_suffix, soften_dort
from .decimal import number_body


class MeasureWriter(Rule):
    name = "measure"
    kind = "write"

    def build(self, variants: bool = False):
        units = pynutil.delete(' units="') + pynutil.insert(" ") + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"')
        return (self.unwrap(optional_sign() + number_body() + units + optional_suffix()) @ soften_dort()).optimize()
