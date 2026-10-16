from __future__ import annotations

import pynini

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from ...numbers import CARDINAL, DIGITS_SPOKEN, strip_thousands
from .cardinal import text


def decimal_words() -> pynini.Fst:
    """``3.14`` → ``three point one four``, ``.5`` → ``point five``, ``1.6 billion`` → ``one point six billion``."""
    integer = strip_thousands() @ CARDINAL
    fraction = pynini.cross(".", " point ") + (pynini.closure(DIGIT, 1) @ DIGITS_SPOKEN)
    number = pynini.union(integer + fraction, pynini.cross(".", "point ") + (pynini.closure(DIGIT, 1) @ DIGITS_SPOKEN))
    return number.optimize()


def quantity() -> pynini.Fst:
    """A scale word after a number (``5 million``) and its short forms (``€10m``, ``$50k``)."""
    return pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS],
                        pynini.cross(" bn", " billion"), pynini.cross("bn", " billion"),
                        pynini.cross(" m", " million"), pynini.cross("m", " million"),
                        pynini.cross(" tn", " trillion"),
                        # $30B, $5M, $50k
                        pynini.cross(pynini.union("b", "B"), " billion"), pynini.cross("M", " million"),
                        pynini.cross(pynini.union("k", "K"), " thousand")).optimize()


def dotted_words() -> pynini.Fst:
    """Versions (``3.2.1`` → ``three point two point one``) and IP addresses (``192.168.1.1``, read with *dot*).
    Groups of three after the first are a thousands-grouped number instead (``1.500.000``)."""
    part = pynini.union("0", NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2))
    thousands = part + pynini.closure("." + DIGIT + DIGIT + DIGIT, 1)
    byte = pynini.union(*[str(n) for n in range(256)])
    ip = byte + "." + byte + "." + byte + "." + byte
    version = pynini.difference(part + pynini.closure("." + part, 2), pynini.union(thousands, ip))
    say = pynini.union("0", NONZERO_DIGIT + pynini.closure(DIGIT)) @ CARDINAL
    return pynini.union(
        ip @ (say + pynini.closure(pynini.cross(".", " dot ") + say, 3, 3)),
        version @ (say + pynini.closure(pynini.cross(".", " point ") + say, 2)),
    ).optimize()


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, cardinal_number: pynini.Fst, variants: bool = False):
        self.number = decimal_words()
        sign = pynini.closure(pynini.union(pynini.cross("-", "minus "), pynini.cross("−", "minus ")), 0, 1)
        # A whole number before a scale word is a decimal token too, so "5 million" is one token.
        whole_with_scale = cardinal_number + pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS])
        return self.wrap(text(pynini.union(sign + pynini.union(
            self.number + pynini.closure(pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS]), 0, 1),
            whole_with_scale,
        ), dotted_words()))).optimize()
