from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BEFORE_NOUN, FEMININE
from ...numbers import CARDINAL, CARDINAL_FEM
from .cardinal import text

_AM = pynini.union("a.m.", "a. m.", "a.m", "am", "AM", "A.M.")
_PM = pynini.union("p.m.", "p. m.", "p.m", "pm", "PM", "P.M.")


def _period(hour: int, pm: bool) -> str:
    """What a 12-hour clock says after the hour: *de la mañana*, *del mediodía*, *de la tarde*, *de la noche*."""
    if not pm:
        return "de la noche" if hour == 12 else "de la mañana"
    return "del mediodía" if hour == 12 else "de la tarde" if hour < 8 else "de la noche"


class TimeReader(Rule):
    """``11:45`` / ``11.45 horas`` → ``once cuarenta y cinco``, ``9:30`` → ``nueve y media``.  A point between hour
    and minutes counts only where the pre-hook turned it into a colon."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hour = pynini.union(*[str(h) for h in range(0, 24)], *[f"0{h}" for h in range(0, 10)])
        hour = hour @ pynini.union(pynutil.delete("0") + DIGIT, pynini.union(*"12") + DIGIT, DIGIT) @ CARDINAL_FEM
        minute = pynini.union(
            pynini.cross("30", "y media"), pynini.cross("15", "y cuarto"),
            pynutil.delete("0") + pynutil.insert("cero ") + (pynini.union(*"123456789") @ CARDINAL),
            (pynini.union(*"12345") + DIGIT) @ CARDINAL,
        )
        minute = pynini.difference(pynini.project(minute, "input"), pynini.union("30", "15")) @ minute | pynini.union(
            pynini.cross("30", "y media"), pynini.cross("15", "y cuarto"))
        if variants:
            # 9:30 → nueve treinta, 9:15 → nueve quince, 9:00 → nueve en punto
            minute = pynini.union(minute, pynutil.add_weight(pynini.cross("30", "treinta") | pynini.cross("15", "quince"), 0.5))
        rest = pynini.union(pynutil.delete("00"), pynutil.insert(" ") + minute)
        clock = hour + pynutil.delete(":") + rest
        # "a las 11.45 horas" → "a las once cuarenta y cinco"; variants mode keeps "horas" as a reading.
        horas = pynutil.delete(pynini.closure(pynini.union(" horas", " h"), 0, 1))
        if variants:
            horas = pynini.union(horas, pynutil.add_weight(pynini.accep(" horas") | pynini.cross(" h", " horas"), 0.5))
        # a zero-padded hour is a clock time: "07 h" → "siete" ("7 h" is a duration, read by the measures)
        padded = (pynini.accep("0") + DIGIT) @ hour + pynutil.delete(pynini.union(" h", "h"))
        # 12-hour clock: "5:02 p.m." → "cinco cero dos de la tarde", "12.15 a.m." → "doce y cuarto de la noche"
        twelve = []
        unmark = pynutil.delete(pynini.union(BEFORE_NOUN, FEMININE)).ques       # "las 5 pm": marked before a word
        for h in range(1, 13):
            said = unmark + (pynini.union(str(h), f"0{h}" if h < 10 else str(h)) @ hour)
            for marks, pm in ((_AM, False), (_PM, True)):
                period = pynini.cross(pynini.closure(" ", 0, 1) + marks, " " + _period(h, pm))
                twelve.append(said + pynini.union(pynutil.delete(":") + rest, pynini.accep("")) + period)
        # "3:02:32" → "tres horas dos minutos y treinta y dos segundos"; "12:00:00" is the clock time
        two = pynini.union("0" + DIGIT, pynini.union(*"12345") + DIGIT)
        number = pynini.union(pynutil.delete("0") + DIGIT, pynini.union(*"12345") + DIGIT) @ CARDINAL
        one = pynini.union("1", "01")
        hours = pynini.union(pynini.cross(one, "una hora"), (pynini.difference(
            pynini.project(hour, "input"), pynini.union(one, "0", "00")) @ hour) + pynutil.insert(" horas"))
        minutes = pynini.union(pynini.cross("01", "un minuto"),
                               (pynini.difference(two, pynini.union("00", "01")) @ number) + pynutil.insert(" minutos"))
        seconds = pynini.union(pynini.cross("01", "un segundo"),
                               (pynini.difference(two, pynini.union("00", "01")) @ number) + pynutil.insert(" segundos"))
        with_seconds = pynini.union(hours + pynini.cross(":", " ") + minutes + pynini.cross(":", " y ") + seconds,
                                    clock + pynutil.delete(":00"))
        graph = pynini.union(clock + horas, padded, *twelve, with_seconds)
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(
                hour + pynini.cross(":00", " en punto") + pynutil.delete(pynini.closure(pynini.union(" horas", " h"), 0, 1)), 0.7))
        return self.wrap(text(graph)).optimize()
