from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASE_MARKS, GENDER_MARKS, NOUNS, RANGE_DASH
from ...numbers import cardinal, noun_form, strip_groups
from .common import text


class RangeReader(Rule):
    """``90—97%`` → от девяноста до девяноста семи процентов (years as ordinals); a score, two numbers under 100 the
    first not less than the second, is said as it is written: ``2-1`` → два один."""

    name = "range"
    kind = "read"

    def build(self, variants: bool = False):
        number = strip_groups()
        year = pynini.union("1", "2") + DIGIT + DIGIT + DIGIT
        dash = pynutil.delete(pynini.union("-", "–", "—", RANGE_DASH))
        plain = pynini.difference(pynini.project(number, "input"), year) @ number @ cardinal("gen", "m")
        counts = pynutil.insert("от ") + plain + dash + pynutil.insert(" до ") + plain
        # a score, 2-1, 1-1, 3-0: two small numbers, the first not less than the second, said one after the other
        dashes = pynini.union("-", "–", "—", RANGE_DASH)
        score = pynini.union(*[(str(a) @ cardinal("nom", "m")) + pynini.cross(dashes, " ")
                               + (pynini.union(*[str(b) for b in range(a + 1)]) @ cardinal("nom", "m"))
                               for a in range(100)]).optimize()
        ranged = pynini.difference(pynini.project(counts, "input"), pynini.project(score, "input")) @ counts
        percent = counts + pynutil.delete(pynini.closure(" ", 0, 1) + "%") + pynutil.insert(" " + noun_form(NOUNS["процент"], "gen", "many"))
        # a bare span of years, as in "(1824 — 1910)": both years said as they are written
        years = year @ cardinal("nom", "m")
        year_span = years + pynini.cross(pynini.union("-", "–", "—", RANGE_DASH), " — ") + years
        marks = pynini.closure(pynutil.delete(pynini.union(*CASE_MARKS.values(), *GENDER_MARKS.values())), 0, 2)
        return self.wrap(text(marks + pynini.union(ranged, score, percent, year_span))).optimize()
