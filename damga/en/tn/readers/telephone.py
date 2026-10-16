from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...numbers import COUNTRY_CODES, DIGITS_SPOKEN
from .cardinal import text

PAUSE = ", "                       # between the written groups
NOT_ONE = pynini.difference(DIGIT, "1").optimize()
TWO_TO_NINE = pynini.difference(DIGIT, pynini.union("0", "1")).optimize()
SPOKEN = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz ,")).optimize()


def _digits(low: int, high: int) -> pynini.Fst:
    return pynini.closure(DIGIT, low, high) @ DIGITS_SPOKEN


def north_american() -> pynini.Fst:
    """``(212) 555-1234`` → ``two one two, five five five, one two three four``.

    With spaces only, the area code and the exchange must start with 2 to 9 (dashes, points or brackets mark the
    shape as a phone number whatever the digits)."""
    def area(first: pynini.Fst) -> pynini.Fst:
        return pynini.union(pynini.cross("800", "eight hundred"),
                            pynini.difference(first + DIGIT + DIGIT, "800") @ DIGITS_SPOKEN)

    def exchange(first: pynini.Fst) -> pynini.Fst:
        return (first + DIGIT + DIGIT) @ DIGITS_SPOKEN
    line = _digits(4, 4)

    def body(sep: str, first: pynini.Fst) -> pynini.Fst:
        gap = pynini.cross(sep, PAUSE)
        return area(first) + gap + exchange(first) + gap + line

    paren = (pynutil.delete("(") + area(DIGIT) + pynutil.delete(")") + pynini.closure(pynutil.delete(pynini.union(" ", "-")), 0, 1)
             + pynutil.insert(PAUSE) + exchange(DIGIT) + pynini.cross(pynini.union("-", ".", " "), PAUSE) + line)
    numbers = pynini.union(body("-", DIGIT), body(".", DIGIT), body(" ", TWO_TO_NINE), paren)
    country = pynini.union(pynini.cross("+1", "plus one"), pynini.cross("1", "one"))
    prefix = pynini.closure(country + pynini.cross(pynini.union("-", ".", " "), PAUSE), 0, 1)
    # +12125551234: unwritten groups, but a North American number has only one shape
    glued = (pynini.cross("+1", "plus one") + pynutil.insert(PAUSE) + area(TWO_TO_NINE) + pynutil.insert(PAUSE)
             + exchange(TWO_TO_NINE) + pynutil.insert(PAUSE) + line)
    return pynini.union(prefix + numbers, country + pynutil.insert(PAUSE) + paren, glued).optimize()


NANP_GLUED = "1" + TWO_TO_NINE + DIGIT + DIGIT + TWO_TO_NINE + DIGIT + DIGIT + DIGIT + DIGIT + DIGIT + DIGIT


def glued_international() -> pynini.Fst:
    """``+442079460958`` → ``plus four four, two zero seven …``; a known country code is split off with a pause.
    ``+1`` with ten digits is left to ``north_american``."""
    code = pynini.union(*COUNTRY_CODES).optimize()
    digits = pynini.closure(DIGIT, 8, 15)
    known = pynini.intersect(pynini.difference(digits, NANP_GLUED), code + pynini.closure(DIGIT)).optimize()
    unknown = pynini.difference(digits, code + pynini.closure(DIGIT)).optimize()
    read = pynini.union(known @ ((code @ DIGITS_SPOKEN) + pynutil.insert(PAUSE) + DIGITS_SPOKEN),
                        unknown @ DIGITS_SPOKEN)
    return (pynini.cross("+", "plus ") + read).optimize()


def extension() -> pynini.Fst:
    """`` ext. 123``, `` ext 123``, `` x123`` (the pre-hook writes ``x 123``) → ``, extension one two three``."""
    word = pynini.union("ext.", "ext", "Ext.", "Ext", "x")
    return (pynini.cross(" ", PAUSE) + pynini.cross(word, "extension") + pynini.cross(pynini.closure(" ", 0, 1), " ")
            + _digits(1, 5)).optimize()


class TelephoneReader(Rule):
    """``+44 20 7946 0958`` → ``plus four four, two zero, seven nine four six, zero nine five eight``: digit by digit
    with a pause between the written groups, optionally followed by an extension."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        group = _digits(2, 4)
        sep = pynini.cross(pynini.union(" ", "-"), PAUSE)
        # +1 is left to north_american()
        international = pynini.cross("+", "plus ") + ((NOT_ONE + pynini.closure(DIGIT, 0, 2)) @ DIGITS_SPOKEN)
        trunk = ("0" + pynini.closure(DIGIT, 1, 4)) @ DIGITS_SPOKEN
        # +44 (0)20 …: the bracketed trunk 0 is not read
        bracket_trunk = pynini.cross(pynini.union(" (0)", " (0) ", "(0)", "(0) "), PAUSE)
        # US social security number: 111-11-1111
        ssn = _digits(3, 3) + pynini.cross("-", PAUSE) + _digits(2, 2) + pynini.cross("-", PAUSE) + _digits(4, 4)
        graph = pynini.union(international + pynini.union(sep, bracket_trunk) + _digits(1, 4)
                             + pynini.closure(sep + group, 1, 4),
                             trunk + pynini.closure(sep + group, 2, 4),
                             north_american(),
                             glued_international(),
                             ssn)
        graph = (graph + pynini.closure(extension(), 0, 1)).optimize()
        if variants:
            # zero as "oh" with the pauses dropped; toll-free 800 digit by digit
            oh = pynini.cdrewrite(pynini.cross("zero", "oh"), "", "", SPOKEN)
            run_on = pynini.cdrewrite(pynini.cross(PAUSE, " "), "", "", SPOKEN)
            eight_zero_zero = pynini.cdrewrite(pynini.cross("eight hundred", "eight zero zero"), "", "", SPOKEN)
            graph = pynini.union(graph,
                                 pynutil.add_weight(graph @ run_on @ oh, 0.5),
                                 pynutil.add_weight(graph @ eight_zero_zero, 0.5))
        return self.wrap(text(graph)).optimize()
