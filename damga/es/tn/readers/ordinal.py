from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...numbers import CARDINAL, CARDINAL_APOC, CARDINAL_FEM, ORDINAL, ORDINAL_APOC, ORDINAL_FEM, strip_thousands
from .cardinal import text

# The letters Latin American writing puts after the digit instead of º/ª (1ro, 2do, 3ro, 4to, 7mo, 8vo, 9no, 10mo):
# the end of the ordinal word, masculine; the feminine swaps the last letter for "a".
_ENDINGS = {1: ("ro", "ero"), 2: ("do",), 3: ("ro", "ero"), 4: ("to",), 5: ("to",), 6: ("to",), 7: ("mo",), 8: ("vo",),
            9: ("no",), 10: ("mo",)}


class OrdinalReader(Rule):
    """``1.º`` / ``1º`` / ``1ro`` → ``primero``, ``1.ª`` / ``1ra`` → ``primera``, ``1.er`` / ``1.ᵉʳ`` → ``primer``;
    above ten the cardinal: ``13.ª`` → ``trece``, ``21.ª`` → ``veintiuna``, ``1.000.º`` → ``mil``."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        # Above ten the cardinal: "el 80.º aniversario" → "ochenta aniversario".
        small = pynini.union(*[str(n) for n in range(1, 11)])
        strip = strip_thousands()
        big = pynini.difference(pynini.project(strip, "input"), small)
        dot = pynutil.delete(pynini.closure(".", 0, 1))
        masc_mark = pynutil.delete(pynini.union("º", "°", "ᵒ"))
        fem_mark = pynutil.delete(pynini.union("ª", "ᵃ"))
        masc = pynini.union(small @ ORDINAL, big @ strip @ CARDINAL) + pynini.union(
            dot + masc_mark, pynutil.delete(".o"))
        fem = pynini.union(small @ ORDINAL_FEM, big @ strip @ CARDINAL_FEM) + pynini.union(
            dot + fem_mark, pynutil.delete(".a"))
        apoc_mark = pynutil.delete(pynini.union(".er", "er", ".ᵉʳ", "ᵉʳ"))
        apoc = pynini.union(pynini.union("1", "3") @ ORDINAL_APOC, big @ strip @ CARDINAL_APOC) + apoc_mark
        # 1ro, 2do, 1ra, 2da: the endings are only read after their own digit (never "2ro"), big numbers take any
        latin = []
        for n, endings in _ENDINGS.items():
            for e in endings:
                latin.append(pynini.accep(str(n)) @ ORDINAL + pynutil.delete(e))
                latin.append(pynini.accep(str(n)) @ ORDINAL_FEM + pynutil.delete(e[:-1] + "a"))
        latin.append((big @ strip @ CARDINAL) + pynutil.delete(pynini.union("vo", "mo", "no", "to", "ro", "do")))
        latin.append((big @ strip @ CARDINAL_FEM) + pynutil.delete(pynini.union("va", "ma", "na", "ta", "ra", "da")))
        graph = pynini.union(masc, fem, apoc, *latin)
        if variants:
            # 80.º → octogésimo, 13.ª → decimotercera
            upto100 = big @ pynini.union(NONZERO_DIGIT + DIGIT, "100")
            graph = pynini.union(graph, pynutil.add_weight(pynini.union(
                (upto100 @ ORDINAL) + dot + masc_mark,
                (upto100 @ ORDINAL_FEM) + dot + fem_mark), 0.6))
        return self.wrap(text(graph)).optimize()
