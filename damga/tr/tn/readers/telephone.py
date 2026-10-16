from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, TR_LOWER, Rule


class TelephoneReader(Rule):
    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        d = DIGIT
        osp = pynutil.delete(pynini.closure(pynini.union(" ", "-"), 0, 1))    # ``0532 123 45 67``, ``+90-532-123-45-67``
        op = pynutil.delete(pynini.closure("(", 0, 1)); cp = pynutil.delete(pynini.closure(")", 0, 1))
        area = op + d + d + d + cp
        rest = osp + d + d + d + pynutil.insert(" ") + osp + d + d + pynutil.insert(" ") + osp + d + d
        domestic = pynini.accep("0") + osp + area + pynutil.insert(" ") + rest
        intl = pynini.union("+90", "0090") + pynutil.insert(" ") + osp + area + pynutil.insert(" ") + rest
        # ``0212 123 45 67'den``: the suffix is said after the last group (*… altmış yediden*).
        suffix = pynini.closure(pynutil.delete("'") + pynutil.insert(' suffix="') + pynini.closure(TR_LOWER, 1) + pynutil.insert('"'), 0, 1)
        return self.wrap(pynutil.insert('number="') + pynini.union(domestic, intl) + pynutil.insert('"') + suffix).optimize()
