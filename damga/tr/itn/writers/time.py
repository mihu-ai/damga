from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule


class TimeWriter(Rule):
    name = "time"
    kind = "write"

    def build(self, variants: bool = False):
        two = DIGIT + DIGIT
        from ....core.rules import NON_QUOTE
        suffix = pynini.closure(pynutil.delete(' suffix="') + pynutil.insert("'") + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"'), 0, 1)
        graph = pynutil.delete('hours="') + two + pynutil.delete('" minutes="') + pynutil.insert(":") + two + pynutil.delete('"') + suffix
        return self.unwrap(graph)
