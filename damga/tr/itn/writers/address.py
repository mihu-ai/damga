from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import NON_QUOTE, Rule

LABELS = {"no": "No", "daire": "Daire", "kat": "Kat", "blok": "Blok"}

class AddressWriter(Rule):
    name = "address"
    kind = "write"

    def build(self, variants: bool = False):
        value = pynini.closure(NON_QUOTE, 1)
        fields = [pynutil.delete(f'{k}="') + pynutil.insert(f"{v}: ") + value + pynutil.delete('"') for k, v in LABELS.items()]
        fields.append(pynutil.delete('street="') + value + pynutil.delete('"'))
        field = pynini.union(*fields)
        return self.unwrap(field + pynini.closure(pynini.accep(" ") + field, 0, 4))
