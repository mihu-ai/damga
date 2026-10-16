from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule


class OrdinalWriter(Rule):
    name = "ordinal"
    kind = "write"

    def build(self, variants: bool = False):
        # Ordinals are written without a thousands separator (2024. yıl, 1687. kat): ``1.687.`` would read as a date.
        number = pynini.closure(DIGIT, 1)
        return self.unwrap(pynutil.delete('integer="') + number + pynutil.delete('"') + pynutil.insert("."))
