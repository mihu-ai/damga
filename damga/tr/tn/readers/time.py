from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import TR_LOWER, Rule


class TimeReader(Rule):
    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hours = pynini.union(*[f"{h:02d}" for h in range(24)] + [str(h) for h in range(24)])
        minutes = pynini.union(*[f"{m:02d}" for m in range(60)])
        h = pynutil.insert('hours="') + hours + pynutil.insert('"')
        m = pynutil.insert(' minutes="') + minutes + pynutil.insert('"')
        suffix = pynini.closure(pynutil.delete("'") + pynutil.insert(' suffix="') + pynini.closure(TR_LOWER, 1) + pynutil.insert('"'), 0, 1)
        colon = h + pynutil.delete(":") + m
        dotted = h + pynutil.delete(".") + m
        keyword = pynutil.insert('word="') + pynini.union("saat", "Saat") + pynutil.insert('" ') + pynutil.delete(" ")
        return pynini.union(
            self.wrap(colon + suffix),
            keyword + self.wrap(pynini.union(colon, dotted) + suffix),
        ).optimize()
