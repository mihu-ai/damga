from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule


class PlateReader(Rule):
    name = "plate"
    kind = "read"

    def build(self, variants: bool = False):
        city = pynini.union(*[f"{i:02d}" for i in range(1, 82)])
        letter = pynini.union(*"ABCDEFGHIJKLMNOPRSTUVYZ")
        osp = pynutil.delete(pynini.closure(" ", 0, 1))
        number = pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 3)
        graph = (pynutil.insert('city="') + city + pynutil.insert('" letters="') + osp + letter + pynini.closure(letter, 0, 2)
                 + pynutil.insert('" number="') + osp + number + pynutil.insert('"'))
        return self.wrap(graph).optimize()
