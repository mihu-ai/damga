from __future__ import annotations

import pathlib

import pynini

from ....core.rules import Rule
from .cardinal import text

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "lexicon_entries.tsv"


def load() -> list[tuple[str, str]]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            a, b = line.split("\t")
            rows.append((a, b))
    return rows


class LexiconEntryReader(Rule):
    name = "lexicon_entry"
    kind = "read"

    def build(self, variants: bool = False, custom: dict[str, str] | None = None):
        rows = load() + list((custom or {}).items())
        return self.wrap(text(pynini.union(*[pynini.cross(pynini.escape(a), b) for a, b in rows]))).optimize()
