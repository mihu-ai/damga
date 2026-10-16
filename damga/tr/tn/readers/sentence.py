from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, TR_ALPHA, TR_UPPER, Rule, drop_space, squeeze_space
from ...itn.readers.word import PunctuationReader, WordReader
from ..categories import ALL_CATEGORIES
from ..writers.number import CARDINAL, strip_thousand_dots
from .cardinal import CardinalReader

WEIGHTS = {"cardinal": 1.1, "ordinal": 1.0, "decimal": 1.05, "money": 1.0, "percent": 1.0, "measure": 1.0, "time": 1.0,
           "date": 0.95, "telephone": 0.9, "iban": 0.8, "plate": 0.95, "email": 0.8, "lexicon_entry": 1.0, "word": 100.0, "punctuation": 1.0,
           "short_year": 1.2, "alnum": 1.2, "sign": 1.0, "fraction": 1.0, "range": 1.5, "account": 1.0}


def locative(n: int) -> str:
    """The locative suffix of the spoken number: 2 → ``de`` (*ikide*), 4 → ``te`` (*dörtte*), 10 → ``da`` (*onda*)."""
    word = pynini.shortestpath(pynini.accep(str(n)) @ CARDINAL).string()
    vowel = [c for c in word if c in "aeıioöuü"][-1]
    return ("t" if word[-1] in "çfhkpsşt" else "d") + ("e" if vowel in "eiöü" else "a")


def fractions() -> pynini.Fst:
    """``3/4`` → *dörtte üç*, ``1/2`` → *ikide bir* (a proper fraction, denominator up to 100); ``7/24`` and ``24/7``
    (round the clock) are two numbers.  The denominator is spoken first, so the pairs are listed."""
    pairs = [(f"{n}/{d}", f'cardinal(integer="{d}" suffix="{locative(d)}") cardinal(integer="{n}")')
             for d in range(2, 101) for n in range(1, d) if (n, d) != (7, 24)]
    pairs += [(f"{a}/{b}", f'cardinal(integer="{a}") cardinal(integer="{b}")') for a, b in ((7, 24), (24, 7))]
    return pynini.string_map(pairs).optimize()


ACCOUNT_WORDS = ("hesap numarası", "hesap numaram", "hesap numaranız", "hesap numarasını", "hesap no", "hesap no.",
                 "şube kodu", "şube kodunu", "şube no", "müşteri numarası", "müşteri numaram", "müşteri no")


def account_numbers() -> pynini.Fst:
    """``Hesap no: 1234-5678-90`` → *hesap no: bir iki üç dört, beş altı yedi sekiz, dokuz sıfır*: after a bank word a
    number is dictated digit by digit with a pause between the written groups, not read as an amount."""
    phrases = [(p + colon, " ".join(f'word="{w}"' for w in (p + colon).split(" ")))
               for phrase in ACCOUNT_WORDS for p in (phrase, phrase[0].upper() + phrase[1:]) for colon in ("", ":")]
    group = pynutil.insert('cardinal(digits="') + pynini.closure(DIGIT, 1) + pynutil.insert('")')
    sep = pynini.cross(pynini.union(" ", "-"), ' word="," ')
    return (pynini.string_map(phrases) + pynini.accep(" ") + group + pynini.closure(sep + group)).optimize()


class SentenceReader(Rule):
    name = "sentence"
    kind = "read"

    def build(self, categories=ALL_CATEGORIES, variants: bool = False, custom_vocab=None):
        cats = set(categories)
        w = WEIGHTS
        cardinal = CardinalReader(variants)
        from .decimal import DecimalReader
        decimal = DecimalReader(cardinal, variants)
        branches = []
        if "cardinal" in cats:
            branches.append(pynutil.add_weight(cardinal.fst, w["cardinal"]))
        if "ordinal" in cats:
            from .ordinal import OrdinalReader
            branches.append(pynutil.add_weight(OrdinalReader(cardinal, variants).fst, w["ordinal"]))
        if "decimal" in cats:
            branches.append(pynutil.add_weight(decimal.fst, w["decimal"]))
        if "money" in cats:
            from .money import MoneyReader
            branches.append(pynutil.add_weight(MoneyReader(cardinal, decimal, variants).fst, w["money"]))
        if "percent" in cats:
            from .percent import PercentReader
            branches.append(pynutil.add_weight(PercentReader(cardinal, decimal, variants).fst, w["percent"]))
        if "cardinal" in cats:
            # An abbreviated year (``'19``, ``'22``).
            short_year = (pynutil.insert('cardinal(integer="') + pynutil.delete("'") + NONZERO_DIGIT + DIGIT
                          + pynutil.insert('")'))
            branches.append(pynutil.add_weight(short_year, w["short_year"]))
            # ``Covid-19`` → ``Covid on dokuz``, ``F-35'ler`` → ``F otuz beşler``, ``F16``, ``21-B``: the letters stay
            # a word, the number is read as a number.
            # (a single lower-case letter before a dash is a variable: ``x-1`` is left alone)
            letters = (pynutil.insert('word="') + pynini.union(pynini.closure(TR_UPPER, 1), TR_ALPHA + pynini.closure(TR_ALPHA, 1))
                       + pynutil.insert('" '))
            caps = pynutil.insert('word="') + pynini.closure(TR_UPPER, 1, 3) + pynutil.insert('" ')
            tail = pynutil.insert(' word="') + pynini.closure(TR_ALPHA, 1, 2) + pynutil.insert('"')
            alnum = pynini.union(letters + pynutil.delete("-") + cardinal.unsigned, caps + cardinal.unsigned,
                                 cardinal.unsigned + pynutil.delete("-") + tail)
            branches.append(pynutil.add_weight(alnum, w["alnum"]))
            # Free-standing signs: ``+`` is always ``artı``; ``−`` is a ``-`` the pre-hook found between operands.
            sign = pynutil.insert('word="') + pynini.union(pynini.cross("+", "artı"), pynini.cross("−", "eksi")) + pynutil.insert('"')
            branches.append(pynutil.add_weight(sign, w["sign"]))
            branches.append(pynutil.add_weight(fractions(), w["fraction"]))
            # A range of 3+ digit numbers gets *ile* (``1914-1918``), else the numbers run together; short ones don't.
            big = strip_thousand_dots() @ (NONZERO_DIGIT + pynini.closure(DIGIT, 2))
            num_range = (pynutil.insert('cardinal(integer="') + big + pynini.cross("-", '") word="ile" cardinal(integer="')
                         + big + pynutil.insert('"') + cardinal.suffix + pynutil.insert(")"))
            branches.append(pynutil.add_weight(num_range, w["range"]))
            branches.append(pynutil.add_weight(account_numbers(), w["account"]))
        if "measure" in cats:
            from .measure import MeasureReader
            branches.append(pynutil.add_weight(MeasureReader(cardinal, decimal, variants).fst, w["measure"]))
        if "time" in cats:
            from .time import TimeReader
            branches.append(pynutil.add_weight(TimeReader(variants).fst, w["time"]))
        if "date" in cats:
            from .date import DateReader
            branches.append(pynutil.add_weight(DateReader(variants).fst, w["date"]))
        if "telephone" in cats:
            from .telephone import TelephoneReader
            branches.append(pynutil.add_weight(TelephoneReader(variants).fst, w["telephone"]))
        if "iban" in cats:
            from .iban import IbanReader
            branches.append(pynutil.add_weight(IbanReader(variants).fst, w["iban"]))
        if "plate" in cats:
            from .plate import PlateReader
            branches.append(pynutil.add_weight(PlateReader(variants).fst, w["plate"]))
        if "email" in cats:
            from .email import EmailReader
            branches.append(pynutil.add_weight(EmailReader(variants).fst, w["email"]))
        if "lexicon_entry" in cats or custom_vocab:
            from .lexicon_entry import LexiconEntryReader
            wl = LexiconEntryReader(variants, custom=custom_vocab, builtin="lexicon_entry" in cats)
            if wl.built:
                branches.append(pynutil.add_weight(wl.fst, w["lexicon_entry"]))
        word = pynutil.add_weight(WordReader(variants).fst, w["word"])
        punct = pynutil.add_weight(PunctuationReader(variants).fst, w["punctuation"])
        trailing_dash = pynini.closure(pynutil.delete(pynini.closure("-", 1, 2)), 0, 1)
        token = pynini.union(pynini.union(*branches) + trailing_dash, word).optimize() if branches else word
        token_plus_punct = (pynini.closure(punct + pynutil.insert(" "), 0, 1) + token
                            + pynini.closure(pynutil.insert(" ") + punct, 0, 1))
        # A dash may separate two tokens (ranges, scores: ``3-5 tane`` → ``üç beş tane``).  Two tokens cost far less
        # than one word, so only numbers split at a dash (``e-posta`` stays a word); dates still win on weight.
        sep = pynini.union(squeeze_space, pynini.cross("-", " "))
        graph = token_plus_punct + pynini.closure(sep + token_plus_punct)
        return (drop_space.ques + graph + drop_space.ques).optimize()
