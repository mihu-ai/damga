from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule


class EmailWriter(Rule):
    name = "email"
    kind = "write"

    def build(self, variants: bool = False):
        return self.unwrap(pynutil.delete('address="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"'))
