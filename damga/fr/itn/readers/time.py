from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import text


class TimeReader(Rule):
    """``quinze heures trente`` → ``15 h 30``, ``deux heures moins le quart`` → ``1 h 45``.  One to ten o'clock
    alone stays words (``huit heures`` is as often a duration), and so do ``midi`` and ``minuit``."""

    name = "time"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        def said(n: int) -> pynini.Fst:
            return number @ pynini.accep(str(n))

        hour = number @ pynini.union(*[str(h) for h in range(24)])
        minutes = number @ pynini.union(*[str(m) for m in range(1, 60)]) @ pynini.union(pynutil.insert("0") + DIGIT, DIGIT + DIGIT)
        heures = pynini.union(" heures", " heure")
        h = pynini.cross(heures, " h")
        noon = pynini.union(pynini.cross("midi", "12 h"), pynini.cross("minuit", "0 h"))
        past = pynini.union(pynutil.delete(" ") + minutes, pynini.cross(" et quart", "15"),
                            pynini.cross(pynini.union(" et demie", " et demi"), "30"), pynini.cross(" et trois quarts", "45"))
        # "deux heures moins dix" → 1 h 50: the hour before, sixty minus the minutes
        before_hour = pynini.union(*[pynini.cross(pynini.project(said(n), "input") + heures, f"{(n - 1) % 24} h") for n in range(1, 24)],
                                   pynini.cross("midi", "11 h"), pynini.cross("minuit", "23 h"))
        to = pynini.union(pynini.cross(" moins le quart", "45"),
                          *[pynini.cross(" moins ", "") + (said(m) @ pynini.cross(str(m), f"{60 - m:02d}"))
                            for m in range(1, 30)])
        # "huit heures du soir" → 20 h: the qualifier picks the half of the day
        clock12 = pynini.union(*[said(n) for n in range(1, 13)]) + h + pynini.closure(pynutil.insert(" ") + past, 0, 1)
        evening = (pynini.union(*[said(n) @ pynini.cross(str(n), str(n + 12)) for n in range(1, 12)]) + h
                   + pynini.closure(pynutil.insert(" ") + past, 0, 1))
        graph = pynini.union(
            hour + h + pynutil.insert(" ") + past,
            (number @ pynini.union(*[str(h) for h in range(11, 24)])) + h,
            noon + pynutil.insert(" ") + past,
            before_hour + pynutil.insert(" ") + to,
            clock12 + pynutil.delete(pynini.union(" du matin", " de la nuit")),
            evening + pynutil.delete(pynini.union(" du soir", " de l'après-midi")),
        )
        return self.wrap(text(graph)).optimize()
