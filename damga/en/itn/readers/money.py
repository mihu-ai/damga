from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import QUANTITY_WORDS
from .cardinal import text

# spoken singular, plural → symbol
CURRENCIES = [("dollar", "dollars", "$"), ("us dollar", "us dollars", "$"), ("united states dollar", "united states dollars", "$"),
              ("euro", "euros", "€"), ("pound", "pounds", "£"), ("yen", "yen", "¥")]
MINOR = [("cent", "cents"), ("penny", "pence")]


class MoneyReader(Rule):
    """``five dollars`` → ``$5``, ``ten million euros`` → ``€10 million``, ``five percent`` → ``5%``."""

    name = "money"
    kind = "read"

    def build(self, number: pynini.Fst, written: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        no_scale = pynini.difference(pynini.project(written, "input"),
                                     pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz "))
                                     + pynini.union(*[" " + w for w in QUANTITY_WORDS]))
        written = no_scale @ written
        # "one fifty five dollars" → $155; plural only, since "two thirty dollar bills" are two $30 bills
        colloquial = (number @ pynini.union(*"123456789")) + pynutil.delete(" ") + (
            number @ (pynini.union(*"123456789") + DIGIT))
        amount = pynini.union(written, decimal)
        scale = pynini.union(*[pynini.accep(" " + w) for w in QUANTITY_WORDS])
        cents_value = (number @ pynini.union(*[str(n) for n in range(1, 100)])) @ pynini.union(
            pynutil.insert("0") + DIGIT, DIGIT + DIGIT)
        minor = pynini.union(*[pynini.union(" " + a, " " + b) for a, b in MINOR])
        # "five dollars fifty", "five dollars and fifty cents"; not "… euros and five point four billion"
        cents = pynutil.insert(".") + pynini.union(
            pynutil.delete(" ") + cents_value + pynutil.delete(pynini.closure(minor, 0, 1)),
            pynutil.delete(" and ") + cents_value + pynutil.delete(minor))
        branches = []
        for sg, pl, symbol in CURRENCIES:
            word = pynutil.delete(pynini.union(" " + sg, " " + pl))
            put = pynutil.insert(symbol)
            branches.append(put + amount + word)
            branches.append(put + pynutil.add_weight(colloquial, 0.1) + pynutil.delete(" " + pl))
            branches.append(put + amount + scale + word)
            if symbol != "¥":
                branches.append(put + written + word + cents)
        return self.wrap(text(pynini.union(*branches))).optimize()


class PercentReader(Rule):
    name = "percent"
    kind = "read"

    def build(self, written: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        sign = pynini.closure(pynini.cross("minus ", "-"), 0, 1)
        amount = pynini.union(written, decimal)
        percent = sign + amount + pynini.cross(pynini.union(" percent", " per cent"), "%")
        # five to ten percent → 5-10%
        span = amount + pynini.union(pynini.cross(" to ", "-"), " or ") + percent
        return self.wrap(text(pynini.union(percent, span))).optimize()
