from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule


class PlateWriter(Rule):
    name = "plate"
    kind = "write"

    def build(self, variants: bool = False):
        q = pynini.closure(NON_QUOTE, 1)
        graph = (pynutil.delete('city="') + q + pynutil.delete('" letters="') + pynutil.insert(" ") + q
                 + pynutil.delete('" number="') + pynutil.insert(" ") + q + pynutil.delete('"'))
        return self.unwrap(graph)
