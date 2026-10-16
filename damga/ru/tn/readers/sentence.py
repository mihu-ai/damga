from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import CHAR, Rule, drop_space, squeeze_space
from ....tr.itn.readers.word import PunctuationReader, WordReader
from ..categories import ALL_CATEGORIES

DEFAULT_WEIGHTS = {
    "cardinal": 1.1, "ordinal": 1.0, "decimal": 1.05, "measure": 1.0, "date": 0.9, "time": 1.0, "range": 1.0,
    "email_url": 1.0, "lexicon_entry": 1.0, "bank": 1.0, "fraction": 1.0, "telephone": 1.0,
    "word": 100.0, "punctuation": 1.0,
}


_UPPER = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
_LOWER = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def spelled_acronym() -> pynini.Fst:
    letter = pynini.union(*[pynini.cross(u, lo) for u, lo in zip(_UPPER, _LOWER)])
    spelled = letter + pynini.closure(pynutil.insert(" ") + letter, 1, 5)
    return (pynutil.insert('lexicon_entry(text="') + spelled + pynutil.insert('")')).optimize()


def rewrites() -> pynini.Fst:
    """Word-level alternatives (variants mode), each optional and weighted, in one transducer composed
    once onto the readings (a composition per rule would copy the whole grammar each time):

    * *три целых пять десятых* without "и"
    * *одна тысяча* / *одну тысячу* for *тысяча* / *тысячу* at the start of a number
    * the spelling with ё (*трёх*, *четырёх*, *четвёртый*), which a voice needs to stress the word right
    * *килограмм*, *грамм* for the genitive plural *килограммов*, *граммов*"""
    whole = ("целых", "целая", "целой", "целую", "целыми", "целым")
    options = [
        (pynini.union(*[pynini.cross(f" {w} и ", f" {w} ") for w in whole]), 0.4),
        (pynini.union(pynini.cross('"тысяча', '"одна тысяча'), pynini.cross('"тысячу', '"одну тысячу')), 0.6),
        (pynini.union(pynini.cross("трех", "трёх"), pynini.cross("четырех", "четырёх"),
                      pynini.cross("четверт", "четвёрт")), 0.3),
        (pynini.union(pynini.cross("килограммов", "килограмм"), pynini.cross("граммов", "грамм")), 0.5),
    ]
    step = pynini.union(CHAR, *[pynutil.add_weight(fst, weight) for fst, weight in options])
    return pynini.closure(step).optimize()


class SentenceReader(Rule):
    name = "sentence"
    kind = "read"

    def build(self, categories=ALL_CATEGORIES, variants: bool = False, custom_vocab=None):
        cats = set(categories)
        w = DEFAULT_WEIGHTS
        branches = []

        def add(name: str, fst: pynini.Fst) -> None:
            branches.append(pynutil.add_weight(fst, w[name]))

        if "cardinal" in cats:
            from .cardinal import CardinalReader
            add("cardinal", CardinalReader(variants).fst)
            # bank numbers, slash fractions and telephone numbers are number readings, so they come with the
            # cardinal class
            from .bank import BankReader
            from .fraction import FractionReader
            from .telephone import TelephoneReader
            add("bank", BankReader(variants).fst)
            add("fraction", FractionReader(variants).fst)
            add("telephone", TelephoneReader(variants).fst)
        if "ordinal" in cats:
            from .ordinal import OrdinalReader
            add("ordinal", OrdinalReader(variants).fst)
        if "decimal" in cats:
            from .decimal import DecimalReader
            add("decimal", DecimalReader(variants).fst)
        if "measure" in cats:
            from .measure import MeasureReader
            add("measure", MeasureReader(variants).fst)
        if "date" in cats:
            from .date import DateReader
            add("date", DateReader(variants).fst)
        if "time" in cats:
            from .time import TimeReader
            add("time", TimeReader(variants).fst)
        if "range" in cats:
            from .range import RangeReader
            add("range", RangeReader(variants).fst)
        if "email_url" in cats:
            from .email_url import EmailUrlReader
            add("email_url", EmailUrlReader(variants).fst)
        if "lexicon_entry" in cats or custom_vocab:
            from .lexicon_entry import LexiconEntryReader
            add("lexicon_entry", LexiconEntryReader(variants, custom=custom_vocab).fst)

        word = pynutil.add_weight(WordReader(variants).fst, w["word"])
        punct = pynutil.add_weight(PunctuationReader(variants).fst, w["punctuation"])
        classes = pynini.union(*branches).optimize()
        if variants:
            classes = (classes @ rewrites()).optimize()
            # СССР → с с с р: an acronym spelled letter by letter, just behind leaving the word as written
            classes = pynini.union(classes, pynutil.add_weight(spelled_acronym(), w["word"] + 0.5))
        token = pynini.union(classes, word).optimize()

        def tpp(t: pynini.Fst) -> pynini.Fst:
            return (pynini.closure(punct + pynutil.insert(" "), 0, 1) + t
                    + pynini.closure(pynutil.insert(" ") + punct, 0, 2))

        unit = tpp(token)
        graph = drop_space.ques + unit + pynini.closure(squeeze_space + unit) + drop_space.ques
        return graph.optimize()
