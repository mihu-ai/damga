from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NON_QUOTE, NONZERO_DIGIT, Rule, group_thousands


def optional_suffix() -> pynini.Fst:
    """`` suffix="da"`` → ``'da`` (absent → nothing)."""
    return pynini.closure(pynutil.delete(' suffix="') + pynutil.insert("'") + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"'), 0, 1)


def glued_suffix() -> pynini.Fst:
    """`` suffix="a"`` → ``a``: after a scale word the suffix is part of the word (``5 milyona``)."""
    return pynini.closure(pynutil.delete(' suffix="') + pynini.closure(NON_QUOTE, 1) + pynutil.delete('"'), 0, 1)


def written_number(group: bool = True, group_four_digits: bool = True) -> pynini.Fst:
    digits = pynini.closure(DIGIT, 1)
    return ((digits @ group_thousands(4 if group_four_digits else 5)) if group else digits).optimize()


def scaled_number() -> pynini.Fst:
    """``5000000`` → ``5 milyon``, ``128000000000`` → ``128 milyar``: a round number of millions or more written with
    its scale word (the ``scale_words`` option)."""
    head = NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)
    scale = pynini.union(pynini.cross("0" * 6, " milyon"), pynini.cross("0" * 9, " milyar"), pynini.cross("0" * 12, " trilyon"))
    return (head + scale).optimize()


def integer_field(group: bool = True, group_four_digits: bool = True, scale_words: bool = False,
                  tail: pynini.Fst | None = None) -> pynini.Fst:
    """``integer="…"`` (+ ``tail`` + suffix) → the written integer; see ``InverseNormalizer`` for the options."""
    tail = tail if tail is not None else pynini.accep("")
    plain = (pynutil.delete('integer="') + written_number(group, group_four_digits) + pynutil.delete('"') + tail
             + optional_suffix())
    if not scale_words:
        return plain.optimize()
    scaled = pynutil.delete('integer="') + scaled_number() + pynutil.delete('"') + glued_suffix()
    return pynini.union(plain, pynutil.add_weight(scaled, -1.0)).optimize()


class CardinalWriter(Rule):
    name = "cardinal"
    kind = "write"

    def build(self, variants: bool = False, group: bool = True, group_four_digits: bool = True,
                 scale_words: bool = False):
        optional_sign = pynini.closure(pynutil.delete('negative="') + pynini.accep("-") + pynutil.delete('" '), 0, 1)
        self.number = written_number(group, group_four_digits)
        graph = optional_sign + integer_field(group, group_four_digits, scale_words)
        return self.unwrap(graph)
