from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule
from .cardinal import optional_sign, optional_suffix, soften_dort
from .decimal import bucuk_with_suffix, number_body


class PercentWriter(Rule):
    name = "percent"
    kind = "write"

    def build(self, variants: bool = False):
        symbol = pynutil.delete('symbol="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"') + pynini.accep(" ")
        body = pynini.union(number_body() + optional_suffix(), bucuk_with_suffix())
        return (self.unwrap(symbol + optional_sign() + body) @ soften_dort()).optimize()
