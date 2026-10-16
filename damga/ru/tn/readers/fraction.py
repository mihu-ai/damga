from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...lexicon import GENDER_MARKS
from ...numbers import cardinal, ordinal
from .common import ANY_CASE_MARK, ANY_GENDER_MARK, cased, text

# Denominators of a proper fraction written with a slash; a larger one (5/12) is left as it is
# (a house number or a date).
DENOMINATORS = (*range(2, 11), 100)


def _ordinal_after(numerator: int, case: str) -> tuple[str, str]:
    """The form of the denominator: after 1 (21 …) the singular feminine in the case of the whole (одна вторая,
    одной второй); after 2–4 and the rest the genitive plural in the nominative and accusative (три четвертых),
    the plural in the case of the whole otherwise (трем четвертым)."""
    if numerator % 10 == 1 and numerator % 100 != 11:
        return case, "f"
    return ("gen", "pl") if case in ("nom", "acc") else (case, "pl")


class FractionReader(Rule):
    """A proper fraction with a slash, the numerator feminine and the denominator an ordinal: ``3/4`` → три четвертых,
    ``до 1/2`` → до одной второй.  Dates are written with dots in Russian, so a slash does not compete with them."""

    name = "fraction"
    kind = "read"

    def build(self, variants: bool = False):
        # the pre-hook may mark the denominator for the noun after it (1/2 тонны): the noun does not change it
        gender = pynini.closure(pynutil.delete(pynini.union(*GENDER_MARKS.values())), 0, 1)

        def reading(case: str) -> pynini.Fst:
            out = []
            for d in DENOMINATORS:
                for n in range(1, d):
                    den_case, gnum = _ordinal_after(n, case)
                    out.append((str(n) @ cardinal(case, "f")) + pynini.cross("/", " ") + gender
                               + (str(d) @ ordinal(den_case, gnum)))
            return pynini.union(*out).optimize()

        round_clock = ANY_CASE_MARK + ANY_GENDER_MARK + pynini.cross("24/7", "двадцать четыре на семь")
        return self.wrap(text(pynini.union(cased(reading, variants=variants), round_clock))).optimize()
