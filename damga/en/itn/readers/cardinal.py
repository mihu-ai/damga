from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, SIGMA, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import CARDINAL_LONG, CARDINAL_LONG_NO_AND, HUNDREDS_COUNTED, YEAR_SPOKEN, group_thousands


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


def spoken_cardinal() -> pynini.Fst:
    """Spoken → digits, with or without the British "and", "a hundred" / "a thousand" for "one …", and counted in
    hundreds (``twenty one hundred`` → 2100)."""
    plain = pynini.union(pynini.invert(CARDINAL_LONG), pynini.invert(CARDINAL_LONG_NO_AND),
                         pynini.invert(HUNDREDS_COUNTED)).optimize()
    scale = pynini.union("hundred", "thousand", "million", "billion", "trillion")
    with_a = (pynini.cross("a ", "one ") + scale + pynini.closure(" " + SIGMA, 0, 1)) @ plain
    return pynini.union(plain, with_a).optimize()


def written_digits(group: bool = True) -> pynini.Fst:
    """``25000`` → ``25,000``, ``1300`` → ``1,300``; year-like 2000–2099 keep no comma."""
    if not group:
        return pynini.closure(DIGIT, 1).optimize()
    year_like = pynini.accep("20") + DIGIT + DIGIT
    four = pynini.difference(NONZERO_DIGIT + DIGIT + DIGIT + DIGIT, year_like)
    four_grouped = four @ (DIGIT + pynutil.insert(",") + DIGIT + DIGIT + DIGIT)
    return pynini.union(pynini.closure(DIGIT, 1, 3), year_like, four_grouped,
                        pynini.closure(DIGIT, 5) @ group_thousands(5)).optimize()


# A number that names something is written in digits even below ten: "paragraph eight" → "paragraph 8".
REFERENCE_WORDS = ("paragraph", "paragraphs", "article", "articles", "amendment", "amendments", "recital", "annex",
                   "chapter", "section", "page", "item", "rule", "figure", "table", "number", "phase", "level",
                   "tier", "stage", "category", "priority", "option", "objective", "pillar", "protocol", "title",
                   "part", "box", "round", "step", "grade", "room", "gate", "platform", "line", "lot", "block", "heading")


class CardinalReader(Rule):
    """``twenty five thousand`` → ``25,000``.  A lone number below ten stays a word (``four reports``)."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False, group: bool = True):
        number = spoken_cardinal()
        self.number = number                                      # spoken → digits, every value
        self.digits = (number @ written_digits(group)).optimize()
        small = pynini.union(*[str(d) for d in range(10)])
        self.big = (number @ pynini.difference(pynini.closure(DIGIT, 1), small) @ written_digits(group)).optimize()
        # Years from 1500 on only: "twelve thirty" is more likely a time than 1230.
        year = (pynini.invert(YEAR_SPOKEN) @ pynini.union(pynini.union("15", "16", "17", "18", "19") + DIGIT + DIGIT,
                                                   "20" + DIGIT + DIGIT)).optimize()
        self.year = year
        scale = pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS])
        # five million → 5 million, never 5000000
        with_scale = pynini.union(number @ pynini.closure(DIGIT, 1, 3), pynini.cross("a", "1")) + scale
        words = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz "))
        ends_in_scale = words + pynini.union(*[" " + w for w in QUANTITY_WORDS])
        self.big = (pynini.difference(pynini.project(self.big, "input"), ends_in_scale) @ self.big).optimize()
        self.digits = (pynini.difference(pynini.project(self.digits, "input"), ends_in_scale) @ self.digits).optimize()
        sign = pynini.closure(pynini.cross("minus ", "-"), 0, 1)
        reference = pynini.union(*REFERENCE_WORDS) + pynini.accep(" ") + self.digits
        # "two thirty", "seven eleven": without context (time, money, date) these stay as said, not "two 30"
        def said(digits: pynini.Fst) -> pynini.Fst:
            return pynini.project(number @ digits, "input")
        keep = pynini.union(said(NONZERO_DIGIT) + " " + said(NONZERO_DIGIT + DIGIT),
                            said(pynini.accep("1") + DIGIT) + " " + said(pynini.union(*"23456789") + DIGIT))
        graph = pynini.union(
            pynutil.add_weight(keep, 0.4),
            pynutil.add_weight(reference, -0.2),
            sign + self.big,
            pynini.cross("minus ", "-") + self.digits,
            pynutil.add_weight(year, -0.1),
            with_scale,
        )
        return self.wrap(text(graph)).optimize()
