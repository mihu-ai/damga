from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASES, MONTHS_ANY, MONTHS_GEN, ORD_SUFFIX, YEAR_FORMS
from ...numbers import CENTURY_FORMS, ROMAN, ordinal
from .common import text, with_one_thousand


class DateReader(Rule):
    """``в две тысячи десятом году`` → в 2010 году, ``седьмого августа две тысячи четырнадцатого года`` →
    7 августа 2014 года."""

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        sp = pynini.accep(" ")
        singular = with_one_thousand(pynini.union(*[pynini.invert(ordinal(c, g)) for c in CASES
                                                     for g in ("m", "n")])).optimize()
        plural = pynini.union(*[pynini.invert(ordinal(c, "pl")) + pynutil.insert("-" + ORD_SUFFIX["pl"][i])
                                for i, c in enumerate(CASES)])
        plural = with_one_thousand(plural).optimize()
        year_nouns_sg = pynini.union(*[f for f, (_, g) in YEAR_FORMS.items() if g == "m"])
        year_nouns_pl = pynini.union(*[f for f, (_, g) in YEAR_FORMS.items() if g == "pl"])
        year_digits = pynini.closure(DIGIT, 1, 4)
        # "в тысяча девятьсот шестьдесят втором тысяча девятьсот шестьдесят пятом годах" → в 1962—1965 годах
        spans = pynini.union(*[(pynini.invert(ordinal(c, "m")) @ year_digits) + pynini.cross(" ", "—")
                               + (pynini.invert(ordinal(c, "m")) @ year_digits) for c in CASES])
        years = pynini.union((singular @ year_digits) + sp + year_nouns_sg, plural + sp + year_nouns_pl,
                             spans + sp + year_nouns_pl)

        day = singular @ pynini.union(*[str(d) for d in range(1, 32)])
        # ноль второго мая: the leading zero of a day written 02 said aloud
        day = pynini.union(day, pynutil.delete("ноль ") + (singular @ pynini.union(*"123456789")))
        year_gen = with_one_thousand(pynini.invert(ordinal("gen", "m"))) @ (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT)
        # тридцать первого января ноль шестого → 31 января 06-го, as восемьдесят шестого → 86-го
        short_year = (pynini.cross("ноль ", "0") + (pynini.invert(ordinal("gen", "m")) @ pynini.union(*"123456789"))
                      + pynutil.insert("-го"))
        date = day + sp + pynini.union(*MONTHS_GEN) + pynini.closure(
            sp + pynini.union(year_gen + pynini.closure(pynini.accep(" года"), 0, 1), short_year), 0, 1)
        month_year = pynini.union(*MONTHS_ANY) + sp + year_gen + pynini.closure(pynini.accep(" года"), 0, 1)
        bare = pynini.accep("в ") + (with_one_thousand(pynini.invert(ordinal("prep", "m"))) @ (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT))
        # двадцать первого века → XXI века
        centuries = pynini.union(*[(pynini.invert(ordinal(c, g)) @ pynini.invert(ROMAN)) + sp + form
                                   for form, (c, g) in CENTURY_FORMS.items() if not form.endswith(".")])
        return self.wrap(text(pynini.union(years, date, month_year, bare, centuries))).optimize()
