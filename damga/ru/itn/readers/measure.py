from __future__ import annotations

import pynini

from ....core.rules import Rule
from ...lexicon import NOUNS
from .cardinal import SCALE_WORDS
from .common import text


class MeasureReader(Rule):
    """``пятьдесят пять процентов`` → 55 %, ``одна целая и одна десятая миллиона`` → 1,1 млн.  Units and currencies
    keep their word (``3 километра``), as Russian texts write them."""

    name = "measure"
    kind = "read"

    def build(self, digits: pynini.Fst, fraction: pynini.Fst, with_scale: pynini.Fst, variants: bool = False):
        percent_forms = pynini.union(*set(NOUNS["процент"][1] + NOUNS["процент"][2]))
        amount = pynini.union(digits, fraction, with_scale)
        percent = amount + pynini.cross(" " + percent_forms, " %")
        thousand = {"тыс.": ["тысяча", "тысячи", "тысяч", "тысячам", "тысячами", "тысячах"]}
        scale = pynini.union(*[pynini.cross(pynini.union(*forms), abbr) for abbr, forms in {**SCALE_WORDS, **thousand}.items()])
        fraction_scaled = fraction + pynini.accep(" ") + scale
        sign = pynini.closure(pynini.cross("минус ", "-"), 0, 1)
        return self.wrap(text(sign + pynini.union(percent, fraction_scaled))).optimize()


