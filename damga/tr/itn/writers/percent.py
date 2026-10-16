from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule
from .decimal import number_body, optional_sign


class PercentWriter(Rule):
    name = "percent"
    kind = "write"

    def build(self, variants: bool = False, **style: bool):
        symbol = pynutil.delete('symbol="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('" ')
        return self.unwrap(symbol + optional_sign() + number_body(**style))
