from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule, drop_space, string_map
from ...lexicon import MONTHS, YEAR_WORDS
from .cardinal import CardinalReader

_BACK = set("aıou"); _ROUND = set("ouüö"); _HARD = set("çfhkpsşt")

def _suffixes(word: str) -> list[str]:
    last_v = [c for c in word if c in "aeıioöuü"][-1]
    a = "a" if last_v in _BACK else "e"
    i = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[last_v]
    d = "t" if word[-1] in _HARD else "d"
    return [f"{d}{a}", f"{d}{a}n", f"{a}", f"{i}", f"{i}n", f"{i}nd{a}", f"{i}n{a}", f"{i}nd{a}n", f"l{a}", f"{i}nd{a}ki"]

class DateReader(Rule):
    name = "date"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        day = pynutil.insert('day="') + (cardinal.graph_no_zero @ pynini.union(*[str(i) for i in range(1, 32)])) + pynutil.insert('"')
        year_digits = cardinal.graph_no_zero @ (pynini.union("1", "2") + DIGIT + DIGIT + DIGIT)
        year = pynutil.insert('year="') + year_digits + pynutil.insert('"')
        # ``iki bin yirmi altıda`` → 2026'da: a suffixed 1xxx/2xxx number is a year, so date wins over cardinal.
        year_sfx = pynutil.insert('year="') + CardinalReader.with_suffix(year_digits) + pynutil.insert('"')

        month_plain = string_map([(m, m.capitalize().replace("I", "İ") if m[0] == "i" else m.capitalize()) for m in MONTHS])
        # ``mayısta`` and ``Mayıs'ta``.
        month_suffixed = pynini.union(*[
            pynini.cross(m + sep + s, m.capitalize() + "'" + s) for m in MONTHS for s in _suffixes(m) for sep in ("", "'")
        ])
        month = pynutil.insert('month="') + month_plain + pynutil.insert('"')
        month_sfx = pynutil.insert('month="') + month_suffixed + pynutil.insert('"')

        year_kw = pynutil.insert(' text="') + pynini.union(*YEAR_WORDS) + pynutil.insert('"')
        sp = pynini.accep(" ")
        graph = pynini.union(
            day + sp + month + sp + year,
            day + sp + month + sp + year_sfx,
            day + sp + month,
            day + sp + month_sfx,
            month + sp + year,
            month + sp + year_sfx,
            year_sfx,
            year + drop_space + year_kw,
            pynutil.add_weight(day + sp + month + sp + year + drop_space + year_kw, -0.1),
        )
        return self.wrap(graph.optimize())
