from __future__ import annotations

import pathlib

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from .cardinal import text

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "lexicon_entries.tsv"
ACRONYMS = DATA.with_name("acronym_words.tsv")
LETTER = pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüßABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ0123456789").optimize()


def load(path: pathlib.Path = DATA) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            a, b = line.split("\t")
            rows.append((a, b))
    return rows


class LexiconEntryReader(Rule):
    name = "lexicon_entry"
    kind = "read"

    def build(self, variants: bool = False, custom: dict[str, str] | None = None):
        rows = load() + list((custom or {}).items())
        entries = pynini.union(*[pynini.cross(pynini.escape(a), b) for a, b in rows])
        # An acronym said as a word, alone or heading a compound: ``SCHUFA-Auskunft`` → ``Schufa-Auskunft``.
        compound_tail = pynini.closure(pynini.accep("-") + pynini.closure(LETTER, 1), 0, 1)
        acronyms = pynini.union(*[pynini.cross(a, b) for a, b in load(ACRONYMS)]) + compound_tail
        return self.wrap(text(pynini.union(entries, pynutil.add_weight(acronyms, 0.1)))).optimize()
