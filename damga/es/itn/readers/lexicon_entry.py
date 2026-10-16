from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import text

BUILTIN = {"etcétera": "etc."}


class LexiconEntryReader(Rule):
    name = "lexicon_entry"
    kind = "read"

    def build(self, variants: bool = False, custom: dict[str, str] | None = None, builtin: bool = True):
        fst = None
        rows = {**(BUILTIN if builtin else {}), **(custom or {})}
        if rows:
            fst = self.wrap(text(pynini.union(*[pynini.cross(a.lower(), b) for a, b in rows.items()]))).optimize()
        return fst
