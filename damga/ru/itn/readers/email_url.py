from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...lexicon import ONE, TWO, UNITS, ZERO
from ...tn.readers.email_url import TLDS
from .common import text

# Latin letters as Russian speakers name them, spelled one by one: эй би си → abc.
LETTERS = {"эй": "a", "би": "b", "си": "c", "ди": "d", "и": "e", "эф": "f", "джи": "g", "эйч": "h", "ай": "i",
           "джей": "j", "кей": "k", "эл": "l", "эм": "m", "эн": "n", "о": "o", "оу": "o", "пи": "p", "кью": "q",
           "ар": "r", "эс": "s", "ти": "t", "ю": "u", "ви": "v", "дабл ю": "w", "экс": "x", "уай": "y", "вай": "y",
           "зед": "z", "зет": "z"}
# Letter names that are also everyday words: not taken as the first letter of an address.
_AMBIGUOUS = ("и", "о", "ю")
# Pieces of addresses said as words: джи мейл → gmail, яндекс точка ру → yandex.ru.
WORDS = {"мейл": "mail", "мэйл": "mail", "джимейл": "gmail", "яндекс": "yandex", "хот": "hot", "гугл": "google",
         "аутлук": "outlook", "рамблер": "rambler", "инбокс": "inbox", "лист": "list", "бк": "bk"}
SPOKEN_TLDS = {"ру": "ru", "ком": "com", "нет": "net", "орг": "org", "инфо": "info", "рф": "рф", "су": "su",
               "ио": "io", "би вай": "by", "кей зет": "kz", "ди и": "de", "ю эй": "ua", "и ю": "eu"}
SEPARATORS = {"точка": ".", "дефис": "-", "тире": "-", "нижнее подчеркивание": "_", "подчеркивание": "_",
              "нижнее подчёркивание": "_", "подчёркивание": "_", "амперсанд": "&"}


class EmailUrlReader(Rule):
    """``эй точка би си собака джи мейл точка ком`` → a.bc@gmail.com.  An address needs "собака" (or "www") and a
    known top-level domain at its end."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        latin = pynini.closure(pynini.union(*"abcdefghijklmnopqrstuvwxyz0123456789"), 1)
        digits = {ZERO[0]: "0", ONE["m"][0]: "1", TWO["m"][0]: "2", **{f[0]: str(d) for d, f in UNITS.items()}}
        letter = pynini.union(*[pynini.cross(w, a) for w, a in LETTERS.items()])
        first_letter = pynini.union(*[pynini.cross(w, a) for w, a in LETTERS.items() if w not in _AMBIGUOUS])
        others = pynini.union(latin, *[pynini.cross(w, a) for w, a in {**WORDS, **digits}.items()])
        piece = pynini.union(letter, others)
        first = pynini.union(first_letter, others)
        glue = pynutil.delete(" ")
        part = piece + pynini.closure(glue + piece)
        sep_word = pynini.union(*[pynini.cross(w, s) for w, s in SEPARATORS.items()])
        sep = glue + sep_word + pynini.closure(glue + sep_word, 0, 1) + glue      # c&-d: амперсанд тире
        name = first + pynini.closure(pynini.union(glue, sep) + piece)
        tld = pynini.union(*TLDS, *[pynini.cross(w, t) for w, t in SPOKEN_TLDS.items()])
        dot = pynini.cross(" точка ", ".")
        host = part + pynini.closure(pynini.union(dot, pynini.cross(pynini.union(" дефис ", " тире "), "-")) + part,
                                     0, 4) + dot + tld
        email = name + pynini.cross(" собака ", "@") + host
        www = pynini.cross(pynini.union("www", "дабл ю дабл ю дабл ю", "три дабл ю"), "www") + dot + host
        return self.wrap(text(pynini.union(email, www))).optimize()
