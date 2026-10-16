from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import SIGMA, Rule, drop_space, squeeze_space
from ....tr.itn.readers.word import PunctuationReader, WordReader
from ...lexicon import MONTHS
from ...numbers import TENS
from ..categories import ALL_CATEGORIES
from .cardinal import CardinalReader

DEFAULT_WEIGHTS = {
    "cardinal": 1.1, "ordinal": 1.0, "decimal": 1.05, "fraction": 1.0, "range": 1.0, "money": 1.0, "measure": 1.0,
    "time": 1.0, "date": 1.0, "email_url": 1.0, "lexicon_entry": 1.0, "bank": 1.0, "telephone": 1.0, "word": 100.0, "punctuation": 1.0,
}


def _belgian_tens() -> pynini.Fst:
    """70–79 and 90–99 the Belgian and Swiss way (soixante-douze → septante-deux, quatre-vingt-onze → nonante et
    un), whole words only.  Huitante/octante is left out."""
    units = ["", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"]
    pairs = []
    for n in list(range(70, 80)) + list(range(90, 100)):
        canon = pynini.shortestpath(pynini.accep(str(n)) @ TENS).string()
        tens = "septante" if n < 80 else "nonante"
        u = n % 10
        pairs.append((canon, tens if u == 0 else (f"{tens} et un" if u == 1 else f"{tens}-{units[u]}")))
    word_end = pynini.union(" ", '"')
    return pynini.cdrewrite(pynini.union(*[pynini.cross(a, b) for a, b in pairs]),
                            pynini.union(" ", '"', "-"), word_end, SIGMA)


def rewrites() -> list[tuple[pynini.Fst, float]]:
    """Word-level alternatives (variants mode):

    * *un janvier* for *premier janvier*
    * *virgule sept* for *zéro virgule sept*
    * *septante* / *nonante* for *soixante-dix* / *quatre-vingt-dix*"""
    month = pynini.union(*MONTHS, *[m.capitalize() for m in MONTHS])
    rules = [
        (pynini.cdrewrite(pynini.cross("premier", "un"), pynini.union('"', " "), " " + month, SIGMA), 0.4),
        (pynini.cdrewrite(pynutil.delete("zéro "), pynini.union('"', " "), "virgule", SIGMA), 0.8),
        (_belgian_tens(), 1.2),
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
        if "cardinal" in cats:
            # Bank numbers are digit readings, so they come with the cardinal class.
            from .bank import BankReader
            add("bank", BankReader(variants).fst)
            # So are phone numbers (``06 12 34 56 78``, ``+33 1 23 45 67 89``).
            from .telephone import TelephoneReader
            add("telephone", TelephoneReader(variants).fst)
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
            # Other readings of the same token, each a small change to the default reading, weighted behind it.
            classes = pynini.union(classes, *[pynutil.add_weight(classes @ rule, weight) for rule, weight in rewrites()])
        token = pynini.union(classes, word).optimize()

        def tpp(t: pynini.Fst) -> pynini.Fst:
            return (pynini.closure(punct + pynutil.insert(" "), 0, 1) + t
                    + pynini.closure(pynutil.insert(" ") + punct, 0, 2))

        unit = tpp(token)
        graph = drop_space.ques + unit + pynini.closure(squeeze_space + unit) + drop_space.ques
        return graph.optimize()
