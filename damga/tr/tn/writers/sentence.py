from __future__ import annotations

import importlib

import pynini

from ....core.rules import Rule
from ...itn.writers.lexicon_entry import LexiconEntryWriter
from ...itn.writers.word import WordWriter
from .cardinal import CardinalWriter


class SentenceWriter(Rule):
    name = "sentence"
    kind = "write"

    def build(self, categories, variants: bool = False):
        cats = set(categories)
        branches = [CardinalWriter(variants).fst, WordWriter(variants).fst, LexiconEntryWriter(variants).fst]
        for name in ("ordinal", "decimal", "money", "percent", "measure", "time", "date", "telephone", "iban", "plate", "email"):
            if name in cats:
                module = importlib.import_module(f".{name}", package=__package__)
                branches.append(getattr(module, f"{name.capitalize()}Writer")(variants).fst)
        token = pynini.union(*branches).optimize()
        return (token + pynini.closure(pynini.accep(" ") + token)).optimize()
