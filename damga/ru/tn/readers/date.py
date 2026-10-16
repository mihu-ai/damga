from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, NONZERO_DIGIT, Rule
from ...lexicon import CASE_MARKS, GENDER_MARKS, MONTHS_ANY, MONTHS_GEN, RANGE_DASH, YEAR_FORMS
from ...numbers import CENTURY_FORMS, ROMAN, ordinal
from .common import ANY_CASE_MARK, OTHER_CASE_WEIGHT, text

_GENDER = pynini.closure(pynutil.delete(pynini.union(*GENDER_MARKS.values())), 0, 1)


def _mark(name: str) -> pynini.Fst:
    return pynutil.delete(CASE_MARKS[name]) + _GENDER


class DateReader(Rule):
    """Dates and years, the year an ordinal as Russian says it: ``7 августа 2014`` → седьмого августа две тысячи
    четырнадцатого года ("года" said even when it is not written), ``в 1961 году`` → в тысяча девятьсот шестьдесят
    первом году.
    """

    name = "date"
    kind = "read"

    def build(self, variants: bool = False):
        number = pynini.union(NONZERO_DIGIT + pynini.closure(DIGIT, 0, 3))
        year4 = pynini.union("1", "2") + DIGIT + DIGIT + DIGIT
        sp = pynini.accep(" ")

        # a year written before a form of "год"
        with_noun = []
        for form, (case, gnum) in YEAR_FORMS.items():
            plain = (number @ ordinal(case, gnum)) + sp + form
            with_noun.append(_GENDER + plain)
            for mark in ("gen", "acc", "ins", "prep", "v", "nom"):
                with_noun.append(_mark(mark) + plain)
            if form == "году":
                with_noun.append(_mark("dat") + (number @ ordinal("dat", "m")) + sp + form)
            else:
                with_noun.append(_mark("dat") + plain)
        abbrev = pynutil.delete(" г.") | pynutil.delete("г.")
        # "(2008 г.)" alone is read in the nominative, "с 2008 г." in the genitive
        abbrev_reading: dict[str | None, tuple[str, str]] = {
            None: ("nom", "год"), "nom": ("nom", "год"), "gen": ("gen", "года"), "v": ("prep", "году"),
            "prep": ("prep", "году"), "dat": ("dat", "году"), "acc": ("nom", "год"), "ins": ("ins", "годом")}
        for abbrev_mark, (case, noun) in abbrev_reading.items():
            head = _GENDER if abbrev_mark is None else _mark(abbrev_mark)
            with_noun.append(head + (number @ ordinal(case, "m")) + abbrev + pynutil.insert(" " + noun))
        plural_abbrev = pynutil.delete(pynini.union(" гг.", "гг."))
        with_noun.append(_mark("v") + (number @ ordinal("prep", "pl")) + plural_abbrev + pynutil.insert(" годах"))
        with_noun.append(_GENDER + (number @ ordinal("gen", "pl")) + plural_abbrev + pynutil.insert(" годов"))

        # the year in a date: genitive, "года" said whether or not it is written
        said_year = [pynutil.insert(" года"), pynini.accep(" года"), pynini.cross(pynini.union(" г.", "г."), " года")]
        if variants:
            said_year.append(pynutil.add_weight(pynini.accep(""), 0.6))        # 7 августа 2014 without "года"
        year_gen = (year4 @ ordinal("gen", "m")) + pynini.union(*said_year)
        day_digits = pynini.union(*[str(d) for d in range(1, 32)], *[f"0{d}" for d in range(1, 10)])
        day_plain = day_digits @ pynini.union(pynutil.delete("0") + NONZERO_DIGIT, NONZERO_DIGIT, NONZERO_DIGIT + DIGIT)
        month = pynini.union(*MONTHS_GEN)
        tail = pynini.closure(sp + year_gen, 0, 1)
        dates = []
        # a date is genitive in a sentence (умер 6 апреля), nominative as a heading (8 марта — …), which the
        # pre-hook marks
        date_cases: tuple[tuple[str | None, str], ...] = (
            (None, "gen"), ("nom", "nom"), ("gen", "gen"), ("dat", "dat"), ("acc", "acc"), ("v", "acc"),
            ("ins", "ins"), ("prep", "prep"))
        numeric = pynini.union(*[pynini.cross(pynini.union(f".{m:02d}.", f".{m}."), " " + name + " ")
                                 for m, name in enumerate(MONTHS_GEN, 1)])
        # 31.01.06: a two-digit year, said as written (ноль шестого года, восемьдесят шестого года)
        numeric2 = pynini.union(*[pynini.cross(f".{m:02d}.", " " + name + " ") for m, name in enumerate(MONTHS_GEN, 1)])
        short_year = pynini.union(pynini.cross("0", "ноль ") + (pynini.union(*"123456789") @ ordinal("gen", "m")),
                                  (pynini.union(*"123456789") + DIGIT) @ ordinal("gen", "m")) + pynutil.insert(" года")
        day2 = pynini.union(*[f"{d:02d}" for d in range(1, 32)])          # 1.10.12 is not a date, 01.10.12 is
        heads: dict[str, list[pynini.Fst]] = {}
        for date_mark, case in date_cases:
            heads.setdefault(case, []).append(_GENDER if date_mark is None else _mark(date_mark))
        for case, own in heads.items():
            paths = list(own)
            if variants and case in ("nom", "gen"):
                # the other case at a cost: первое мая as a heading or subject, первого мая in a sentence
                paths.append(pynutil.add_weight(ANY_CASE_MARK + _GENDER, OTHER_CASE_WEIGHT[case]))
            date_head = pynini.union(*paths)
            day = day_plain @ ordinal(case, "n")
            dates.append(date_head + day + pynini.union(sp + month + tail, numeric + year_gen))
            dates.append(date_head + (day2 @ day) + numeric2 + short_year)

        # a month and a year: в январе 2008 (года)
        month_year = pynini.union(*MONTHS_ANY) + sp + year_gen
        # "в 1511": a bare year after "в"; "в 2001 —2003": both ends of a bare span
        bare = _mark("v") + (year4 @ ordinal("prep", "m"))
        bare = pynini.union(bare, bare + pynini.cross(pynini.union("—", "–", RANGE_DASH), " — ") + (year4 @ ordinal("prep", "m")))
        # XXI век → двадцать первый век, в XIX веке → в девятнадцатом веке, XV—XVI вв. stays as it is
        centuries = []
        for form, (case, gnum) in CENTURY_FORMS.items():
            said = {"вв.": "веков", "в.": "века"}.get(form, form)
            centuries.append(pynini.closure(pynutil.delete(pynini.union(*CASE_MARKS.values())), 0, 1)
                             + (ROMAN @ ordinal(case, gnum)) + pynini.cross(pynini.union(" " + form, form) if "." in form else " " + form, " " + said))
        # a span of years before "годах", "годов" …: both ends in that case (в 1988—1989 годах)
        dash = pynini.cross(pynini.union("—", "–", "-", RANGE_DASH), " — ")
        spans = []
        for form, (case, gnum) in YEAR_FORMS.items():
            if gnum != "pl":
                continue
            span = (year4 @ ordinal(case, "m")) + dash + (year4 @ ordinal(case, "m")) + sp + form
            spans += [_GENDER + span] + [_mark(m) + span for m in ("gen", "dat", "acc", "ins", "prep", "v", "nom")]
        span_reading: dict[str | None, tuple[str, str]] = {
            None: ("gen", "годов"), "v": ("prep", "годах"), "prep": ("prep", "годах"), "gen": ("gen", "годов"),
            "dat": ("dat", "годам")}
        for span_mark, (case, noun) in span_reading.items():
            head = _GENDER if span_mark is None else _mark(span_mark)
            spans.append(head + (year4 @ ordinal(case, "m")) + dash + (year4 @ ordinal(case, "m"))
                         + pynutil.delete(pynini.union(" гг.", "гг.")) + pynutil.insert(" " + noun))
        graph = pynini.union(*with_noun, *dates, month_year, bare, *centuries, *spans)
        return self.wrap(text(graph)).optimize()
