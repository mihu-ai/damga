from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import COUNTRY_CODES, NOT_YEAR
from ...numbers import DIGITS_SPOKEN
from .bank import PAUSE, _count
from .cardinal import text

# what a written phone number is made of besides its digits
_MARKS = pynini.union(" ", "/", "-", "(", ")", "+").optimize()
KEYWORDS = ("Telefonnummer", "Telefon", "Tel.", "Tel", "Fax", "Mobil", "Mobilnummer", "Handy", "Handynummer",
            "Rufnummer", "Ruf an", "Faxnummer")


def _group(low: int = 2) -> pynini.Fst:
    """A written group of ``low`` or more digits, read digit by digit (a year mark from ``prepare`` is dropped)."""
    return pynutil.delete(NOT_YEAR).ques + (pynini.closure(DIGIT, low) @ DIGITS_SPOKEN)


def _numbers(keyword: bool) -> pynini.Fst:
    """The digit groups of a phone number.  Groups after the first have at least two digits, so a following number
    ("… 1234567 2 Mal") stays its own word."""
    sep = pynini.cross(pynini.union(" ", "/", "-", " / ", " - ", "/ "), PAUSE)
    group = _group()
    rest = pynini.closure(sep + group, 1)
    # national: "030 1234567"; without a keyword the area code needs 2+ digits after the 0 (01/01/2020 is a date)
    area = "0" + NONZERO_DIGIT + pynini.closure(DIGIT, 1 if not keyword else 0, 3)
    national = (area @ DIGITS_SPOKEN) + rest
    # "(030) 1234567"
    paren = (pynutil.delete("(") + (area @ DIGITS_SPOKEN) + pynini.cross(pynini.union(") ", ")"), PAUSE) + group
             + pynini.closure(sep + group))
    # international: "+49 (0)30 12345678", "0049 30 12345678"; the trunk "(0)" is not read
    country = (pynini.union(pynini.cross("+", "plus "), pynini.cross("00", "null null "))
               + ((NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)) @ DIGITS_SPOKEN))
    trunk = pynini.union(sep, pynini.cross(pynini.union(" (0)", " (0) "), PAUSE))
    international = country + trunk + _group(1) + pynini.closure(sep + group)
    # "+493012345678": a known (prefix-free) country code is split off; after an unknown one the digits run on
    glued = pynini.closure(DIGIT, 8, 15)
    known = pynini.union(*COUNTRY_CODES)
    split = (glued @ (known + pynini.closure(DIGIT))) @ (
        (known @ DIGITS_SPOKEN) + pynutil.insert(PAUSE) + DIGITS_SPOKEN)
    other = pynini.difference(glued, known + pynini.closure(DIGIT)) @ DIGITS_SPOKEN
    plus_unbroken = pynini.cross("+", "plus ") + pynini.union(split, other)
    graph = pynini.union(national, paren, international, plus_unbroken)
    if keyword:   # after a keyword any digit groups count: "Tel. 1234567"
        graph = pynini.union(graph, _group(1) + pynini.closure(sep + group))
        shape = _count(DIGIT, 6, 17, pynini.union(_MARKS, NOT_YEAR))
    else:
        shape = _count(DIGIT, 8, 17, pynini.union(_MARKS, NOT_YEAR))
        # "+1 000 000 000" is an amount written in thousands, not a number to dial
        thousands = "+" + pynini.closure(DIGIT, 1, 3) + pynini.closure(" " + DIGIT + DIGIT + DIGIT, 1)
        shape = pynini.difference(shape, thousands)
    return (shape.optimize() @ graph).optimize()


def telephone() -> pynini.Fst:
    """``Tel. 030 1234567`` → ``Tel. null drei null, eins zwei drei vier fünf sechs sieben``.

    After a keyword 6+ digits count; without one, 8+ digits starting with ``0``, ``00`` or ``+``."""
    keyword = pynini.union(*KEYWORDS) + pynini.closure(":", 0, 1) + " "
    return pynini.union(keyword + _numbers(True), _numbers(False)).optimize()


class TelephoneReader(Rule):
    """German telephone and fax numbers, read digit by digit with a pause between the written groups."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        return self.wrap(text(telephone())).optimize()
