from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL_APOC, CARDINAL_FEM, strip_thousands
from ..units import CURRENCIES
from .cardinal import BEFORE_NOUN, FEMININE, text
from .decimal import decimal_words

QUANTITY = ["millones", "millón", "mil millones", "billones"]


def _symbols(rows, plural: bool, prefix: str = " ") -> pynini.Fst:
    """The written symbols of ``rows`` → their currency name (``€`` → `` euros``)."""
    return pynini.union(*[pynini.cross(pynini.escape(s), prefix + (pl if plural else sg))
                          for symbols, sg, pl, *_ in rows for s in symbols]).optimize()


class MoneyReader(Rule):
    """``5 €`` → ``cinco euros``, ``1,50 €`` → ``un euro con cincuenta céntimos``, ``10 millones €`` → ``diez
    millones de euros``.  The pre-hook moves a symbol written before the amount after it."""

    name = "money"
    kind = "read"

    def build(self, variants: bool = False):
        strip = strip_thousands()
        space = pynutil.delete(pynini.closure(pynini.union(" ", " ", " "), 0, 1))
        unmark = pynini.closure(pynutil.delete(pynini.union(BEFORE_NOUN, FEMININE)), 0, 1)
        # 01 → un céntimo, 50 → cincuenta céntimos, a single digit counts tens: 1,5 € → un euro con cincuenta céntimos
        two = pynini.difference(DIGIT + DIGIT, pynini.union("00", "01"))
        cents_many = pynini.union(pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL_APOC),
                                  (NONZERO_DIGIT + DIGIT) @ CARDINAL_APOC)
        cents_many = pynini.union(two @ cents_many, (NONZERO_DIGIT + pynutil.insert("0")) @ cents_many)
        quantity = pynini.union(*[pynini.accep(" " + q) for q in QUANTITY])
        branches = []
        # the amount alone, its currency by gender: 1 € → un euro, 21 £ → veintiuna libras, 5,00 € → cinco euros
        for fem in (False, True):
            rows = [r for r in CURRENCIES if r[3] == fem]
            card = strip @ (CARDINAL_FEM if fem else CARDINAL_APOC)
            one = pynini.cross("1", "una" if fem else "un")
            many = pynini.difference(pynini.project(card, "input"), "1") @ card
            branches += [one + space + _symbols(rows, False),
                         many + pynutil.delete(pynini.closure(pynini.union(",00", ",0"), 0, 1)) + space + _symbols(rows, True)]
            # no minor unit: the decimal, 12,05 ¥ → doce coma cero cinco yenes
            rows = [r for r in rows if r[4] is None]
            branches.append(decimal_words(fem) + space + _symbols(rows, True))
        # the pre-hook marks a number before "millones" as before a noun: un millón, veintiún millones
        scaled = pynini.union(pynutil.delete(BEFORE_NOUN) + (strip @ CARDINAL_APOC), strip @ CARDINAL_APOC,
                              pynini.closure(pynutil.delete(BEFORE_NOUN), 0, 1) + decimal_words())
        branches.append(scaled + quantity + space + _symbols(CURRENCIES, True, " de "))
        # with cents (below a million), the currency named before them: 1,50 € → un euro con cincuenta céntimos
        below_million = strip @ pynini.closure(DIGIT, 1, 6)
        for row in CURRENCIES:
            symbols, sg, pl, fem, minor = row
            if minor is None:
                continue
            card = below_million @ (CARDINAL_FEM if fem else CARDINAL_APOC)
            nonzero = pynini.difference(pynini.project(card, "input"), pynini.union("1", "0")) @ card
            amount = pynini.union(pynini.cross("1", ("una " if fem else "un ") + sg), nonzero + pynutil.insert(" " + pl))
            cents = pynini.union(pynini.cross("01", "un " + minor[:-1]), cents_many + pynutil.insert(" " + minor))
            sym = space + pynutil.delete(pynini.union(*[pynini.escape(s) for s in symbols]))
            branches.append(amount + pynini.cross(",", " con ") + cents + sym)
            branches.append(pynutil.delete("0,") + cents + sym)          # 0,55 $ → cincuenta y cinco centavos
            if variants:
                # 1,50 € → un euro cincuenta
                branches.append(pynutil.add_weight(
                    amount + pynini.cross(",", " ") + (pynini.difference(DIGIT + DIGIT, "00") @ cents_many) + sym, 0.5))
        return self.wrap(text(unmark + pynini.union(*branches))).optimize()
