from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_FEM
from .cardinal import text


class TimeReader(Rule):
    """``15 h 30`` / ``15:30`` → ``quinze heures trente``, ``1 h`` → ``une heure``."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hours = pynini.union(*[str(h) for h in range(24)], *[f"0{h}" for h in range(10)])
        hour_words = hours @ pynini.union(pynutil.delete("0") + DIGIT, pynini.closure(DIGIT, 1, 2)) @ CARDINAL_FEM
        hour = pynini.union(
            ((pynini.union("0", "00", "1", "01")) @ hour_words) + pynutil.insert(" heure"),
            (pynini.difference(hours, pynini.union("0", "00", "1", "01")) @ hour_words) + pynutil.insert(" heures"),
        )
        minutes = pynini.union(pynutil.delete("0") + (pynini.union(*"123456789") @ CARDINAL),
                               (pynini.union(*"12345") + DIGIT) @ CARDINAL)
        sp = pynutil.delete(pynini.closure(" ", 0, 1))
        h = sp + pynutil.delete("h") + sp
        graph = pynini.union(
            hour + h + pynini.closure(pynutil.insert(" ") + minutes, 0, 1) + pynini.closure(pynutil.delete("00"), 0, 1),
            hour + pynutil.delete(":") + pynini.union(pynutil.delete("00"), pynutil.insert(" ") + minutes),
        )
        if variants:
            # 12 h → midi, 0 h → minuit
            twelve = pynini.union("12 h", "12h", "12:00", "12 h 00", "12h00")
            zero = pynini.union("0 h", "0h", "00:00", "00 h", "00h", "0:00")
            special = pynini.union(pynini.cross(twelve, "midi"), pynini.cross(zero, "minuit"),
                                   pynini.cross(pynini.union("12 h ", "12h", "12:"), "midi ") + minutes)
            graph = pynini.union(graph, pynutil.add_weight(special, 0.5))
        return self.wrap(text(graph)).optimize()
