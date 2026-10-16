from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from ...numbers import ENDINGS, ORDINAL_STEM
from .cardinal import text


def spoken_ordinal() -> pynini.Fst:
    """``dritten`` → ``3.``, ``zwanzigste`` → ``20.``, ``einundzwanzigsten`` → ``21.``: every ending."""
    below_million = pynini.union(*[str(n) for n in range(1, 10)]) + pynini.closure(DIGIT, 0, 5)
    stem = below_million @ ORDINAL_STEM
    with_ending = stem + pynini.union(*[pynutil.insert(e) for e in ENDINGS])
    return (pynini.invert(with_ending) + pynutil.insert(".")).optimize()


class OrdinalReader(Rule):
    """``im zwanzigsten jahrhundert`` → ``im 20. Jahrhundert``; first to twelfth stay words (``zum dritten Mal``)
    unless a month follows (see DateReader)."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        self.number = spoken_ordinal()
        small = pynini.union(*[f"{n}." for n in range(1, 13)])
        big = self.number @ pynini.difference(pynini.closure(DIGIT, 1) + ".", small)
        return self.wrap(text(big)).optimize()


class DateReader(Rule):
    """``am dritten oktober zweitausendzwölf`` → ``am 3. Oktober 2012``, ``am dritten zehnten …`` → ``am 3.10.…``."""

    name = "date"
    kind = "read"

    def build(self, ordinal: pynini.Fst, year: pynini.Fst, variants: bool = False):
        day = ordinal @ (pynini.union(*[str(d) for d in range(1, 32)]) + ".")
        month = pynini.union(*[pynini.cross(m.lower(), m) for m in MONTHS])
        sp = pynini.accep(" ")
        days = day + pynini.closure(pynini.union(" und ", " bis ") + day, 0, 1)
        graph = days + sp + month + pynini.closure(sp + year, 0, 1)
        # the month said as its number: dreiundzwanzigsten elften → 23.11.
        month_number = ordinal @ (pynini.union(*[str(m) for m in range(1, 13)]) + ".")
        numeric = day + pynutil.delete(" ") + month_number + pynini.closure(pynutil.delete(" ") + year, 0, 1)
        month_year = month + sp + year                          # im januar zweitausendneun → im Januar 2009
        return self.wrap(text(pynini.union(graph, numeric, month_year))).optimize()
