from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL
from .cardinal import text

# "nine thirty" is read as a time only after one of these words; otherwise it may be a price or a model number.
CONTEXT = ("at", "by", "until", "till", "from", "around", "before", "after", "since")


def _said(n: int) -> str:
    return pynini.shortestpath(pynini.accep(str(n)) @ CARDINAL).string()


def _quarters() -> tuple[pynini.Fst, pynini.Fst]:
    """``half past three`` → ``3:30``, ``quarter to twelve`` → ``11:45``.  ``ten to eleven`` is returned apart, since
    "to" also joins two numbers (``five to ten``)."""
    minute_word = pynini.closure(pynini.union(" minutes", " minute", " mins", " min"), 0, 1)
    past, to = [], []
    for h in range(1, 13):
        hour, before = _said(h), (h - 2) % 12 + 1
        past += [pynini.cross(f"half past {hour}", f"{h}:30"),
                 pynini.cross(pynini.union("", "a ") + f"quarter past {hour}", f"{h}:15"),
                 pynini.cross(pynini.union("", "a ") + f"quarter to {hour}", f"{before}:45")]
        for m in range(1, 30):
            said = pynini.accep(_said(m)) + minute_word
            past.append(pynini.cross(said + f" past {hour}", f"{h}:{m:02d}"))
            to.append(pynini.cross(said + f" to {hour}", f"{before}:{60 - m:02d}"))
    return pynini.union(*past).optimize(), pynini.union(*to).optimize()


class TimeReader(Rule):
    """``nine thirty a m`` → ``9:30 a.m.``, ``at nine thirty`` → ``at 9:30``, ``fourteen hundred hours`` → ``14:00``."""

    name = "time"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        hour12 = number @ pynini.union(*[str(h) for h in range(1, 13)])
        hour24 = number @ pynini.union(*[str(h) for h in range(0, 24)])
        zero = pynini.union("oh ", "o ", "zero ")
        minutes = pynini.union(
            pynini.cross(zero, "0") + (number @ pynini.union(*"123456789")),
            number @ (pynini.union(*"12345") + DIGIT),
        )
        suffix = pynini.union(pynini.cross(" a m", " a.m."), pynini.cross(" p m", " p.m."),
                              pynini.cross(" am", " a.m."), pynini.cross(" pm", " p.m."))
        clock = hour12 + pynini.cross(" ", ":") + minutes
        # military time: "fourteen hundred hours"; not "six hundred hours", which counts hours
        military_hour = pynini.union(number @ pynini.union(*[str(h) for h in range(10, 24)]),
                                     pynini.cross(zero, "0") + (number @ pynini.union(*"123456789")))
        military = pynini.union(military_hour + pynini.cross(" hundred hours", ":00"),
                                military_hour + pynini.cross(" ", ":") + minutes + pynutil.delete(" hours"))
        past, to = _quarters()
        context = pynini.union(*CONTEXT) + pynini.accep(" ")
        graph = pynini.union(
            clock + suffix,
            hour12 + suffix,
            hour12 + pynini.union(" o'clock", pynini.cross(" oclock", " o'clock")),
            context + hour24 + pynini.cross(" ", ":") + minutes,
            military,
            past + pynini.closure(suffix, 0, 1),
            to + suffix,
            # "at ten to eleven"; not "from five to ten"
            pynutil.add_weight(pynini.accep("at ") + to + pynini.closure(suffix, 0, 1), 0.5),
        )
        return self.wrap(text(graph)).optimize()
