from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, SIGMA, Rule
from .cardinal import optional_sign, optional_suffix, soften_dort
from .number import CARDINAL, FRACTIONAL


def number_body() -> pynini.Fst:
    """``integer="6" sep="bare" fractional="05"`` → ``altı sıfır beş``; ``sep`` is ``nokta`` or ``bare``, absent
    it is ``virgül`` (the written Turkish decimal comma)."""
    integer = pynutil.delete('integer="') + (pynini.closure(DIGIT, 1) @ CARDINAL) + pynutil.delete('"')
    sep = pynini.union(
        pynutil.insert(" virgül "),
        pynini.cross(' sep="nokta"', " nokta "),
        pynini.cross(' sep="bare"', " "),
    )
    fractional = sep + pynutil.delete(' fractional="') + (pynini.closure(DIGIT, 1) @ FRACTIONAL) + pynutil.delete('"')
    return (integer + pynini.closure(fractional, 0, 1)).optimize()


def optional_quantity() -> pynini.Fst:
    """`` quantity="milyondan"`` → `` milyondan`` (the scale word after a point decimal, kept as written)."""
    return pynini.closure(pynutil.delete(' quantity="') + pynutil.insert(" ") + pynini.closure(NON_QUOTE, 1)
                          + pynutil.delete('"'), 0, 1)


_BACK_VOWEL = pynini.union(*"aıou")
_FRONT_VOWEL = pynini.union(*"eiöü")
_CONSONANT = pynini.difference(NON_QUOTE, pynini.union(_BACK_VOWEL, _FRONT_VOWEL))


def bucuk_with_suffix() -> pynini.Fst:
    """``2,5'luk`` / ``2,5'a`` → ``iki buçukluk`` / ``iki buçuğa``.  A back-vowel suffix cannot follow ``beş``, so the
    writer meant *buçuk*; reading ``beşluk`` would be wrong.  Weighted to win over ``number_body``."""
    integer = pynutil.delete('integer="') + (pynini.closure(DIGIT, 1) @ CARDINAL) + pynutil.delete('"')
    sep = pynini.closure(pynini.union(pynutil.delete(' sep="nokta"'), pynutil.delete(' sep="bare"')), 0, 1)
    back = pynini.closure(_CONSONANT) + _BACK_VOWEL + pynini.closure(NON_QUOTE)
    graph = (integer + sep + pynini.cross(' fractional="5"', " buçuk")
             + pynutil.delete(' suffix="') + back + pynutil.delete('"'))
    soften = pynini.cdrewrite(pynini.cross("buçuk", "buçuğ"), "", pynini.union(_BACK_VOWEL, _FRONT_VOWEL), SIGMA)
    return pynutil.add_weight((graph @ soften).optimize(), -1.0)


class DecimalWriter(Rule):
    name = "decimal"
    kind = "write"

    def build(self, variants: bool = False):
        group = pynini.union("0", pynini.difference(DIGIT, "0") + pynini.closure(DIGIT)) @ CARDINAL
        dotted = (pynutil.delete('dotted="') + group + pynini.closure(pynini.cross(".", " nokta ") + group, 2)
                  + pynutil.delete('"') + optional_suffix())
        body = pynini.union(number_body() + optional_quantity() + optional_suffix(), bucuk_with_suffix(), dotted)
        return (self.unwrap(optional_sign() + body) @ soften_dort()).optimize()
