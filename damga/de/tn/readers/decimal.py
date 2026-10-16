from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BIG_SCALES
from ...numbers import CARDINAL, DIGITS_SPOKEN, strip_thousands
from .cardinal import sign, text


def decimal_words() -> pynini.Fst:
    """``3,5`` → ``drei Komma fünf``, ``0,15`` → ``null Komma eins fünf``."""
    integer = strip_thousands() @ CARDINAL
    return (integer + pynini.cross(",", " Komma ") + (pynini.closure(DIGIT, 1) @ DIGITS_SPOKEN)).optimize()


# scale word abbreviations; the words are also accepted in lower case
_ABBR = {"Million": ("Mio.", "Mio"), "Milliarde": ("Mrd.", "Mrd"), "Billion": ("Bio.",)}


def scale_words() -> pynini.Fst:
    """`` Mio.`` / `` Millionen`` after a number → `` Millionen`` (singular after exactly one: ``eine Million``)."""
    plural = pynini.union(*[pynini.cross(pynini.union(pl, pl.lower(), *_ABBR.get(sg, ())), pl) for sg, pl in BIG_SCALES])
    return (pynutil.delete(" ") + pynutil.insert(" ") + plural).optimize()


def scaled() -> pynini.Fst:
    """``10 Mio.`` → ``zehn Millionen``, ``1 Mio.`` → ``eine Million``, ``1,6 Mrd.`` → ``eins Komma sechs Milliarden``."""
    integer = strip_thousands() @ CARDINAL
    many = pynini.difference(pynini.project(integer, "input"), "1") @ integer
    one = pynini.union(*[pynini.cross("1 " + pynini.union(sg, sg.lower(), *_ABBR.get(sg, ())), "eine " + sg)
                         for sg, _ in BIG_SCALES])
    return pynini.union(one, pynini.union(many, decimal_words()) + scale_words()).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(sign() + pynini.union(decimal_words(), scaled()))).optimize()
