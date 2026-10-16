from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule


class IbanWriter(Rule):
    name = "iban"
    kind = "write"

    def build(self, variants: bool = False):
        return self.unwrap(pynutil.delete('number="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"'))
