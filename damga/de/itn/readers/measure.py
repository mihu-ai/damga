from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import BIG_SCALES
from ...tn.readers.measure import load_units
from .cardinal import text

CURRENCY = ("Euro", "Cent", "Dollar", "Pfund", "Franken", "Rappen", "Yen", "Pence", "Penny")
# the word for the hundredth of each currency, as said
MINOR = {"Euro": ("cent",), "Dollar": ("cent",), "Pfund": ("pence", "penny"), "Franken": ("rappen",)}
OTHER = ("Prozent", "Prozentpunkte", "Prozentpunkten", "Mal", "Jahre", "Jahren", "Tage", "Tagen", "Monate", "Monaten",
         "Wochen", "Stunden", "Minuten", "Sekunden", "Menschen", "Personen", "Mitgliedstaaten", "Länder", "Ländern")


class MeasureReader(Rule):
    """A number before a unit, a currency or "Prozent" is written in digits even below thirteen: ``fünf prozent`` →
    ``5 Prozent``, ``fünf euro fünfzig`` → ``5,50 Euro``."""

    name = "measure"
    kind = "read"

    def build(self, number: pynini.Fst, written: pynini.Fst, decimal: pynini.Fst, variants: bool = False):
        nouns = set(CURRENCY) | set(OTHER)
        for _, sg, pl, _ in load_units():
            nouns |= {sg, pl}
        word = pynini.union(*[pynini.cross(" " + n.lower(), " " + n) for n in sorted(nouns)])
        scale = pynini.closure(pynini.union(*[pynini.cross(" " + w.lower(), " " + w) for s in BIG_SCALES for w in s]), 0, 1)
        sign = pynini.closure(pynini.cross("minus ", "-"), 0, 1)
        amount = sign + pynini.union(written, decimal + scale)
        cents = (number @ pynini.union(*[str(n) for n in range(1, 100)])) @ pynini.union(
            pynini.cross("", "0") + DIGIT, DIGIT + DIGIT)
        # after "und" the cents word must follow: "zwei euro und zwanzig" is two things
        with_cents = []
        for major, minors in MINOR.items():
            minor = pynutil.delete(pynini.union(*[" " + m for m in minors]))
            with_cents.append(written + pynini.cross(f" {major.lower()} ", ",")
                              + pynini.union(cents + minor.ques, pynutil.delete("und ") + cents + minor)
                              + pynutil.insert(f" {major}"))
        return self.wrap(text(pynini.union(amount + word, *with_cents))).optimize()
