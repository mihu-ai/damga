from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, TR_LOWER, Rule
from ...itn.readers.email import TLDS


class EmailReader(Rule):
    name = "email"
    kind = "read"

    def build(self, variants: bool = False):
        word = pynini.closure(pynini.union(TR_LOWER, DIGIT), 1)
        sep = pynini.union(pynini.cross(".", " nokta "), pynini.cross("_", " alt çizgi "), pynini.cross("-", " tire "), pynini.cross("+", " artı "))
        local = word + pynini.closure(sep + word)
        tld = pynini.union(*TLDS)
        domain = word + pynini.closure(pynini.cross(".", " nokta ") + word) + pynini.cross(".", " nokta ") + tld + pynini.closure(pynini.cross(".", " nokta ") + tld, 0, 1)
        email = local + pynini.cross("@", " et ") + domain
        web = pynini.union(pynini.cross("www.", "www nokta ") + domain, pynutil.add_weight(domain, 0.2))
        return self.wrap(pynutil.insert('address="') + pynini.union(email, web) + pynutil.insert('"')).optimize()
