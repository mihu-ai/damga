from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import CARDINAL, ONES, TENS
from .cardinal import text


class TimeReader(Rule):
    """``9:05`` → ``nine oh five``, ``9am`` → ``nine a m``, ``2pm-5pm`` → ``two p m to five p m``."""

    name = "time"
    kind = "read"

    def build(self, variants: bool = False):
        hour12 = pynini.union(*[str(h) for h in range(1, 13)], *[f"0{h}" for h in range(1, 10)])
        hour24 = pynini.union(*[str(h) for h in range(0, 24)], *[f"0{h}" for h in range(0, 10)])
        hour_words = pynini.union(pynutil.delete("0") + pynini.union(*"123456789"), pynini.union(*[str(h) for h in range(1, 24)]),
                                  pynini.cross("00", "0"), "0") @ CARDINAL
        minutes = pynini.union(pynutil.delete("0") + pynutil.insert("oh ") + ONES,
                               (pynini.union(*"12345") + DIGIT) @ TENS)
        colon = pynini.union(":", ".")
        clock = (hour24 @ hour_words) + pynutil.delete(":") + pynutil.insert(" ") + minutes
        oclock = (hour12 @ hour_words) + pynini.cross(":00", " o'clock")
        hundred = ((pynini.union(*[str(h) for h in range(13, 24)]) @ hour_words) + pynini.cross(":00", " hundred"))
        zero_hour = pynini.cross("00:00", "midnight") | pynini.cross("12:00", "twelve o'clock")
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        suffix = pynini.union(
            pynini.cross(pynini.union("am", "a.m.", "a.m", "AM", "A.M."), "a m"),
            pynini.cross(pynini.union("pm", "p.m.", "p.m", "PM", "P.M."), "p m"),
        )
        with_suffix = ((hour12 @ hour_words) + pynini.closure((pynutil.delete(colon) + pynutil.insert(" ")
                       + pynini.union(minutes, pynutil.delete("00"))), 0, 1) + space + pynutil.insert(" ") + suffix)

        # 14:10:30 → fourteen hours ten minutes and thirty seconds
        def counted(unit: str) -> pynini.Fst:
            two = pynini.union(pynutil.delete("0") + DIGIT, pynini.union(*"12345") + DIGIT) @ CARDINAL
            return pynini.union(pynini.cross(pynini.union("1", "01"), f"one {unit}"),
                                pynini.difference(pynini.project(two, "input"), pynini.union("1", "01")) @ two
                                + pynutil.insert(f" {unit}s"))
        hours = (hour24 @ pynini.union(pynini.cross(pynini.union("1", "01"), "one hour"),
                                       pynini.difference(hour24, pynini.union("1", "01")) @ hour_words
                                       + pynutil.insert(" hours")))
        seconds = (hours + pynini.cross(":", " ") + counted("minute") + pynini.cross(":", " and ")
                   + counted("second") + pynini.closure(space + pynutil.insert(" ") + suffix, 0, 1))
        graph = pynini.union(pynutil.add_weight(clock, 0.1), oclock, hundred, zero_hour, with_suffix, seconds)
        # 2pm-5pm, 4:00 am - 8:12 pm → two p m to five p m
        dash = pynini.cross(pynini.closure(" ", 0, 1) + pynini.union("-", "–") + pynini.closure(" ", 0, 1), " to ")
        graph = pynini.union(graph, with_suffix + dash + with_suffix)
        return self.wrap(text(graph)).optimize()
