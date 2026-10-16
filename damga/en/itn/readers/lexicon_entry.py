from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import text

BUILTIN = {"mister": "Mr", "missus": "Mrs", "et cetera": "etc.",
           # names written with a number
           "co two": "CO2", "c o two": "CO2", "g seven": "G7", "g eight": "G8", "g twenty": "G20",
           "fp six": "FP6", "fp seven": "FP7", "fp eight": "FP8", "fp nine": "FP9", "covid nineteen": "COVID-19",
           "world war one": "World War I", "world war two": "World War II"}


class LexiconEntryReader(Rule):
    name = "lexicon_entry"
    kind = "read"

    def build(self, variants: bool = False, custom: dict[str, str] | None = None, builtin: bool = True):
        fst = None
        rows = {**(BUILTIN if builtin else {}), **(custom or {})}
        if rows:
            fst = self.wrap(text(pynini.union(*[pynini.cross(a.lower(), b) for a, b in rows.items()]))).optimize()
        return fst
