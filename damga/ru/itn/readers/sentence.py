from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule, drop_space, squeeze_space
from ....tr.itn.readers.word import PunctuationReader, WordReader
from ..categories import ALL_CATEGORIES
from .cardinal import CardinalReader

DEFAULT_WEIGHTS = {"cardinal": 1.1, "ordinal": 1.1, "decimal": 1.05, "measure": 1.0, "date": 0.9, "time": 1.0,
                   "telephone": 1.0, "email_url": 1.0, "lexicon_entry": 1.0, "word": 100.0, "punctuation": 1.0}


class SentenceReader(Rule):
    name = "sentence"
    kind = "read"

    def build(self, categories=ALL_CATEGORIES, variants: bool = False, custom_vocab=None, group: bool = True):
        cats = set(categories)
        w = DEFAULT_WEIGHTS
        cardinal = CardinalReader(variants, group=group)
        branches = []

        def add(name: str, fst: pynini.Fst) -> None:
            branches.append(pynutil.add_weight(fst, w[name]))

        if "cardinal" in cats:
            add("cardinal", cardinal.fst)
        from .decimal import DecimalReader
        decimal = DecimalReader(variants)
        if "decimal" in cats:
            add("decimal", decimal.fst)
        if "ordinal" in cats:
            from .ordinal import OrdinalReader
            add("ordinal", OrdinalReader(variants).fst)
        if "measure" in cats:
            from .measure import MeasureReader
            add("measure", MeasureReader(cardinal.digits, decimal.number, cardinal.with_scale, variants).fst)
        if "date" in cats:
            from .date import DateReader
            add("date", DateReader(variants).fst)
        if "time" in cats:
            from .time import TimeReader
            add("time", TimeReader(variants).fst)
        if "telephone" in cats:
            from .telephone import TelephoneReader
            add("telephone", TelephoneReader(variants).fst)
        if "email_url" in cats:
            from .email_url import EmailUrlReader
            add("email_url", EmailUrlReader(variants).fst)
        if custom_vocab:
            from .lexicon_entry import LexiconEntryReader
            wl = LexiconEntryReader(variants, custom=custom_vocab)
            if wl.built:
                add("lexicon_entry", wl.fst)

        word = pynutil.add_weight(WordReader(variants).fst, w["word"])
        punct = pynutil.add_weight(PunctuationReader(variants).fst, w["punctuation"])
        token = pynini.union(*branches, word).optimize()

        def tpp(t: pynini.Fst) -> pynini.Fst:
            return (pynini.closure(punct + pynutil.insert(" "), 0, 1) + t
                    + pynini.closure(pynutil.insert(" ") + punct, 0, 2))

        unit = tpp(token)
        graph = drop_space.ques + unit + pynini.closure(squeeze_space + unit) + drop_space.ques
        return graph.optimize()
