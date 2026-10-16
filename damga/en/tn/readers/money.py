from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, DIGITS_SPOKEN, strip_thousands
from .cardinal import text
from .decimal import quantity
from .measure import load_units

# symbol or code → (singular, plural, minor singular, minor plural)
CURRENCIES = {
    "$": ("dollar", "dollars", "cent", "cents"), "USD": ("dollar", "dollars", "cent", "cents"),
    "US$": ("dollar", "dollars", "cent", "cents"),
    "€": ("euro", "euros", "cent", "cents"), "EUR": ("euro", "euros", "cent", "cents"),
    "£": ("pound", "pounds", "penny", "pence"), "GBP": ("pound", "pounds", "penny", "pence"),
    "¥": ("yen", "yen", "", ""), "JPY": ("yen", "yen", "", ""),
    "CHF": ("franc", "francs", "centime", "centimes"),
    "₹": ("rupee", "rupees", "paisa", "paise"), "INR": ("rupee", "rupees", "paisa", "paise"),
    "₩": ("won", "won", "", ""), "KRW": ("won", "won", "", ""),
}
# $20/mo, £10/wk → twenty dollars per month, ten pounds per week; units come from the measure table (€5/kg)
PERIODS = {"mo": "month", "month": "month", "yr": "year", "year": "year", "wk": "week", "week": "week", "d": "day",
           "day": "day", "hr": "hour", "h": "hour", "hour": "hour", "night": "night", "person": "person"}


class MoneyReader(Rule):
    """``$5.50`` → ``five dollars fifty cents``, ``€10m`` → ``ten million euros``."""

    name = "money"
    kind = "read"

    def build(self, variants: bool = False):
        integer = (strip_thousands() @ CARDINAL).optimize()
        many = (pynini.difference(pynini.project(integer, "input"), "1") @ integer).optimize()
        minor_digits = pynini.union(pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL), (NONZERO_DIGIT + DIGIT) @ CARDINAL)
        # one fractional digit or three and more: a decimal amount, not cents
        point = pynini.cross(".", " point ") + (pynini.union(DIGIT, pynini.closure(DIGIT, 3)) @ DIGITS_SPOKEN)
        scale = pynini.union(integer, integer + pynini.cross(".", " point ") + (pynini.closure(DIGIT, 1) @ DIGITS_SPOKEN))
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        branches = []
        for symbol, (sg, pl, minor_sg, minor_pl) in CURRENCIES.items():
            sym = pynutil.delete(pynini.escape(symbol)) + space
            amount = pynini.union(pynini.cross("1", "one " + sg), many + pynutil.insert(" " + pl))
            branches.append(sym + amount)
            branches.append(sym + scale + quantity() + pynutil.insert(" " + pl))
            branches.append(sym + integer + point + pynutil.insert(" " + pl))
            if minor_sg:
                minor = pynini.union(pynini.cross("01", "one " + minor_sg),
                                     (pynini.difference(DIGIT + DIGIT, pynini.union("01", "00")) @ minor_digits)
                                     + pynutil.insert(" " + minor_pl))
                whole = pynini.difference(pynini.project(amount, "input"), "0") @ amount   # $0.99 is ninety nine cents
                branches.append(sym + whole + pynutil.delete(".") + pynini.union(pynutil.delete("00"), pynutil.insert(" ") + minor))
                branches.append(sym + pynutil.delete(pynini.union("0.", ".")) + minor)
        money = pynini.union(*branches).optimize()
        per_unit = {**PERIODS, **{written: sg for written, sg, _ in load_units() if "/" not in written}}
        per = pynini.union(*[pynini.cross("/" + pynini.escape(k), " per " + v) for k, v in per_unit.items()])
        dash = pynini.cross(pynini.closure(" ", 0, 1) + pynini.union("-", "–") + pynini.closure(" ", 0, 1), " to ")
        graph = pynini.union(money + pynini.closure(per, 0, 1), money + dash + money)
        return self.wrap(text(graph)).optimize()
