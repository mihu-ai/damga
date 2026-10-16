from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .number import DIGIT_BY_DIGIT


class IbanWriter(Rule):
    name = "iban"
    kind = "write"

    def build(self, variants: bool = False):
        # Digit by digit with a pause between the written groups, the way an IBAN is dictated; read as numbers,
        # neighbouring groups run together (``1005 1978`` → *bin beş bin dokuz yüz …*).
        d = DIGIT
        two = (d + d) @ DIGIT_BY_DIGIT
        four = (d + d + d + d) @ DIGIT_BY_DIGIT
        sp = pynini.cross(" ", ", ")
        graph = pynutil.insert("te re ") + two + sp + four + sp + four + sp + four + sp + four + sp + four + sp + two
        return self.unwrap(pynutil.delete('groups="') + graph + pynutil.delete('"'))
