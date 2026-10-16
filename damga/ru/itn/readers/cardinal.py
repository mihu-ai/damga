from __future__ import annotations

import pynini

from ....core.rules import DIGIT, Rule
from .common import spoken_cardinal, text, written

# Scale words written as abbreviations after a round number: двадцать миллионов → 20 млн.
SCALE_WORDS = {"млн": ["миллион", "миллиона", "миллионов", "миллиону", "миллионам", "миллионом", "миллионами",
                       "миллионе", "миллионах"],
               "млрд": ["миллиард", "миллиарда", "миллиардов", "миллиарду", "миллиардам", "миллиардом",
                        "миллиардами", "миллиарде", "миллиардах"],
               "трлн": ["триллион", "триллиона", "триллионов", "триллиону", "триллионам", "триллионом",
                        "триллионами", "триллионе", "триллионах"]}


class CardinalReader(Rule):
    """``двадцати пяти`` → 25, ``двадцать миллионов`` → 20 млн.  Zero, one and two stay words, as Russian texts write
    them (``два года``)."""

    name = "cardinal"
    kind = "read"

    def build(self, variants: bool = False, group: bool = True):
        number = spoken_cardinal()
        self.number = number
        small = pynini.union("0", "1", "2")
        self.big = (number @ pynini.difference(pynini.closure(DIGIT, 1), small) @ written(group)).optimize()
        self.digits = (number @ written(group)).optimize()
        scale = pynini.union(*[pynini.cross(pynini.union(*forms), abbr) for abbr, forms in SCALE_WORDS.items()])
        with_scale = (number @ pynini.closure(DIGIT, 1, 3)) + pynini.accep(" ") + scale
        words = pynini.closure(pynini.union(*"абвгдеёжзийклмнопрстуфхцчшщъыьэюя "))
        ends_in_scale = words + pynini.union(*[" " + w for forms in SCALE_WORDS.values() for w in forms])
        # "миллион" alone stays a word; "двадцать миллионов" is 20 млн (with_scale)
        big = pynini.difference(pynini.project(self.big, "input"), ends_in_scale) @ self.big
        # … and so do "тысячи", "тысяч" …, which alone mean "thousands" (тысячи людей)
        alone = pynini.union(*[w for forms in SCALE_WORDS.values() for w in forms],
                             "тысячи", "тысяч", "тысячам", "тысячами", "тысячах")
        big = pynini.difference(pynini.project(big, "input"), alone) @ big
        sign = pynini.closure(pynini.cross("минус ", "-"), 0, 1)
        fst = self.wrap(text(pynini.union(sign + big, pynini.cross("минус ", "-") + self.digits,
                                                     with_scale))).optimize()
        self.with_scale = with_scale
        return fst


