from __future__ import annotations

from pynini.lib import pynutil

from ....core.rules import SIGMA, Rule, string_map
from .cardinal import CardinalReader

ORDINAL_SUFFIX = [
    ("birinci", "bir"), ("ikinci", "iki"), ("üçüncü", "üç"), ("dördüncü", "dört"), ("beşinci", "beş"),
    ("altıncı", "altı"), ("yedinci", "yedi"), ("sekizinci", "sekiz"), ("dokuzuncu", "dokuz"),
    ("onuncu", "on"), ("yirminci", "yirmi"), ("otuzuncu", "otuz"), ("kırkıncı", "kırk"), ("ellinci", "elli"),
    ("altmışıncı", "altmış"), ("yetmişinci", "yetmiş"), ("sekseninci", "seksen"), ("doksanıncı", "doksan"),
    ("yüzüncü", "yüz"), ("bininci", "bin"), ("milyonuncu", "milyon"), ("milyarıncı", "milyar"),
]

class OrdinalReader(Rule):
    name = "ordinal"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        last_word = string_map(ORDINAL_SUFFIX)

        spoken = SIGMA + last_word
        graph = (spoken @ cardinal.graph_no_zero).optimize()
        self.graph = graph
        return self.wrap(pynutil.insert('integer="') + graph + pynutil.insert('"'))
