from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import SIGMA, TR_LOWER, Rule, drop_space
from ...lexicon import QUANTITY_WORDS
from .cardinal import CardinalReader


class DecimalReader(Rule):
    name = "decimal"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        zeros = pynini.closure(pynini.cross("sıfır", "0") + drop_space)
        fractional = pynini.union(zeros + cardinal.graph_no_zero, pynini.cross("sıfır", "0"))
        self.fractional = fractional.optimize()

        integer = pynutil.insert('integer="') + cardinal.graph + pynutil.insert('"')
        no_integer = pynutil.insert('integer="0"')
        # A scale word after a decimal stays a word (``on iki virgül üç milyon`` → 12,3 milyon, ``iki buçuk milyar``
        # → 2,5 milyar), so the fractional part never swallows it (12,3000000 would be a different number).
        scale_words = pynini.union(*QUANTITY_WORDS)
        no_scale = pynini.difference(SIGMA, SIGMA + scale_words + SIGMA)
        # The suffix of the whole number sits on the last fractional word: ``yüzde otuz yedi nokta üçünün`` → %37,3'ünün.
        frac = pynutil.insert(' fractional="') + pynini.union(
            no_scale @ fractional, no_scale @ CardinalReader.with_suffix(fractional, anywhere=True)) + pynutil.insert('"')
        quantity = pynini.closure(pynutil.insert(' quantity="') + pynutil.delete(" ") + scale_words + pynini.closure(TR_LOWER)
                                  + pynutil.insert('"'), 0, 1)
        # ``bir nokta dokuz`` (a point decimal read out, as in English) is written with the Turkish comma: 1,9.
        virgul = pynini.union(
            pynini.union(integer + drop_space, no_integer) + pynutil.delete("virgül") + drop_space + frac,
            integer + drop_space + pynutil.delete("nokta") + drop_space + frac,
            integer + pynutil.delete(" buçuk") + pynutil.insert(' fractional="5"'),
        ) + quantity
        self.optional_minus = pynini.closure(
            pynutil.insert('negative="') + pynini.cross("eksi", "-") + pynutil.insert('" ') + drop_space, 0, 1)
        self.graph = virgul.optimize()
        # Three or more numbers joined by ``nokta`` are an IP address or a version (``3.2.1``), not a decimal.
        part = no_scale @ cardinal.graph
        dot = drop_space + pynini.cross("nokta", ".") + drop_space
        dotted = pynutil.insert('dotted="') + part + dot + part + pynini.closure(dot + part, 1) + pynutil.insert('"')
        return self.wrap(pynini.union(self.optional_minus + self.graph, dotted))
