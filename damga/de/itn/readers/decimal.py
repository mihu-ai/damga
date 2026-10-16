from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BIG_SCALES
from ...numbers import DIGIT_WORD
from .cardinal import text


def spoken_decimal(number: pynini.Fst) -> pynini.Fst:
    """``elf komma zwei`` → ``11,2``, ``null komma fünfzehn`` → ``0,15``."""
    digit = pynini.union(pynini.invert(DIGIT_WORD), pynini.cross("ein", "1"), pynini.cross("zwo", "2"))
    digits = digit + pynini.closure(pynutil.delete(" ") + digit)
    after = pynini.union(digits, number @ (pynini.union(*"123456789") + DIGIT))
    # "zweieinhalb", "anderthalb" stay words.
    return ((number @ pynini.closure(DIGIT, 1)) + pynini.cross(" komma ", ",") + after).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        self.number = spoken_decimal(number)
        scale = pynini.closure(pynini.union(*[pynini.cross(" " + w.lower(), " " + w) for s in BIG_SCALES for w in s]), 0, 1)
        sign = pynini.closure(pynini.cross("minus ", "-"), 0, 1)
        return self.wrap(text(sign + self.number + scale)).optimize()
