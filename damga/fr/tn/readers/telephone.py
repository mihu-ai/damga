from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import DIGIT_WORD, TENS, TWO, UNIT, ZERO_WORD
from .cardinal import digits_spoken, text

# A pair is read as a number (``45`` → *quarante-cinq*), a leading zero as a digit (``06`` → *zéro six*).
PAIR = pynini.union(("0" + DIGIT) @ (ZERO_WORD + pynutil.insert(" ") + DIGIT_WORD), TENS).optimize()
FIRST = (NONZERO_DIGIT @ UNIT).optimize()
SEPARATORS = (" ", "-", ".", "")
# ``+33 (0)1 23 …``: the trunk zero in brackets is not said.
TRUNK_ZERO = pynutil.delete(pynini.union("(0)", " (0)", "(0) ", " (0) "))


def gap(sep: str) -> pynini.Fst:
    """The written separator between two groups → a short pause."""
    return pynutil.insert(", ") if not sep else pynini.cross(sep, ", ")


def national(sep: str) -> pynini.Fst:
    """The nine digits after the trunk zero or +33, in the French layout: ``1 23 45 67 89``."""
    return (FIRST + pynini.closure(gap(sep) + PAIR, 4, 4)).optimize()


def group() -> pynini.Fst:
    """A group of a foreign number: one digit, a pair, or three to five digits read one by one."""
    return pynini.union(DIGIT_WORD, PAIR, pynini.closure(DIGIT, 3, 5) @ digits_spoken()).optimize()


class TelephoneReader(Rule):
    """Phone numbers, a ``, `` pause between the groups: French ones in pairs (``06 12 34 56 78`` → *zéro six,
    douze, trente-quatre, …*), also after ``+33`` / ``0033``; other countries as grouped, or digit by digit when
    glued, as the code cannot be told from the number.

    A French number needs the leading 0 and five groups, a foreign one the + and at least seven digits after the
    code."""

    name = "telephone"
    kind = "read"

    def build(self, variants: bool = False):
        prefix = pynini.union(pynini.cross("+33", "plus trente-trois"), pynini.cross("0033", "zéro zéro trente-trois"))
        domestic, french = [], []
        for sep in SEPARATORS:
            domestic.append(pynini.cross("0", "zéro ") + FIRST + pynini.closure(gap(sep) + PAIR, 4, 4))
            french.append(prefix + gap(sep) + national(sep))
            french.append(prefix + TRUNK_ZERO + pynutil.insert(", ") + national(sep))

        code = pynini.cross("+", "plus ") + pynini.union(NONZERO_DIGIT @ UNIT, (NONZERO_DIGIT + DIGIT) @ TWO,
                                                         (NONZERO_DIGIT + DIGIT + DIGIT) @ digits_spoken())
        foreign = []
        for sep in (" ", "-", "."):
            # At least seven digits after the code, whatever the grouping.
            enough = (pynini.closure(pynini.closure(sep) + DIGIT, 7) + pynini.closure(sep)).optimize()
            groups = pynini.closure(gap(sep) + group(), 1)
            foreign.append(("+" + pynini.closure(DIGIT, 1, 3) + sep + enough) @ (code + groups))
        glued = pynini.cross("+", "plus ") + (pynini.closure(DIGIT, 8, 15) @ digits_spoken())

        graph = pynini.union(
            *domestic, *french,
            pynutil.add_weight(pynini.union(*foreign), 0.05),
            pynutil.add_weight(glued, 0.05),
        )
        return self.wrap(text(graph)).optimize()
