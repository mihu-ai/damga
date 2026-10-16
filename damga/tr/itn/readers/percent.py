from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import TR_LOWER, Rule, drop_space
from ...lexicon import DIGITS
from .cardinal import CardinalReader
from .decimal import DecimalReader


class PercentReader(Rule):
    name = "percent"
    kind = "read"

    def build(self, cardinal: CardinalReader, decimal: DecimalReader, variants: bool = False):
        # Every inflection after ``yüzde`` (``yüzde on altısı`` → %16'sı, ``yüzde birini`` → %1'ini); ``iki yüzde
        # birini`` (200'de birini) is the ``hundredth`` branch below.
        suffixed = cardinal.with_suffix(cardinal.graph, anywhere=True)
        integer = pynutil.insert('integer="') + pynini.union(cardinal.graph_mixed, suffixed) + pynutil.insert('"')
        value = pynini.union(decimal.graph, integer)
        graph = pynini.union(
            pynini.cross("yüzde", 'symbol="%"') + drop_space + pynutil.insert(" ") + decimal.optional_minus + value,
            pynini.cross("binde", 'symbol="‰"') + drop_space + pynutil.insert(" ") + value,
        )
        fst = self.wrap(graph.optimize())
        # ``iki yüzde birini`` → 200'de birini: after a single digit word, ``yüzde`` is ``yüz`` + locative and the
        # ``bir…`` that follows is "one of them", not a percentage.  Two tokens in one branch, so it outweighs the
        # cardinal ``iki`` + percent ``yüzde birini`` reading.
        hundreds = pynini.union(*[pynini.cross(w, d + "00") for w, d in DIGITS if w != "bir"])
        bir_case = pynini.accep("bir") + pynini.union("i", "ı", "e", "d") + pynini.closure(TR_LOWER)
        self.hundredth = (pynutil.insert('cardinal(integer="') + hundreds + pynini.cross(" yüzde", '" suffix="de")')
                          + pynini.cross(" ", ' word="') + bir_case + pynutil.insert('"')).optimize()
        return fst
