from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import text

UNITS = ("kilomètre", "kilomètres", "mètre", "mètres", "centimètres", "millimètres", "hectare", "hectares", "tonne",
         "tonnes", "kilo", "kilos", "kilogramme", "kilogrammes", "gramme", "grammes", "litre", "litres", "degré",
         "degrés", "mégawatts", "gigawatts", "kilowattheures", "euro", "euros", "centime", "centimes", "dollar",
         "dollars", "livre", "livres", "francs", "kilomètres carrés", "mètres carrés")
# Not durations: "sept ans", "trois mois" stay words.


class PercentReader(Rule):
    """``cinq pour cent`` → ``5 %``, ``cinq à dix pour cent`` → ``5 à 10 %``."""

    name = "percent"
    kind = "read"

    def build(self, number: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        sign = pynini.closure(pynini.cross("moins ", "-"), 0, 1)
        amount = pynini.union(number, decimal)
        percent = sign + amount + pynini.cross(pynini.union(" pour cent", " pourcent", " pour cents"), " %")
        span = amount + pynini.accep(" à ") + percent
        return self.wrap(text(pynini.union(percent, span))).optimize()


class MeasureReader(Rule):
    """A small number before a unit or a currency is written in digits too (``cinq kilomètres`` → ``5
    kilomètres``); an amount and its cents are one number (``deux euros et vingt centimes`` → ``2,20 euros``)."""

    name = "measure"
    kind = "read"

    def build(self, number: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        # "une tonne", "un an": one of a unit stays a word
        amount = pynini.union(pynini.difference(pynini.project(number, "input"), pynini.union("un", "une")) @ number, decimal)
        unit = pynini.union(*[pynini.accep(" " + u) for u in UNITS])
        sign = pynini.closure(pynini.cross("moins ", "-"), 0, 1)
        cents = number @ pynini.union(*[str(n) for n in range(1, 100)]) @ pynini.union(pynutil.insert("0") + DIGIT, DIGIT + DIGIT)
        one = number @ pynini.union("0", "1")
        many = number @ pynini.difference(pynini.closure(pynini.union(DIGIT, " "), 1), pynini.union("0", "1"))
        priced = []
        for sg, pl, minor in (("euro", "euros", "centime"), ("dollar", "dollars", "cent"), ("franc", "francs", "centime")):
            said = pynutil.delete(pynini.union(" " + sg, " " + pl))
            minor_said = pynutil.delete(pynini.union(" " + minor, " " + minor + "s"))
            # "et" only with the cents named: "cinq euros et vingt centimes", not "cinq euros et vingt pays"
            tail = pynini.union(pynini.cross(" ", ",") + cents + minor_said.ques, pynini.cross(" et ", ",") + cents + minor_said)
            priced += [one + said + tail + pynutil.insert(" " + sg), many + said + tail + pynutil.insert(" " + pl)]
        return self.wrap(text(pynini.union(sign + amount + unit, *priced))).optimize()
