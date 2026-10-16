from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_ATTRIBUTIVE, strip_thousands
from .cardinal import text
from .decimal import decimal_words, scaled

# symbol or code → (major, minor); German uses the same word for one and many (ein Euro, fünf Euro)
CURRENCIES = {"€": ("Euro", "Cent"), "EUR": ("Euro", "Cent"), "$": ("Dollar", "Cent"), "USD": ("Dollar", "Cent"),
              "US$": ("Dollar", "Cent"), "£": ("Pfund", "Pence"), "GBP": ("Pfund", "Pence"),
              "CHF": ("Franken", "Rappen"), "¥": ("Yen", ""), "JPY": ("Yen", "")}


class MoneyReader(Rule):
    """``1,50 €`` → ``ein Euro fünfzig``, ``EUR 10 Mio.`` → ``zehn Millionen Euro``."""

    name = "money"
    kind = "read"

    def build(self, variants: bool = False):
        integer = (strip_thousands() @ CARDINAL_ATTRIBUTIVE).optimize()
        cents = pynini.union(pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL), (NONZERO_DIGIT + DIGIT) @ CARDINAL)
        # before the word for the cents: 0,01 € → ein Cent
        minor_cents = pynini.union(pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL_ATTRIBUTIVE),
                                   (NONZERO_DIGIT + DIGIT) @ CARDINAL_ATTRIBUTIVE)
        # two digits after the comma are cents (1,50 € → ein Euro fünfzig); one or three and more are a decimal
        not_cents = pynini.closure(DIGIT, 1) + "," + pynini.union(DIGIT, pynini.closure(DIGIT, 3))
        amount_scaled = pynini.union(scaled(), not_cents @ decimal_words())
        space = pynutil.delete(pynini.closure(pynini.union(" ", " "), 0, 1))
        majors: dict[tuple[str, str], list[str]] = {}
        for symbol, (major, minor) in CURRENCIES.items():
            majors.setdefault((major, minor), []).append(symbol)
        whole = pynini.difference(pynini.project(integer, "input"), "0") @ integer   # 0,50 € is fünfzig Cent
        cents_part = pynutil.delete(",") + pynini.union(pynutil.delete("00"), pynutil.delete(pynini.union("-", "–")),
                                                        pynutil.insert(" ") + cents)
        branches = []
        # one branch per currency word, not per symbol; in "1,50 €" the word must come before the cents
        for (major, minor), symbols in majors.items():
            sym = pynini.union(*[pynini.escape(x) for x in symbols])
            say = pynini.cross(sym, " " + major)
            prefix = pynutil.delete(sym) + space + pynini.union(
                integer + pynutil.insert(" " + major),
                whole + pynutil.insert(" " + major) + cents_part,
                amount_scaled + pynutil.insert(" " + major),
                *([pynutil.delete("0,") + minor_cents + pynutil.insert(" " + minor)] if minor else []))
            suffix = pynini.union(
                pynini.union(integer, amount_scaled) + space + say,
                whole + pynutil.insert(" " + major) + cents_part + space + pynutil.delete(sym),
                *([pynutil.delete("0,") + minor_cents + space + pynini.cross(sym, " " + minor)] if minor else []))
            branches += [prefix, suffix]
        # written with the word: 1 Euro → ein Euro (not "eins Euro"); 7,80 Euro → sieben Euro achtzig
        words = ("Euro", "Cent", "Dollar", "Pfund", "Franken", "Rappen", "Yen")
        branches.append(integer + pynini.accep(" ") + pynini.union(*words))
        for major in ("Euro", "Dollar", "Pfund", "Franken"):
            branches.append(whole + pynutil.delete(",00") + pynini.accep(f" {major}"))
            branches.append(whole + pynutil.delete(",") + pynutil.insert(f" {major} ") + cents + pynutil.delete(f" {major}"))
        return self.wrap(text(pynini.union(*branches))).optimize()
