from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, TR_LOWER, Rule
from ...lexicon import MONTHS


def capital(month: str) -> str:
    return ("İ" + month[1:]) if month[0] == "i" else month.capitalize()


class DateReader(Rule):
    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        day_num = pynini.union(*[str(d) for d in range(1, 32)] + [f"{d:02d}" for d in range(1, 10)])
        day = pynutil.insert('day="') + day_num + pynutil.insert('"')
        # A month name is written the way it was (``14 Haziran'da`` → *on dört Haziran'da*); a month written as digits
        # comes out capitalised, as Turkish writes a month in a date.
        month_name = pynini.union(*MONTHS, *[capital(m) for m in MONTHS])
        year_num = pynini.union("1", "2") + DIGIT + DIGIT + DIGIT
        year = pynutil.insert(' year="') + year_num + pynutil.insert('"')
        suffix = pynutil.delete("'") + pynutil.insert(' suffix="') + pynini.closure(TR_LOWER, 1) + pynutil.insert('"')
        sep = pynini.union(*[pynutil.delete(c) for c in "./-"])
        sp = pynutil.delete(" ")
        month = pynutil.insert(' month="')
        month_numeric = pynini.union(*[pynini.cross(d, f' month="{capital(m)}" month_digits="{d}"')
                                       for i, m in enumerate(MONTHS, 1) for d in dict.fromkeys((f"{i:02d}", str(i)))])
        graph = pynini.union(
            # ``28.10.2024'te``; the written month digits are kept for the variant that reads them as a number.
            day + sep + month_numeric + sep + year + pynini.closure(suffix, 0, 1),
            day + sp + month + month_name + pynutil.insert('"') + pynini.closure(sp + year, 0, 1) + pynini.closure(suffix, 0, 1),
            pynutil.insert('month="') + month_name + pynutil.insert('"') + sp + year + pynini.closure(suffix, 0, 1),
            pynutil.insert('year="') + year_num + pynutil.insert('"') + suffix,
        )
        return self.wrap(graph)
