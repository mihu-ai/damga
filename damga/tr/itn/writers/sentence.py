from __future__ import annotations

import pynini

from ....core.rules import Rule
from .cardinal import CardinalWriter
from .word import WordWriter


class SentenceWriter(Rule):
    name = "sentence"
    kind = "write"

    def build(self, categories, variants: bool = False, group_thousands: bool = True,
                 group_four_digits: bool = True, scale_words: bool = False):
        cats = set(categories)
        style = {"group_four_digits": group_four_digits, "scale_words": scale_words}
        cardinal = CardinalWriter(variants, group=group_thousands, **style)
        branches = [cardinal.fst, WordWriter(variants).fst]
        if "ordinal" in cats:
            from .ordinal import OrdinalWriter
            branches.append(OrdinalWriter(variants).fst)
        if "decimal" in cats:
            from .decimal import DecimalWriter
            branches.append(DecimalWriter(variants, **style).fst)
        if "money" in cats:
            from .money import MoneyWriter
            branches.append(MoneyWriter(variants, **style).fst)
        if "percent" in cats:
            from .percent import PercentWriter
            branches.append(PercentWriter(variants, **style).fst)
        if "measure" in cats:
            from .measure import MeasureWriter
            branches.append(MeasureWriter(variants, **style).fst)
        if "time" in cats:
            from .time import TimeWriter
            branches.append(TimeWriter(variants).fst)
        if "date" in cats:
            from .date import DateWriter
            branches.append(DateWriter(variants).fst)
        if "telephone" in cats:
            from .telephone import TelephoneWriter
            branches.append(TelephoneWriter(variants).fst)
        if "iban" in cats:
            from .iban import IbanWriter
            branches.append(IbanWriter(variants).fst)
        if "plate" in cats:
            from .plate import PlateWriter
            branches.append(PlateWriter(variants).fst)
        if "email" in cats:
            from .email import EmailWriter
            branches.append(EmailWriter(variants).fst)
        if "address" in cats:
            from .address import AddressWriter
            branches.append(AddressWriter(variants).fst)
        if "spelling" in cats:
            from .spelling import SpellingWriter
            branches.append(SpellingWriter(variants).fst)
        from .lexicon_entry import LexiconEntryWriter
        branches.append(LexiconEntryWriter(variants).fst)
        token = pynini.union(*branches).optimize()
        return (token + pynini.closure(pynini.accep(" ") + token)).optimize()
