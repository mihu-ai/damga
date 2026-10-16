from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import optional_suffix
from .number import CARDINAL, DIGIT_BY_DIGIT


class TimeWriter(Rule):
    name = "time"
    kind = "write"

    def build(self, variants: bool = False):
        hour = pynini.closure(DIGIT, 1) @ pynini.union(pynutil.delete("0") + DIGIT, DIGIT + DIGIT, DIGIT) @ CARDINAL
        hour = pynini.union(pynutil.delete("0") + (DIGIT @ CARDINAL), (DIGIT + DIGIT) @ CARDINAL, DIGIT @ CARDINAL)
        minute = pynini.union(
            pynutil.delete("00"),
            pynutil.insert(" ") + (pynini.accep("0") + DIGIT) @ DIGIT_BY_DIGIT,
            pynutil.insert(" ") + (pynini.difference(DIGIT, "0") + DIGIT) @ CARDINAL,
        )
        graph = pynutil.delete('hours="') + hour + pynutil.delete('" minutes="') + minute + pynutil.delete('"')
        return self.unwrap(graph + optional_suffix())
