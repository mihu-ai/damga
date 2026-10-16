from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.data import load_tsv
from ....core.rules import Rule

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "lexicon_entries.tsv"

class LexiconEntryReader(Rule):
    name = "lexicon_entry"
    kind = "read"

    def build(self, variants: bool = False, custom: dict[str, str] | None = None, builtin: bool = True):
        pairs = load_tsv(DATA, lower_first=False) if builtin else []
        branches = []
        if pairs:
            branches.append(pynini.union(*[pynini.cross(pynini.escape(a), pynini.escape(b)) for a, b in pairs]))
        if custom:
            branches.append(pynutil.add_weight(pynini.union(*[pynini.cross(pynini.escape(a), pynini.escape(b)) for a, b in custom.items()]), -0.1))
        if not branches:
            self._fst = None
            return
        return self.wrap(pynutil.insert('word="') + pynini.union(*branches) + pynutil.insert('"'))
