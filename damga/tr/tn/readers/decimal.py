from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, TR_LOWER, Rule
from .cardinal import CardinalReader

# Scale words that may follow a written decimal (``12.3 milyon``).
QUANTITY_WORDS = ("milyon", "milyar", "trilyon")


class DecimalReader(Rule):
    """``3,14`` → ``üç virgül on dört``; a point decimal is read with ``nokta`` (``1.6`` → ``bir nokta altı``),
    except two fractional digits without a unit, read as two numbers (``6.97`` → ``altı doksan yedi``).  Three
    fractional digits are a thousands group.  The reading is chosen with the ``sep`` field (``nokta`` / ``bare``;
    absent = ``virgül``)."""

    name = "decimal"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        self.sign = pynini.closure(pynini.union(pynini.cross("-", 'negative="eksi" '), pynini.cross("+", 'negative="artı" ')), 0, 1)
        integer = pynutil.insert('integer="') + cardinal.number + pynutil.insert('"')
        fractional = pynutil.delete(",") + pynutil.insert(' fractional="') + pynini.closure(DIGIT, 1) + pynutil.insert('"')
        self.graph = (integer + fractional).optimize()

        plain = pynutil.insert('integer="') + pynini.union("0", pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 2)) + pynutil.insert('"')

        def dot(digits: pynini.Fst, sep: str, integer: pynini.Fst = plain) -> pynini.Fst:
            return (integer + pynutil.delete(".") + pynutil.insert(f' sep="{sep}" fractional="') + digits
                    + pynutil.insert('"'))

        one_or_long = pynini.union(DIGIT, pynini.closure(DIGIT, 4))
        two = DIGIT + DIGIT
        # In measures, percentages and before a scale word every point decimal is read with ``nokta``.
        self.dot_graph = pynini.union(dot(one_or_long, "nokta"), dot(two, "nokta")).optimize()
        def field(digits: pynini.Fst) -> pynini.Fst:
            return pynutil.insert('integer="') + digits + pynutil.insert('"')

        nonzero = pynini.difference(DIGIT, "0")
        self.dot_metre_graph = pynini.union(
            dot(one_or_long, "nokta"),
            dot(two, "bare", field(nonzero)),
            dot(two, "nokta", field(pynini.union("0", nonzero + pynini.closure(DIGIT, 1, 2)))),
        ).optimize()
        quantity = (pynutil.delete(" ") + pynutil.insert(' quantity="') + pynini.union(*QUANTITY_WORDS)
                    + pynini.closure(TR_LOWER) + pynutil.insert('"'))
        standalone = pynini.union(
            dot(one_or_long, "nokta") + cardinal.suffix,
            dot(two, "bare") + cardinal.suffix,
            self.dot_graph + quantity,
        )
        # Three or more dotted groups are an IP address or a version (``192.168.1.1``, ``3.2.1``), read part by part
        # with ``nokta``; groups of three after the first are a thousands-grouped number (``1.500.000``) instead.
        part = pynini.union("0", pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 2))
        thousands = part + pynini.closure("." + DIGIT + DIGIT + DIGIT, 1)
        dotted = pynini.difference(part + "." + part + pynini.closure("." + part, 1), thousands)
        dotted = pynutil.insert('dotted="') + dotted + pynutil.insert('"') + cardinal.suffix
        return self.wrap(pynini.union(self.sign + pynini.union(self.graph + cardinal.suffix, standalone),
                                                dotted)).optimize()
