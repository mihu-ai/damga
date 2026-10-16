from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import SIGMA, Rule, drop_space, squeeze_space
from ....tr.itn.readers.word import WordReader
from ...lexicon import NUMBER_WORDS
from ...punctuation import PunctuationReader
from ..categories import ALL_CATEGORIES
from .cardinal import CardinalReader

DEFAULT_WEIGHTS = {
    "cardinal": 1.1, "ordinal": 1.0, "decimal": 1.05, "fraction": 1.0, "range": 1.0, "money": 1.0, "measure": 1.0,
    "time": 1.0, "date": 1.0, "email_url": 1.0, "lexicon_entry": 1.0, "telephone": 0.9, "bank": 0.9, "word": 100.0, "punctuation": 1.0,
}


def rewrites() -> list[tuple[pynini.Fst, float]]:
    """Word-level alternatives (variants mode):

    * *one hundred five* without "and", also *two thousand five*
    * *one and a half* for *one point five*
    * *point seven* / *nought point seven* for *zero point seven*
    * *a hundred*, *a thousand*, *a million*, *a half* for *one …*
    * *million euro* for *million euros*"""
    sigma = SIGMA
    letters = pynini.union(*"abcdefghijklmnopqrstuvwxyz")
    start = pynini.accep('"')                                        # the start of a reading in its text field
    after_half = pynini.union('"', *[" " + w for w in ("million", "billion", "trillion", "percent", "per", "euros",
                                                       "dollars", "pounds", "kilo", "meter", "mile", "degree", "giga",
                                                       "mega", "hour", "minute", "second", "year", "times")])
    scale = pynini.union("hundred", "thousand", "million", "billion")
    other_word = pynini.difference(pynini.closure(letters, 1), pynini.union(*NUMBER_WORDS)).optimize()
    rules = [
        (pynini.cdrewrite(pynini.cross(" and ", " "), scale, letters, sigma), 0.3),
        (pynini.cdrewrite(pynini.cross(" point five", " and a half"), letters, after_half, sigma), 0.4),
        (pynini.cdrewrite(pynutil.delete("zero "), start, "point", sigma), 0.4),
        (pynini.cdrewrite(pynini.cross("zero ", "nought "), start, "point", sigma), 1.0),
        (pynini.cdrewrite(pynini.cross("one ", "a "), start, pynini.union("hundred", "half", "quarter"), sigma), 0.5),
        # "a thousand and five", "a million euros", but not "a thousand three hundred"
        (pynini.cdrewrite(pynini.cross("one ", "a "), start,
                          pynini.union("thousand", "million", "billion")
                          + pynini.union('"', " and ", " " + other_word + pynini.union(" ", '"')), sigma), 0.5),
        (pynini.cdrewrite(pynini.cross(" euros", " euro"), "", "", sigma), 0.6),
    ]
    return [(r.optimize(), w) for r, w in rules]


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
            add("decimal", DecimalReader(cardinal.number, variants).fst)
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
        if "telephone" in cats:
            from .telephone import TelephoneReader
            add("telephone", TelephoneReader(variants).fst)
        if "bank" in cats:
            from .bank import BankReader
            add("bank", BankReader(variants).fst)
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
            # alternatives are weighted behind the default reading
            classes = pynini.union(classes, *[pynutil.add_weight(classes @ rule, weight) for rule, weight in rewrites()])
        token = pynini.union(classes, word).optimize()

        def tpp(t: pynini.Fst) -> pynini.Fst:
            return (pynini.closure(punct + pynutil.insert(" "), 0, 1) + t
                    + pynini.closure(pynutil.insert(" ") + punct, 0, 3))

        unit = tpp(token)
        graph = drop_space.ques + unit + pynini.closure(squeeze_space + unit) + drop_space.ques
        return graph.optimize()
