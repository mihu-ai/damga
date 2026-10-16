from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import MONTHS, TIES
from ...numbers import CARDINAL, ORDINAL, YEAR
from .cardinal import text
from .ordinal import ordinal_words

_ABBR = {"jan": "january", "feb": "february", "mar": "march", "apr": "april", "jun": "june", "jul": "july",
         "aug": "august", "sep": "september", "sept": "september", "oct": "october", "nov": "november",
         "dec": "december"}
_LETTERS = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz "))


def _capital(word: str) -> str:
    return word[0].upper() + word[1:]


def _day_word(d: int) -> str:
    return pynini.shortestpath(pynini.accep(str(d)) @ ORDINAL).string()


class DateReader(Rule):
    """Dates and decades: ``6 December 2012`` → ``the sixth of December twenty twelve``, ``1990s`` →
    ``nineteen nineties``.  Numeric dates are day first."""

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        day_digits = pynini.union(*[str(d) for d in range(1, 32)], *[f"0{d}" for d in range(1, 10)])
        day_plain = (day_digits @ pynini.union(pynutil.delete("0") + NONZERO_DIGIT, NONZERO_DIGIT, NONZERO_DIGIT + DIGIT)
                     @ ORDINAL)
        day_written = (day_digits + pynini.union("st", "nd", "rd", "th")) @ ordinal_words()
        day = pynini.union(day_plain, day_written)
        # "may" and "march" are also common words, so they name a month only when capitalised
        month = pynini.union(*[pynini.union(m, _capital(m)) if m not in ("may", "march") else pynini.accep(_capital(m))
                               for m in MONTHS],
                             *[pynini.cross(m.upper(), _capital(m)) for m in MONTHS],
                             *[pynini.cross(pynini.union(a, _capital(a), a.upper()) + pynini.closure(".", 0, 1), _capital(m))
                               for a, m in _ABBR.items()])
        year = (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT) @ YEAR
        sp = pynini.accep(" ")
        comma_year = pynini.closure(pynutil.delete(","), 0, 1) + sp + year

        # 19-20 March → the nineteenth to twentieth of March
        days = day + pynini.closure(pynini.union(pynini.accep(" and "), pynini.cross(pynini.union("-", "–"), " to ")) + day, 0, 1)
        day_first = pynutil.insert("the ") + days + pynutil.insert(" of") + sp + month + pynini.closure(comma_year, 0, 1)
        month_first = month + sp + day + pynini.closure(comma_year, 0, 1)
        # Jan-15-2020, Jan-15
        month_dashed = month + pynini.cross("-", " ") + day + pynini.closure(pynini.cross("-", " ") + year, 0, 1)

        # Numeric dates, day first.  ISO dates are reordered by the pre-hook: a branch that writes before it reads
        # would slow down every sentence.
        numeric = []
        for m in range(1, 13):
            name = _capital(MONTHS[m - 1])
            for d in range(1, 32):
                said = f"the {_day_word(d)} of {name}"
                slashed = pynini.union(*{f"{d:02d}/{m:02d}/", f"{d}/{m}/", f"{d:02d}.{m:02d}.", f"{d}.{m}.",
                                         f"{d:02d}-{m:02d}-", f"{d}-{m}-"})
                numeric.append(pynini.cross(slashed, said + " ") + year)

        # 1990s → nineteen nineties, 2000s → two thousands
        plural = pynini.union(*[pynini.cross(w, w[:-1] + "ies") for w, _ in TIES], pynini.cross("ten", "tens"),
                              pynini.cross("hundred", "hundreds"), pynini.cross("thousand", "thousands"))
        decade_year = pynini.union(pynini.difference(pynini.union("1", "2") + DIGIT + DIGIT + "0", "2010") @ YEAR,
                                   pynini.cross("2010", "twenty ten"))
        decade = (((pynini.union("1", "2") + DIGIT + DIGIT + "0") @ decade_year
                   @ (pynini.closure(_LETTERS + " ", 0, 1) + plural))
                  + pynutil.delete(pynini.union("s", "'s")))
        # 1960s-1980s, 1960s-80s → nineteen sixties to (nineteen) eighties
        short_decade = pynini.union(*[pynini.cross(d + "0", w[:-1] + "ies") for w, d in TIES]) + pynutil.delete(
            pynini.union("s", "'s"))
        decades = decade + pynini.cross(pynini.union("-", "–"), " to ") + pynini.union(decade, short_decade)
        graph = pynini.union(day_first, month_first, month_dashed, decade, decades, *numeric)
        if variants:
            # Other day/month orders and decades without the century; a table, so every branch reads before it writes.
            others = []
            for month_name in MONTHS:
                name = _capital(month_name)
                written_names = [name] if month_name in ("may", "march") else [name, month_name]
                for day_number in range(1, 32):
                    day_said = _day_word(day_number)
                    day_plain_said = pynini.shortestpath(pynini.accep(str(day_number)) @ CARDINAL).string()
                    for written_name in written_names:
                        for day_text in {str(day_number), f"{day_number:02d}"}:
                            others += [pynini.cross(f"{day_text} {written_name}", f"{name} the {day_said}"),
                                       pynini.cross(f"{day_text} {written_name}", f"{name} {day_said}"),
                                       pynini.cross(f"{day_text} {written_name}", f"{day_said} of {name}"),
                                       pynini.cross(f"{written_name} {day_text}", f"the {day_said} of {name}"),
                                       pynini.cross(f"{written_name} {day_text}", f"{name} the {day_said}"),
                                       pynini.cross(f"{day_text} {written_name}", f"{day_plain_said} {name}"),
                                       pynini.cross(f"{written_name} {day_text}", f"{name} {day_plain_said}")]
            orders = pynini.union(*others) + pynini.closure(comma_year, 0, 1)
            the_tens = (pynutil.delete(pynini.union("1", "2") + DIGIT)
                        + pynini.union(*[pynini.cross(d + "0", w[:-1] + "ies") for w, d in TIES])
                        + pynutil.delete(pynini.union("s", "'s")))
            graph = pynini.union(graph, pynutil.add_weight(orders, 0.6), pynutil.add_weight(the_tens, 0.6))
        return self.wrap(text(graph)).optimize()
