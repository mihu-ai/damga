from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import MONTHS
from ...numbers import ORDINAL_STEM, YEAR
from .cardinal import text

_ABBR = {"Jan.": "Januar", "Feb.": "Februar", "Febr.": "Februar", "Mär.": "März", "Mrz.": "März", "Apr.": "April",
         "Jun.": "Juni", "Jul.": "Juli", "Aug.": "August", "Sept.": "September", "Sep.": "September", "Okt.": "Oktober",
         "Nov.": "November", "Dez.": "Dezember"}
# The ending of an ordinal follows the word before it: "am 3. Oktober" → dritten, "der 3. Oktober" → dritte.
WEAK = ("der", "die", "das", "Der", "Die", "Das")
STRONG_EN = ("am", "Am", "vom", "Vom", "zum", "Zum", "im", "Im", "beim", "dem", "den", "des", "Dem", "Den", "Des",
             "einem", "einen", "eines", "seinem", "ihrem", "diesem", "jedem", "dieses", "zur", "vor", "seit", "bis")


def day_stem() -> pynini.Fst:
    days = pynini.union(*[str(d) for d in range(1, 32)], *[f"0{d}" for d in range(1, 10)])
    return days @ pynini.union(pynutil.delete("0") + pynini.union(*"123456789"), pynini.union(*"123456789"),
                               pynini.union(*"123") + DIGIT) @ ORDINAL_STEM


class DateReader(Rule):
    """``am 3. Oktober 2012`` → ``am dritten Oktober zweitausendzwölf``, ``der 3. Oktober`` → ``der dritte
    Oktober``, ``3. Oktober`` → ``dritten Oktober``, ``03.10.2012`` → ``dritten zehnten zweitausendzwölf``,
    ``1990er`` → ``neunzehnhundertneunziger``."""

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        stem = day_stem()
        # Jänner and Feber: the Austrian January and February; a month typed in lower case (3. juli) is the month
        named = {**{m: m for m in MONTHS}, "Jänner": "Jänner", "Feber": "Feber", **_ABBR}
        month = pynini.union(*[pynini.cross(w, m) for k, m in named.items() for w in {k, k.lower()}])
        year = (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ YEAR
        sp = pynini.accep(" ")
        with_year = pynini.closure(sp + year, 0, 1)

        def day(ending: str) -> pynini.Fst:
            # 3. und 4. Oktober → dritten und vierten Oktober
            one = stem + pynutil.delete(".") + pynutil.insert(ending)
            return one + pynini.closure(pynini.union(pynini.accep(" und "), pynini.cross(pynini.union("-", "–", " bis "), " bis "))
                                        + one, 0, 1)

        weak = pynini.union(*WEAK) + sp + day("e") + sp + month + with_year
        strong = pynini.union(*STRONG_EN) + sp + day("en") + sp + month + with_year
        bare = day("en") + sp + month + with_year
        month_num = pynini.union(*[pynini.cross(f"{i:02d}", m) for i, m in enumerate(MONTHS, 1)],
                                 *[pynini.cross(str(i), m) for i, m in enumerate(MONTHS, 1)])
        # 03.10.2012 → dritten zehnten zweitausendzwölf; 23.11. → dreiundzwanzigsten elften: a month written as a
        # number is said as one
        month_ordinal = (pynini.union(*[str(i) for i in range(1, 13)], *[f"0{i}" for i in range(1, 10)])
                         @ pynini.union(pynutil.delete("0") + pynini.union(*"123456789"), pynini.union(*"123456789"),
                                        "10", "11", "12") @ ORDINAL_STEM) + pynutil.insert("en")
        year_part = pynini.union(pynini.cross(".", " ") + ((pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ YEAR),
                                 pynutil.delete("."))
        numeric = stem + pynutil.insert("en") + pynini.cross(".", " ") + month_ordinal + year_part
        numeric_named = stem + pynutil.insert("en") + pynini.cross(".", " ") + month_num + year_part
        # 1990er → neunzehnhundertneunziger, 90er → neunziger
        decade = pynini.union(((pynini.union("1", "2") + DIGIT + DIGIT + "0") @ YEAR) + pynini.cross("er", "er"),
                              pynini.union(*[pynini.cross(d + "0er", w) for w, d in
                                             [("zwanziger", "2"), ("dreißiger", "3"), ("vierziger", "4"), ("fünfziger", "5"),
                                              ("sechziger", "6"), ("siebziger", "7"), ("achtziger", "8"), ("neunziger", "9")]]))
        decade = decade + pynini.closure(pynini.union("n", pynini.cross("-Jahre", " Jahre"), pynini.cross("-Jahren", " Jahren")), 0, 1)
        graph = pynini.union(weak, strong, bare, numeric, decade)
        if variants:
            graph = pynini.union(graph, pynutil.add_weight(numeric_named, 0.5))   # 03.10.2012 → dritten Oktober …
        return self.wrap(text(graph)).optimize()
