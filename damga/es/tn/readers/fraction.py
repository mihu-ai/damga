from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import BEFORE_NOUN, FEMININE
from ...numbers import CARDINAL, CARDINAL_APOC, strip_thousands
from .cardinal import text

# Denominator → singular (the plural adds -s): the partitive forms to ten, -avo from eleven (onceavo, treintavo).
DENOMINATORS = {
    2: "medio", 3: "tercio", 4: "cuarto", 5: "quinto", 6: "sexto", 7: "séptimo", 8: "octavo", 9: "noveno",
    10: "décimo", 11: "onceavo", 12: "doceavo", 13: "treceavo", 14: "catorceavo", 15: "quinceavo",
    16: "dieciseisavo", 17: "diecisieteavo", 18: "dieciochoavo", 19: "diecinueveavo", 20: "veinteavo",
    30: "treintavo", 40: "cuarentavo", 50: "cincuentavo", 60: "sesentavo", 70: "setentavo", 80: "ochentavo",
    90: "noventavo", 100: "centésimo", 200: "ducentésimo", 300: "tricentésimo", 400: "cuadringentésimo",
    500: "quingentésimo", 600: "sexcentésimo", 700: "septingentésimo", 800: "octingentésimo", 900: "noningentésimo",
    1000: "milésimo", 10000: "diezmilésimo", 100000: "cienmilésimo", 1000000: "millonésimo",
}
# 21 to 99: the -avo of the units glued to the tens (veintiunavo, veintidosavo, treintaiunavo, cuarentaidosavo)
_UNIT_AVO = ["unavo", "dosavo", "tresavo", "cuatroavo", "cincoavo", "seisavo", "sieteavo", "ochoavo", "nueveavo"]
_TENS = {2: "veinti", 3: "treintai", 4: "cuarentai", 5: "cincuentai", 6: "sesentai", 7: "setentai", 8: "ochentai",
         9: "noventai"}
for _t, _head in _TENS.items():
    for _u, _avo in enumerate(_UNIT_AVO, 1):
        DENOMINATORS[10 * _t + _u] = _head + _avo
VULGAR = {"½": "un medio", "⅓": "un tercio", "⅔": "dos tercios", "¼": "un cuarto", "¾": "tres cuartos",
          "⅕": "un quinto", "⅖": "dos quintos", "⅗": "tres quintos", "⅘": "cuatro quintos", "⅙": "un sexto",
          "⅚": "cinco sextos", "⅐": "un séptimo", "⅛": "un octavo", "⅜": "tres octavos", "⅝": "cinco octavos",
          "⅞": "siete octavos", "⅑": "un noveno", "⅒": "un décimo"}


def _written(d: int) -> pynini.Fst:
    """``100000`` and its grouped spelling ``100.000``."""
    plain = str(d)
    grouped = f"{d:,}".replace(",", ".")
    return pynini.union(plain, grouped) if grouped != plain else pynini.accep(plain)


def proper_fractions() -> pynini.Fst:
    """``3/4`` → ``tres cuartos``, ``1/123`` → ``uno sobre ciento veintitrés``: a numerator below the denominator
    (the pre-hook may mark the denominator for the noun after it)."""
    slash = pynini.cross("/", " ") + pynutil.delete(pynini.union(FEMININE, BEFORE_NOUN)).ques
    unmark = pynutil.delete(pynini.union(FEMININE, BEFORE_NOUN)).ques
    branches = []
    for d, sg in DENOMINATORS.items():
        # a marked half before a noun is read by the fraction reader ("medio kilo")
        one = pynini.cross("1/", "un ") if d == 2 else pynini.cross("1", "un") + slash
        branches.append(one + pynini.cross(_written(d), sg))
        if d > 2:
            if d < 100:
                many = pynini.union(*[str(n) for n in range(2, d)]) @ CARDINAL_APOC
            else:                               # fewer digits than the denominator: always below it
                many = pynini.difference(NONZERO_DIGIT + pynini.closure(DIGIT, 0, len(str(d)) - 2), "1") @ CARDINAL_APOC
            branches.append(many + slash + pynini.cross(_written(d), sg + "s"))
    # any other denominator from 101 up: "1/123" → "uno sobre ciento veintitrés", "1/1.200.000" too; never a year,
    # "Ley 39/2015" is a law number
    named = pynini.union(*[str(d) for d in DENOMINATORS], *[str(y) for y in range(1800, 2100)])
    strip = strip_thousands()
    for length in range(3, 13):
        den = strip @ pynini.difference(NONZERO_DIGIT + DIGIT ** (length - 1), named) @ CARDINAL
        num = (NONZERO_DIGIT + pynini.closure(DIGIT, 0, length - 2)) @ CARDINAL
        branches.append(num + pynini.cross("/", " sobre ") + unmark + den)
    return pynini.union(*branches).optimize()


class FractionReader(Rule):
    """Proper fractions: ``3/4`` → ``tres cuartos``, ``1/123`` → ``uno sobre ciento veintitrés``, ``3 2/5`` →
    ``tres y dos quintos``.  Dates take three parts, so a two-part ``3/4`` is never a date here."""

    name = "fraction"
    kind = "read"

    def build(self, variants: bool = False):
        vulgar = pynini.union(*[pynini.cross(k, v) for k, v in VULGAR.items()])
        slash = pynini.cross("/", " ") + pynutil.delete(pynini.union(FEMININE, BEFORE_NOUN)).ques
        slashed = proper_fractions()
        # before a noun a half is an adjective: "1/2 kilo" → "medio kilo", "1/2 taza" → "media taza"
        half = [pynini.cross("1/" + BEFORE_NOUN + "2", "medio"), pynini.cross("1/" + FEMININE + "2", "media")]
        # mixed numbers: "3 2/5" → "tres y dos quintos", "2 1/2" → "dos y medio", "2 1/2 tazas" → "dos y media tazas"
        whole = (NONZERO_DIGIT + pynini.closure(DIGIT, 0, 2)) @ CARDINAL
        mixed = whole + pynini.union(
            pynini.cross(" ", " y ") + slashed,
            pynini.cross(pynini.union(" 1/2", " 1/" + BEFORE_NOUN + "2", "½"), " y medio"),
            pynini.cross(" 1/" + FEMININE + "2", " y media"),
            pynutil.insert(" y ") + pynini.union(*[pynini.cross(k, v) for k, v in VULGAR.items() if k != "½"]))
        sign = pynini.closure(pynini.union(pynini.cross("-", "menos "), pynini.cross("−", "menos ")), 0, 1)
        graph = pynini.union(sign + pynini.union(slashed, vulgar, mixed), *half,
                             pynini.cross("24", "veinticuatro") + slash + pynini.cross("7", "siete"))
        return self.wrap(text(graph)).optimize()
