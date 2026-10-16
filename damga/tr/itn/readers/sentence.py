from __future__ import annotations

from typing import TYPE_CHECKING

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule, drop_space, squeeze_space
from ..categories import ALL_CATEGORIES
from .cardinal import CardinalReader
from .word import PunctuationReader, WordReader

DEFAULT_WEIGHTS = {
    "cardinal": 1.1,
    "ordinal": 1.1,
    "decimal": 1.05,
    "money": 1.0,
    "percent": 1.0,
    "measure": 1.0,
    "time": 1.0,
    "date": 1.0,
    "telephone": 0.9,
    "iban": 0.8,
    "plate": 0.95,
    "email": 0.8,
    "address": 1.0,
    "spelling": 0.9,
    "lexicon_entry": 1.0,
    "word": 100.0,
    "punctuation": 1.0,
}


if TYPE_CHECKING:
    from .decimal import DecimalReader

class SentenceReader(Rule):
    name = "sentence"
    kind = "read"

    def build(self, categories=ALL_CATEGORIES, variants: bool = False, custom_vocab=None):
        cats = set(categories)
        w = DEFAULT_WEIGHTS

        cardinal = CardinalReader(variants)
        branches = []
        if "cardinal" in cats:
            branches.append(pynutil.add_weight(cardinal.fst, w["cardinal"]))
        if "ordinal" in cats:
            from .ordinal import OrdinalReader
            branches.append(pynutil.add_weight(OrdinalReader(cardinal, variants).fst, w["ordinal"]))
        decimal: DecimalReader | None = None
        if "decimal" in cats or "money" in cats or "percent" in cats or "measure" in cats:
            from .decimal import DecimalReader
            decimal = DecimalReader(cardinal, variants)
        if "decimal" in cats:
            assert decimal is not None
            branches.append(pynutil.add_weight(decimal.fst, w["decimal"]))
        if "money" in cats:
            from .money import MoneyReader
            assert decimal is not None
            branches.append(pynutil.add_weight(MoneyReader(cardinal, decimal, variants).fst, w["money"]))
        if "percent" in cats:
            from .percent import PercentReader
            assert decimal is not None
            percent = PercentReader(cardinal, decimal, variants)
            branches.append(pynutil.add_weight(percent.fst, w["percent"]))
            branches.append(pynutil.add_weight(percent.hundredth, w["percent"]))
        if "measure" in cats:
            from .measure import MeasureReader
            assert decimal is not None
            branches.append(pynutil.add_weight(MeasureReader(cardinal, decimal, variants).fst, w["measure"]))
        if "time" in cats:
            from .time import TimeReader
            branches.append(pynutil.add_weight(TimeReader(cardinal, variants).fst, w["time"]))
        if "date" in cats:
            from .date import DateReader
            branches.append(pynutil.add_weight(DateReader(cardinal, variants).fst, w["date"]))

        guarded = []
        if "telephone" in cats:
            from .telephone import TelephoneReader
            guarded.append(pynutil.add_weight(TelephoneReader(cardinal, variants).fst, w["telephone"]))
        if "iban" in cats:
            from .iban import IbanReader
            guarded.append(pynutil.add_weight(IbanReader(cardinal, variants).fst, w["iban"]))
        if "plate" in cats:
            from .plate import PlateReader
            branches.append(pynutil.add_weight(PlateReader(cardinal, variants).fst, w["plate"]))
        if "email" in cats:
            from .email import EmailReader
            branches.append(pynutil.add_weight(EmailReader(cardinal, variants).fst, w["email"]))
        if "address" in cats:
            from .address import AddressReader
            branches.append(pynutil.add_weight(AddressReader(cardinal, variants).fst, w["address"]))
        if "spelling" in cats:
            from .spelling import SpellingReader
            branches.append(pynutil.add_weight(SpellingReader(variants).fst, w["spelling"]))
        if "lexicon_entry" in cats or custom_vocab:
            from .lexicon_entry import LexiconEntryReader
            wl = LexiconEntryReader(variants, custom=custom_vocab, builtin="lexicon_entry" in cats)
            if wl.built:
                branches.append(pynutil.add_weight(wl.fst, w["lexicon_entry"]))

        word = pynutil.add_weight(WordReader(variants).fst, w["word"])
        punct = pynutil.add_weight(PunctuationReader(variants).fst, w["punctuation"])
        classes = pynini.union(*branches) if branches else word
        token = pynini.union(classes, word).optimize()

        def tpp(t):
            return pynini.closure(punct + pynutil.insert(" "), 0, 1) + t + pynini.closure(pynutil.insert(" ") + punct, 0, 1)

        unit = tpp(token)
        if guarded:
            from .word import NON_NUMBER_WORD
            g = pynini.union(*guarded)
            follower = pynutil.add_weight(pynutil.insert('word="') + NON_NUMBER_WORD + pynutil.insert('"'), w["word"])
            unit = pynini.union(unit, tpp(g) + squeeze_space + tpp(follower))
            graph = pynini.union(unit + pynini.closure(squeeze_space + unit) + pynini.closure(squeeze_space + tpp(g), 0, 1), tpp(g))
        else:
            graph = unit + pynini.closure(squeeze_space + unit)
        graph = drop_space.ques + graph + drop_space.ques
        return graph.optimize()
