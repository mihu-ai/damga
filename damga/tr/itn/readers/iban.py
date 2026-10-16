from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule, drop_space
from .cardinal import CardinalReader
from .telephone import digit_groups


class IbanReader(Rule):
    name = "iban"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        groups = digit_groups(cardinal, max_group=4)
        d = DIGIT
        four = d + d + d + d
        fmt = d + d + pynutil.insert(" ") + four + pynutil.insert(" ") + four + pynutil.insert(" ") + four + pynutil.insert(" ") + four + pynutil.insert(" ") + four + pynutil.insert(" ") + d + d
        prefix = pynini.union(pynini.cross("te re", "TR"), pynini.cross("ti ar", "TR"), pynini.cross("tr", "TR"), pynini.cross("iban te re", "TR"), pynini.cross("iban", "TR"))
        number = prefix + drop_space + (groups @ fmt)
        return self.wrap(pynutil.insert('number="') + number + pynutil.insert('"')).optimize()
