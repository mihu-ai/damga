from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule


class IbanReader(Rule):
    name = "iban"
    kind = "read"

    def build(self, variants: bool = False):
        d = DIGIT
        osp = pynutil.delete(pynini.closure(" ", 0, 1))
        four = osp + pynutil.insert(" ") + d + d + d + d
        graph = pynutil.delete("TR") + d + d + four + four + four + four + four + osp + pynutil.insert(" ") + d + d
        return self.wrap(pynutil.insert('groups="') + graph + pynutil.insert('"')).optimize()
