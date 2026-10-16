from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule, string_map
from ...itn.readers.plate import LETTER_NAMES
from .number import CARDINAL

_LETTER_SPOKEN: dict[str, str] = {}
for spoken, upper in LETTER_NAMES:
    _LETTER_SPOKEN.setdefault(upper, spoken)

class PlateWriter(Rule):
    name = "plate"
    kind = "write"

    def build(self, variants: bool = False):
        city = pynini.union(pynutil.delete("0") + (DIGIT @ CARDINAL), (pynini.difference(DIGIT, "0") + DIGIT) @ CARDINAL)
        letter = string_map([(u, s) for u, s in _LETTER_SPOKEN.items()])
        letters = letter + pynini.closure(pynutil.insert(" ") + letter, 0, 2)
        number = pynini.closure(DIGIT, 1) @ CARDINAL
        graph = (pynutil.delete('city="') + city + pynutil.delete('" letters="') + pynutil.insert(" ") + letters
                 + pynutil.delete('" number="') + pynutil.insert(" ") + number + pynutil.delete('"'))
        return self.unwrap(graph)
