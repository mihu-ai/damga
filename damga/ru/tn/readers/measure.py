from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASES, NOUNS, SCALES, Noun, adjective
from ...numbers import FEW_CLASS, MANY_CLASS, ONE_CLASS, cardinal, counted, fraction, noun_form, strip_groups
from .common import cased, text
from .decimal import spoken

_I = CASES.index


def _phrase(adj: str, noun: Noun) -> tuple[Noun, str]:
    """квадратный километр: the adjective agrees with the noun; after 2–4 it takes the genitive plural."""
    g, sg, pl = noun
    sg2 = tuple(f"{adjective(adj, c, g)} {sg[_I(c)]}" for c in CASES)
    pl2 = tuple(f"{adjective(adj, c, 'pl')} {pl[_I(c)]}" for c in CASES)
    return (g, sg2, pl2), f"{adjective(adj, 'gen', 'pl')} {sg[1]}"


def _suffixed(noun: Noun, suffix: str) -> Noun:
    """километр + " в час" → километр в час, километра в час …"""
    g, sg, pl = noun
    return (g, tuple(w + suffix for w in sg), tuple(w + suffix for w in pl))


# written unit → (noun, few form or None)
UNITS: dict[str, tuple[Noun, str | None]] = {
    "км": (NOUNS["километр"], None), "м": (NOUNS["метр"], None), "см": (NOUNS["сантиметр"], None),
    "мм": (NOUNS["миллиметр"], None), "кг": (NOUNS["килограмм"], None), "г": (NOUNS["грамм"], None),
    "мг": (NOUNS["миллиграмм"], None), "л": (NOUNS["литр"], None), "мл": (NOUNS["миллилитр"], None),
    "га": (NOUNS["гектар"], None), "км²": _phrase("квадратный", NOUNS["километр"]),
    "км2": _phrase("квадратный", NOUNS["километр"]), "м²": _phrase("квадратный", NOUNS["метр"]),
    "м2": _phrase("квадратный", NOUNS["метр"]), "м³": _phrase("кубический", NOUNS["метр"]),
    "м3": _phrase("кубический", NOUNS["метр"]), "км/ч": (_suffixed(NOUNS["километр"], " в час"), None),
    "м/с": (_suffixed(NOUNS["метр"], " в секунду"), None),
    "°C": (_suffixed(NOUNS["градус"], " Цельсия"), None), "°С": (_suffixed(NOUNS["градус"], " Цельсия"), None),
    "°": (NOUNS["градус"], None), "кВт": (NOUNS["киловатт"], None), "МВт": (NOUNS["мегаватт"], None),
    "ГВт": (NOUNS["гигаватт"], None), "ГБ": (NOUNS["гигабайт"], None), "МБ": (NOUNS["мегабайт"], None),
    "ТБ": (NOUNS["терабайт"], None), "ч": (NOUNS["час"], None), "мин": (NOUNS["минута"], None),
    "сек": (NOUNS["секунда"], None), "%": (NOUNS["процент"], None),
    "руб.": (NOUNS["рубль"], None), "руб": (NOUNS["рубль"], None), "р.": (NOUNS["рубль"], None),
    "₽": (NOUNS["рубль"], None), "коп.": (NOUNS["копейка"], None), "долл.": (NOUNS["доллар"], None),
    "$": (NOUNS["доллар"], None), "€": (NOUNS["евро"], None), "евро": (NOUNS["евро"], None),
    "£": (NOUNS["фунт"], None), "¥": (NOUNS["иена"], None), "USD": (NOUNS["доллар"], None),
    "EUR": (NOUNS["евро"], None), "RUB": (NOUNS["рубль"], None), "GBP": (NOUNS["фунт"], None),
    "экз.": (NOUNS["экземпляр"], None), "с.": (NOUNS["страница"], None), "стр.": (NOUNS["страница"], None),
    "т.": (NOUNS["том"], None),
}
CURRENCY_SIGNS = {"$": "доллар", "€": "евро", "£": "фунт", "₽": "рубль"}
# A sum with two decimals is said in the currency and its hundredth (рублей пятьдесят копеек).  Written currency →
# (currency, hundredth).
MONEY = {"рубль": "копейка", "доллар": "цент", "евро": "цент", "фунт": "пенс"}
MONEY_WRITTEN = {
    **{w: "рубль" for w in ("руб.", "руб", "р.", "₽", "RUB", *NOUNS["рубль"][1], *NOUNS["рубль"][2])},
    **{w: "доллар" for w in ("долл.", "$", "USD", *NOUNS["доллар"][1], *NOUNS["доллар"][2])},
    **{w: "евро" for w in ("€", "EUR", "евро")}, **{w: "фунт" for w in ("£", "GBP")},
}
# Scale words written after a number: 20 млн, 4,5 млрд, 25 тыс.
SCALE_ABBR = {"тыс.": 0, "тыс": 0, "тысяч": 0, "тысячи": 0, "млн": 1, "миллионов": 1, "миллиона": 1,
              "миллион": 1, "млрд": 2, "миллиардов": 2, "миллиарда": 2, "миллиард": 2, "трлн": 3}


class MeasureReader(Rule):
    """A number with a unit, a currency or a percent sign; the unit agrees with the number and both take the case
    of a preposition before them: ``около 51 %`` → около пятидесяти одного процента, ``5 млн руб.`` → пять миллионов
    рублей."""

    name = "measure"
    kind = "read"

    def build(self, variants: bool = False):
        number = strip_groups()
        decimal = number + pynini.union(",", ".") + pynini.closure(DIGIT, 1, 6)
        space = pynutil.delete(pynini.closure(" ", 0, 1))
        classes = (("one", ONE_CLASS), ("few", FEW_CLASS), ("many", MANY_CLASS))

        def amounts(case: str, gender: str) -> dict[str, pynini.Fst]:
            """The number read in ``case``/``gender``, split by the agreement class it gives the noun after it;
            "scaled" is a number with a scale word (20 млн), after which every noun is genitive plural."""
            words = cardinal(case, gender)
            out = {cls: (pynini.intersect(pynini.project(number, "output"), acc) @ words) for cls, acc in classes}
            out = {cls: (number @ f).optimize() for cls, f in out.items()}
            out["frac"] = (decimal @ fraction(case)).optimize()
            if variants and case in ("nom", "acc", "gen"):
                # 2,5 км → два с половиной километра, 1,5 тонны → полторы тонны, 3,5 → три запятая пять
                out["frac"] = pynini.union(out["frac"], pynutil.add_weight(spoken(case, gender), 0.5)).optimize()
            scaled = []
            for k, abbrs in _SCALES_BY_INDEX.items():
                noun = SCALES[k][1]
                short = [a for a in abbrs if a in ("тыс.", "тыс", "млн", "млрд", "трлн")]      # 1,23млрд
                abbr = pynutil.delete(pynini.union(" " + pynini.union(*abbrs), *short))
                by_cls = pynini.union(*[(number @ pynini.intersect(pynini.project(number, "output"), acc)
                                         @ cardinal(case, noun[0])) + pynutil.insert(" " + noun_form(noun, case, cls))
                                        for cls, acc in classes])
                scaled.append(by_cls + abbr)
                scaled.append(out["frac"] + abbr + pynutil.insert(" " + noun_form(noun, case, "frac")))
            out["scaled"] = pynini.union(*scaled).optimize()
            return out

        def unit_reading(case: str) -> pynini.Fst:
            out = []
            for gender in ("m", "f"):
                a = amounts(case, gender)
                units = {w: v for w, v in UNITS.items() if (v[0][0] == "f") == (gender == "f")}
                signs = {s_: NOUNS[n] for s_, n in CURRENCY_SIGNS.items() if (NOUNS[n][0] == "f") == (gender == "f")}
                for cls in ("one", "few", "many", "frac"):
                    after = pynini.union(*[pynutil.delete(pynini.escape(w)) + pynutil.insert(" " + noun_form(noun, case, cls, few))
                                           for w, (noun, few) in units.items()])
                    out.append(a[cls] + space + after)
                # after a scale word every unit is genitive plural: 5 млн руб. → пять миллионов рублей
                after = pynini.union(*[pynutil.delete(pynini.escape(w)) + pynutil.insert(" " + noun[2][1])
                                       for w, (noun, _) in units.items()])
                out.append(a["scaled"] + pynini.closure(space + after, 0, 1))
                # a currency sign before the number: $5 → пять долларов, $4,5 млрд → … миллиарда долларов
                for s_, noun in signs.items():
                    put = pynutil.delete(s_) + space
                    for cls in ("one", "few", "many", "frac"):
                        out.append(put + a[cls] + pynutil.insert(" " + noun_form(noun, case, cls)))
                    out.append(put + a["scaled"] + pynutil.insert(" " + noun[2][1]))
            return pynini.union(*out)

        def money_reading(case: str) -> pynini.Fst:
            out = []
            for currency, hundredth in MONEY.items():
                whole = number @ counted(NOUNS[currency], case)
                cents = pynini.union(pynutil.delete("00"),
                                     pynutil.insert(" ") + (pynini.union(pynutil.delete("0") + pynini.union(*"123456789"),
                                                                         pynini.union(*"123456789") + DIGIT)
                                                            @ counted(NOUNS[hundredth], case)))
                amount = whole + pynutil.delete(pynini.union(",", ".")) + (pynini.closure(DIGIT, 2, 2) @ cents)
                written = [w for w, c in MONEY_WRITTEN.items() if c == currency]
                out.append(amount + pynutil.delete(space + pynini.union(*[pynini.escape(w) for w in written])))
                signs = [s_ for s_, n in CURRENCY_SIGNS.items() if n == currency]
                if signs:
                    out.append(pynutil.delete(pynini.union(*signs)) + space + amount)
            return pynini.union(*out)

        sign = pynini.closure(pynini.union(pynini.cross("-", "минус "), pynini.cross("−", "минус ")), 0, 1)
        money = pynutil.add_weight(cased(money_reading, variants=variants), -0.2)
        return self.wrap(text(sign + pynini.union(cased(unit_reading, variants=variants), money))).optimize()


_SCALES_BY_INDEX: dict[int, list[str]] = {}
for _abbr, _k in SCALE_ABBR.items():
    _SCALES_BY_INDEX.setdefault(_k, []).append(_abbr)
