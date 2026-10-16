from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from .cardinal import CardinalReader


class AddressReader(Rule):
    name = "address"
    kind = "read"

    def build(self, cardinal: CardinalReader, variants: bool = False):
        number = cardinal.graph_mixed @ (pynini.difference(DIGIT, "0") + pynini.closure(DIGIT, 0, 4))
        osp = pynutil.delete(pynini.closure(" ", 0, 1))
        colon = pynutil.delete(pynini.closure(pynini.union(":", ".", ","), 0, 1))

        def part(keywords, field):
            kw = pynutil.delete(pynini.union(*keywords)) + colon + osp
            return kw + pynutil.insert(f'{field}="') + number + pynutil.insert('"')

        no = part(["no", "numara", "numarası", "nu"], "no")

        street = pynini.union("caddesi", "cadde", "sokak", "sokağı", "sokağında", "mahallesi", "mahalle", "bulvarı", "bulvar",
                              "yolu", "apartmanı", "sitesi", "sokaktan", "caddesinde")
        street_no = (pynutil.insert('street="') + street + pynutil.insert('" ') + pynutil.delete(" ")
                     + pynutil.add_weight(part(["nokta", "na", "no", "nu", "numara", "nokta,"], "no"), 0.2))
        daire = pynini.union(part(["daire", "dairesi"], "daire"), pynutil.add_weight(pynini.cross("daireydi", 'daire="7"'), 0.5))
        kat = part(["kat", "katı"], "kat")
        sep = pynutil.delete(pynini.closure(pynini.union(" ", ","), 1, 3)) + pynutil.insert(" ")
        tail = pynini.closure(sep + pynini.union(daire, kat), 0, 2)
        graph = pynini.union(no + tail, street_no + tail, daire + pynini.closure(sep + kat, 0, 1), kat + pynini.closure(sep + daire, 0, 1))
        return self.wrap(graph.optimize())
