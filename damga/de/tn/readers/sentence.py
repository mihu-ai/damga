from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule, drop_space, squeeze_space
from ....tr.itn.readers.word import PunctuationReader, WordReader
from ..categories import ALL_CATEGORIES
from .cardinal import CardinalReader

DEFAULT_WEIGHTS = {
    "cardinal": 1.1, "ordinal": 1.0, "decimal": 1.05, "fraction": 1.0, "range": 1.0, "money": 1.0, "measure": 1.0,
    "time": 1.0, "date": 1.0, "email_url": 1.0, "bank": 1.0, "telephone": 1.0, "lexicon_entry": 1.0, "word": 100.0, "punctuation": 1.0,
}


class SentenceReader(Rule):
    name = "sentence"
    kind = "read"

    def build(self, categories=ALL_CATEGORIES, variants: bool = False, custom_vocab=None):
        cats = set(categories)
        w = DEFAULT_WEIGHTS
        cardinal = CardinalReader(variants)
        branches = []

        def add(name: str, fst: pynini.Fst) -> None:
            branches.append(pynutil.add_weight(fst, w[name]))

        if "cardinal" in cats:
            add("cardinal", cardinal.fst)
        if "ordinal" in cats:
            from .ordinal import OrdinalReader
            add("ordinal", OrdinalReader(variants).fst)
        if "decimal" in cats:
            from .decimal import DecimalReader
            add("decimal", DecimalReader(variants).fst)
        if "fraction" in cats:
            from .fraction import FractionReader
            add("fraction", FractionReader(variants).fst)
        if "range" in cats:
            from .range import RangeReader
            add("range", RangeReader(cardinal.number, variants).fst)
        if "money" in cats:
            from .money import MoneyReader
            add("money", MoneyReader(variants).fst)
        if "measure" in cats:
            from .measure import MeasureReader
            add("measure", MeasureReader(variants).fst)
        if "time" in cats:
            from .time import TimeReader
            add("time", TimeReader(variants).fst)
        if "date" in cats:
            from .date import DateReader
            add("date", DateReader(variants).fst)
        if "email_url" in cats:
            from .email_url import EmailUrlReader
            add("email_url", EmailUrlReader(variants).fst)
        if "bank" in cats:
            from .bank import BankReader
            add("bank", BankReader(variants).fst)
        if "telephone" in cats:
            from .telephone import TelephoneReader
            add("telephone", TelephoneReader(variants).fst)
        if "lexicon_entry" in cats or custom_vocab:
            from .lexicon_entry import LexiconEntryReader
            add("lexicon_entry", LexiconEntryReader(variants, custom=custom_vocab).fst)

        word = pynutil.add_weight(WordReader(variants).fst, w["word"])
        punct = pynutil.add_weight(PunctuationReader(variants).fst, w["punctuation"])
        token = pynini.union(*branches, word).optimize()

        def tpp(t: pynini.Fst) -> pynini.Fst:
            return (pynini.closure(punct + pynutil.insert(" "), 0, 1) + t
                    + pynini.closure(pynutil.insert(" ") + punct, 0, 2))

        unit = tpp(token)
        graph = drop_space.ques + unit + pynini.closure(squeeze_space + unit) + drop_space.ques
        return graph.optimize()
