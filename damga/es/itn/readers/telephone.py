from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import DIGIT_WORD
from .cardinal import spoken_cardinal, text

_FIRST = pynini.union(*"6789")                    # Spanish numbers start with 6, 7, 8 or 9
_SEP = pynini.union(pynutil.delete(" "), pynutil.delete(", "))   # a comma may mark a pause
_SPACE = pynutil.insert(" ")


def _groups(number: pynini.Fst) -> tuple[pynini.Fst, pynini.Fst, pynini.Fst]:
    """The spoken groups of a telephone number → their digits: one digit word (``cero`` … ``nueve``), a two-digit
    number (``doce``, ``treinta y cuatro``) and a three-digit one (``seiscientos doce``).  A round hundred
    (``seiscientos``) is no group: ``novecientos doce`` is always 912, never 900 | 12."""
    one = pynini.invert(DIGIT_WORD)
    two = number @ (NONZERO_DIGIT + DIGIT)
    three = number @ pynini.difference(NONZERO_DIGIT + DIGIT ** 2, NONZERO_DIGIT + "00")
    return one.optimize(), two.optimize(), three.optimize()


def _national(number: pynini.Fst) -> pynini.Fst:
    """Nine digits starting 6-9, grouped as spoken: three digits and three pairs → ``612 34 56 78``, a pair, three
    digits and two pairs → ``91 234 56 78``, any other grouping → ``612 345 678``."""
    one, two, three = _groups(number)
    any_group = pynini.union(one, two, three)
    three_digits = pynini.union(one + _SEP + one + _SEP + one, three)
    pair = pynini.union(two, pynini.accep("cero") @ one + _SEP + one)       # "05" is read *cero cinco*
    mobile = (three_digits @ (_FIRST + DIGIT ** 2)) + (_SEP + _SPACE + pair) ** 3
    landline = (pair @ (_FIRST + DIGIT)) + _SEP + _SPACE + three_digits + (_SEP + _SPACE + pair) ** 2
    d3 = DIGIT ** 3
    plain = (any_group + pynini.closure(_SEP + any_group)) @ (_FIRST + DIGIT ** 8) @ (
        d3 + _SPACE + d3 + _SPACE + d3)
    return pynini.union(mobile, landline, pynutil.add_weight(plain, 0.1)).optimize()


class TelephoneReader(Rule):
    """Telephone numbers read out in digits or groups: a Spanish number (nine digits starting 6-9) →
    ``912 345 678``, optionally after ``más treinta y cuatro`` → ``+34``; another country code after ``más`` with
    seven digits or more; ten digits → ``123 123 5678``.  An ordinary nine-digit number is said with
    ``millones``/``mil``, which no group takes."""

    name = "telephone"
    kind = "read"

    def build(self, number: pynini.Fst, variants: bool = False):
        one, two, three = _groups(number)
        national = _national(number)
        spain = pynini.union(pynini.cross("más treinta y cuatro", "+34"), pynini.cross("más tres cuatro", "+34"),
                             pynini.cross("cero cero treinta y cuatro", "+34"))
        code = pynini.cross("más ", "+") + (spoken_cardinal() @ (NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)))
        digits = pynini.union(one, two, three)
        rest = (digits + pynini.closure(_SEP + digits)) @ pynini.closure(DIGIT, 7, 12)
        # ten digits → 3-3-4
        d3 = DIGIT ** 3
        ten = (digits + pynini.closure(_SEP + digits)) @ DIGIT ** 10 @ (d3 + _SPACE + d3 + _SPACE + DIGIT ** 4)
        graph = pynini.union(
            pynutil.add_weight(ten, 0.1),
            national,
            pynutil.add_weight(spain + _SEP + _SPACE + national, -0.1),
            pynutil.add_weight(code + _SEP + _SPACE + rest, 0.5),   # +34 and a Spanish number first
        )
        return self.wrap(text(graph)).optimize()
