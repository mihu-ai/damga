from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, SCALE_OF, strip_thousands
from .cardinal import text
from .decimal import decimal_words, quantity

# written → (singular, plural, minor singular, minor plural)
CURRENCIES = {
    "€": ("euro", "euro", "centesimo", "centesimi"), "EUR": ("euro", "euro", "centesimo", "centesimi"),
    "$": ("dollaro", "dollari", "centesimo", "centesimi"), "USD": ("dollaro", "dollari", "centesimo", "centesimi"),
    "£": ("sterlina", "sterline", "penny", "pence"), "GBP": ("sterlina", "sterline", "penny", "pence"),
    "CHF": ("franco", "franchi", "centesimo", "centesimi"),
}
# The currency written out after the amount: 12,50 euro is said as 12,50 € (dodici euro e cinquanta), 1 eur as un euro.
CURRENCY_WORDS = {"euro": "€", "Euro": "€", "eur": "€", "Eur": "€", "dollari": "$", "dollaro": "$",
                  "sterline": "£", "sterlina": "£", "franchi": "CHF"}


class MoneyReader(Rule):
    """``5 €`` / ``€ 5`` → ``cinque euro``, ``1,50 €`` → ``un euro e cinquanta``, ``2,05 €`` → ``due euro e cinque
    centesimi`` (a lone cent digit says its unit: "e cinque" alone sounds like 2,50)."""

    name = "money"
    kind = "read"

    def build(self, variants: bool = False):
        integer = (strip_thousands() @ CARDINAL).optimize()
        other = pynini.difference(pynini.project(integer, "input"), "1") @ integer @ SCALE_OF   # 0, 2, 3, …
        nonzero_other = pynini.difference(pynini.project(other, "input"), "0") @ other  # 2, 3, …
        cents = (NONZERO_DIGIT + DIGIT) @ CARDINAL
        decimals = decimal_words()
        # one fractional digit or three and more: a decimal amount (2,5 € → due virgola cinque euro)
        decimal_amount = (pynini.difference(pynini.project(decimals, "input"),
                                            pynini.closure(pynini.union(DIGIT, ".", " "), 1) + "," + DIGIT + DIGIT)
                          @ decimals).optimize()
        scaled = (pynini.union(integer, decimals, pynini.cross("1", "un")) + quantity()).optimize()
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        # Symbols that are said the same way share one graph (€ and EUR, $ and USD, £ and GBP).
        by_words: dict[tuple[str, str, str, str], list[str]] = {}
        for written, words in CURRENCIES.items():
            by_words.setdefault(words, []).append(written)
        branches = []
        for (sg, pl, minor_sg, minor_pl), symbols in by_words.items():
            sym = pynutil.delete(pynini.union(*[pynini.escape(w) for w in symbols]))
            word = [w for w, s in CURRENCY_WORDS.items() if s in symbols]
            after = pynini.union(sym, pynutil.delete(pynini.union(*word))) if word else sym
            one_cent = pynini.union(pynini.cross("01", "un " + minor_sg),
                                    pynutil.delete("0") + (pynini.difference(DIGIT, pynini.union("0", "1")) @ CARDINAL)
                                    + pynutil.insert(" " + minor_pl))
            one = pynini.cross("1", ("una " if sg.endswith("a") else "un ") + sg)    # una sterlina
            one_or_many = pynini.union(one, other + pynutil.insert(" " + pl))
            whole = pynini.union(one, nonzero_other + pynutil.insert(" " + pl))
            amount = pynini.union(
                one_or_many,
                whole + pynutil.delete(",") + pynini.union(pynutil.delete("00"),
                                                           pynutil.insert(" e ") + pynini.union(cents, one_cent)),
                pynutil.delete("0,") + pynini.union(pynini.cross("01", "un " + minor_sg),
                                                    (pynini.difference(DIGIT + DIGIT, pynini.union("00", "01"))
                                                     @ pynini.union(pynutil.delete("0") + (NONZERO_DIGIT @ CARDINAL), cents))
                                                    + pynutil.insert(" " + minor_pl)),
                decimal_amount + pynutil.insert(" " + pl),
            ).optimize()
            said = scaled + pynutil.insert(" di " + pl)
            branches += [sym + space + amount, amount + space + after, sym + space + said, said + space + sym]
        return self.wrap(text(pynini.union(*branches))).optimize()
