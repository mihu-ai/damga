from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import text

# currency names (singular, plural, the adjectives that may follow the plural: "pesos mexicanos")
CURRENCY_NAMES = [
    ("euro", "euros", ()), ("dólar", "dólares", ("estadounidenses", "americanos", "canadienses", "australianos")),
    ("libra", "libras", ("esterlinas",)), ("peso", "pesos", ("mexicanos", "argentinos", "colombianos", "chilenos",
                                                             "uruguayos", "dominicanos", "cubanos")),
    ("yen", "yenes", ()), ("franco", "francos", ("suizos",)), ("sol", "soles", ()), ("real", "reales", ()),
    ("colón", "colones", ()), ("quetzal", "quetzales", ()), ("lempira", "lempiras", ()), ("córdoba", "córdobas", ()),
    ("balboa", "balboas", ()), ("guaraní", "guaraníes", ()), ("bolívar", "bolívares", ()),
    ("boliviano", "bolivianos", ()), ("rupia", "rupias", ()), ("rublo", "rublos", ()), ("yuan", "yuanes", ()),
    ("peseta", "pesetas", ()), ("won", "wones", ()), ("corona", "coronas", ("suecas", "noruegas", "danesas")),
]
MINOR = ["céntimos", "centavos", "peniques", "centésimos"]


class MoneyReader(Rule):
    """An amount of money is written in digits, its currency stays a word: ``doce dólares y cinco centavos`` →
    ``12,05 dólares``.  ``un euro`` alone stays as it is (``ni un euro``)."""

    name = "money"
    kind = "read"

    def build(self, number: pynini.Fst, written: pynini.Fst, variants: bool = False):
        one = pynini.cross(pynini.union("un", "una"), "1")
        two_up = written @ pynini.difference(pynini.closure(pynini.union(DIGIT, ".")), pynini.union("0", "1"))
        cents = (number @ pynini.union(*[str(n) for n in range(1, 100)])) @ pynini.union(
            pynutil.insert("0") + DIGIT, DIGIT + DIGIT)
        minor = pynini.union(*MINOR)
        # "y cinco centavos", "con sesenta y tres", "cincuenta centavos"; a bare number only from ten up
        tail = pynini.union(
            pynini.cross(pynini.union(" y ", " con "), ",") + cents + pynutil.delete(pynini.closure(" " + minor, 0, 1)),
            pynini.cross(" ", ",") + cents + pynutil.delete(" " + minor),
            pynini.cross(" ", ",") + (number @ pynini.union(*[str(n) for n in range(10, 100)])))
        plain, moved = [], []
        for sg, pl, adjectives in CURRENCY_NAMES:
            names = [pl] + [f"{pl} {a}" for a in adjectives]
            plain += names
            # the cents go to the amount, the currency follows it: "doce dólares y cinco centavos" → "12,05 dólares"
            moved += [pynutil.delete(" " + said) + tail + pynutil.insert(" " + name)
                      for name in names for said in ([name, sg] if name == pl else [name])]
        major = pynini.union(two_up + " " + pynini.union(*plain), pynini.union(one, two_up) + pynini.union(*moved))
        # "dos dólares y sesenta y tres dólares" is two amounts, not 2,63 (but "y cinco centavos" are cents)
        graph = pynini.union(major, two_up + " " + pynini.union(*MINOR),
                             pynutil.add_weight(major + " y " + major, 0.5))
        return self.wrap(text(graph)).optimize()
