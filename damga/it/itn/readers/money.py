from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import text

CURRENCY_WORDS = ("euro", "dollari", "dollaro", "sterline", "sterlina", "franchi", "centesimi", "centesimo")
UNIT_WORDS = ("chilometri", "chilometro", "metri", "metro", "centimetri", "chili", "chilo", "chilogrammi",
              "grammi", "tonnellate", "tonnellata", "ettari", "ettaro", "litri", "litro", "gradi", "grado", "megawatt",
              "gigawatt", "chilowattora")


class MoneyReader(Rule):
    """A number before a currency or a unit word is written in digits even below ten: ``cinque euro`` → ``5 euro``,
    ``un euro e cinquanta`` → ``1,50 euro``, ``tre chilometri`` → ``3 chilometri``."""

    name = "money"
    kind = "read"

    def build(self, number: pynini.Fst, written: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        amount = pynini.union(written, decimal, pynini.cross(pynini.union("un", "una"), "1"))
        cents = (number @ pynini.union(*[str(n) for n in range(1, 100)])) @ pynini.union(
            pynutil.insert("0") + DIGIT, DIGIT + DIGIT)
        word = pynini.union(*[pynini.accep(" " + w) for w in CURRENCY_WORDS + UNIT_WORDS])
        euro_cents = (pynini.union(written, pynini.cross("un", "1")) + pynini.cross(" euro e ", ",") + cents
                      + pynutil.insert(" euro") + pynutil.delete(pynini.closure(" centesimi", 0, 1)))
        sign = pynini.closure(pynini.cross("meno ", "-"), 0, 1)
        return self.wrap(text(pynini.union(sign + amount + word, euro_cents))).optimize()


class PercentReader(Rule):
    """``dieci percento`` / ``dieci per cento`` → ``10%``, ``zero virgola sette percento`` → ``0,7%``."""

    name = "percent"
    kind = "read"

    def build(self, written: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        sign = pynini.closure(pynini.cross("meno ", "-"), 0, 1)
        # "lo zero cinquanta per cento": a rate said without "virgola"
        zero_point = pynini.cross("zero ", "0,") + (written @ (pynini.union(*"123456789") + DIGIT))
        amount = pynini.union(written, decimal, pynini.cross(pynini.union("un", "uno"), "1"), zero_point)
        percent = sign + amount + pynini.cross(pynini.union(" percento", " per cento"), "%")
        # "per cento" without a number before it stays words, never "per 100"
        keep = pynutil.add_weight(pynini.accep("per cento"), 0.5)
        return self.wrap(text(pynini.union(percent, keep))).optimize()
