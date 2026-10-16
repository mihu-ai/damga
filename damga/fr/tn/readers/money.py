from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_FEM, strip_thousands
from .cardinal import text
from .decimal import decimal_words

# symbol → (singular, plural, feminine, minor singular, minor plural)
CURRENCIES = {
    "€": ("euro", "euros", False, "centime", "centimes"), "EUR": ("euro", "euros", False, "centime", "centimes"),
    "$": ("dollar", "dollars", False, "cent", "cents"), "USD": ("dollar", "dollars", False, "cent", "cents"),
    "£": ("livre", "livres", True, "penny", "pence"), "GBP": ("livre", "livres", True, "penny", "pence"),
    "CHF": ("franc suisse", "francs suisses", False, "centime", "centimes"),
}
SCALES = {"M": "millions", "Md": "milliards", "Mds": "milliards", "millions": "millions", "million": "million",
          "milliards": "milliards", "milliard": "milliard"}


class MoneyReader(Rule):
    """``5 €`` / ``€5`` → ``cinq euros``, ``1,50 €`` → ``un euro cinquante``, ``10 M€`` → ``dix millions
    d'euros``."""

    name = "money"
    kind = "read"

    def build(self, variants: bool = False):
        sp = pynutil.delete(pynini.closure(pynini.union(" ", " ", " "), 0, 1))
        branches = []
        for symbol, (sg, pl, fem, minor_sg, minor_pl) in CURRENCIES.items():
            card = CARDINAL_FEM if fem else CARDINAL
            integer = strip_thousands() @ card
            one = pynini.union("1") @ card
            many = pynini.difference(pynini.project(integer, "input"), pynini.union("0", "1")) @ integer
            amount = pynini.union(one + pynutil.insert(" " + sg), many + pynutil.insert(" " + pl))
            sym = pynutil.delete(pynini.escape(symbol))
            cents_digits = pynini.union(pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL), (NONZERO_DIGIT + DIGIT) @ CARDINAL)
            cents = pynini.union(pynutil.delete("00"), pynutil.insert(" ") + cents_digits)   # un euro cinquante
            only_cents = pynini.union(
                pynini.cross("0,01", f"un {minor_sg}"),
                pynutil.delete("0,") + (pynini.difference(DIGIT + DIGIT, pynini.union("00", "01")) @ cents_digits)
                + pynutil.insert(" " + minor_pl))
            value = pynini.union(amount, amount + pynutil.delete(",") + cents, only_cents)
            elided = "d'" if pl[0] in "aeiouéè" else "de "
            scale_word = pynini.union(*[pynini.cross(pynini.union(" " + k, k), " " + v) for k, v in SCALES.items()])
            scaled = pynini.union(integer, decimal_words(fem=False)) + scale_word
            if variants:
                # 2,5 milliards € → deux milliards et demi d'euros (another reading, see decimal.half_with_scale)
                scaled = pynini.union(scaled, pynutil.add_weight((strip_thousands() @ CARDINAL) + pynutil.delete(",5")
                                                                 + scale_word + pynutil.insert(" et demi"), 0.3))
            scaled = scaled + pynutil.insert(f" {elided}{pl}")
            for v in (value, scaled):
                branches.append(v + sp + sym)          # 5 €, 10 M€, 10 millions €
                branches.append(sym + sp + v)          # €5, EUR 10 millions
        return self.wrap(text(pynini.union(*branches))).optimize()
