from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_ATTRIBUTIVE
from .cardinal import text


class TimeReader(Rule):
    """``15:30 Uhr`` → ``fünfzehn Uhr dreißig``.  ``15.30`` without "Uhr" stays a decimal."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hours = pynini.union(*[str(h) for h in range(0, 25)], *[f"0{h}" for h in range(0, 10)])
        strip = pynini.union(pynutil.delete("0") + DIGIT, DIGIT, NONZERO_DIGIT + DIGIT)
        say_hour = pynini.union(pynini.cross("0", "null"), pynini.difference(pynini.closure(DIGIT, 1, 2), "0") @ CARDINAL_ATTRIBUTIVE)
        hour = hours @ strip @ say_hour
        minutes = pynini.union(pynutil.delete("00"),
                               pynutil.insert(" ") + pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL),
                               pynutil.insert(" ") + ((pynini.union(*"12345") + DIGIT) @ CARDINAL))
        uhr = pynutil.delete(pynini.union(" Uhr", " h"))
        colon = hour + pynutil.insert(" Uhr") + pynutil.delete(":") + minutes + pynini.closure(uhr, 0, 1)
        dot = hour + pynutil.insert(" Uhr") + pynutil.delete(".") + minutes + uhr
        plain = hour + pynini.accep(" Uhr")
        # hh:mm:ss only with "Uhr": without it, 2:02:23 may be a duration
        two = pynini.union(*[f"{n:02d}" for n in range(60)]) @ strip

        def count(sg: str, pl: str) -> pynini.Fst:
            return pynini.union(pynini.cross("1", "eine " + sg),
                                (pynini.difference(pynini.project(two, "output"), "1") @ CARDINAL) + pynutil.insert(" " + pl))

        seconds = (hour + pynutil.insert(" Uhr ") + pynutil.delete(":") + (two @ count("Minute", "Minuten"))
                   + pynutil.insert(" ") + pynutil.delete(":") + (two @ count("Sekunde", "Sekunden")) + uhr)
        return self.wrap(text(pynini.union(colon, dot, plain, seconds))).optimize()
