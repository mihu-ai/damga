from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL
from .cardinal import text


class TimeReader(Rule):
    """``9.15`` → ``nove e quindici``, ``1.30`` → ``una e trenta``.  A point with two digits is a clock time: Italian
    writes decimals with a comma and thousands with three digits."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hours = pynini.union(*[str(h) for h in range(0, 25)], *[f"0{h}" for h in range(0, 10)])
        hour_words = pynini.union(pynini.cross(pynini.union("1", "01"), "una"),
                                  (pynini.difference(hours, pynini.union("1", "01"))
                                   @ pynini.union(pynutil.delete("0") + DIGIT, pynini.closure(DIGIT, 1, 2)) @ CARDINAL))
        minutes = pynini.union(pynutil.delete("0") + (pynini.union(*"123456789") @ CARDINAL),
                               (pynini.union(*"12345") + DIGIT) @ CARDINAL)
        sep = pynini.union(".", ":")
        graph = hour_words + pynutil.delete(sep) + pynini.union(pynutil.delete("00"), pynutil.insert(" e ") + minutes)

        # 17:15:26 → diciassette e quindici minuti e ventisei secondi: with seconds, minutes and seconds say their unit
        def counted(sg: str, pl: str) -> pynini.Fst:
            return pynini.union(pynini.cross("01", "un " + sg),
                                pynini.difference(pynini.project(minutes, "input"), "01") @ minutes
                                + pynutil.insert(" " + pl))

        with_seconds = (hour_words + pynutil.delete(":")
                        + pynini.union(pynutil.delete("00"), pynutil.insert(" e ") + counted("minuto", "minuti"))
                        + pynutil.delete(":")
                        + pynini.union(pynutil.delete("00"), pynutil.insert(" e ") + counted("secondo", "secondi")))
        graph = pynini.union(graph, with_seconds)
        return self.wrap(text(graph)).optimize()
