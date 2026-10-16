from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from .cardinal import DIGIT_BY_DIGIT
from .common import text

TLDS = ["ru", "su", "рф", "com", "org", "net", "info", "io", "ai", "eu", "by", "kz", "ua", "de", "uk", "us", "edu",
        "gov"]


class EmailUrlReader(Rule):
    """``ivan.petrov@mail.ru`` → ivan точка petrov собака mail точка ru."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        word = pynini.closure(letter, 1)
        digit = pynutil.insert(" ") + (pynini.union(*"0123456789") @ DIGIT_BY_DIGIT) + pynutil.insert(" ")
        sep = pynini.union(pynini.cross(".", " точка "), pynini.cross("-", " дефис "), pynini.cross("_", " нижнее подчеркивание "))
        part = pynini.closure(pynini.union(word, digit), 1)
        tld = pynini.union(*TLDS)
        domain = part + pynini.closure(pynini.cross(".", " точка ") + part) + pynini.cross(".", " точка ") + tld
        email = part + pynini.closure(sep + part) + pynini.cross("@", " собака ") + domain
        scheme = pynini.union(pynini.cross("https://", "эйч ти ти пи эс двоеточие слеш слеш "),
                              pynini.cross("http://", "эйч ти ти пи двоеточие слеш слеш "))
        www = pynini.cross("www.", "www точка ")
        path = pynini.closure(pynini.cross("/", " слеш ") + pynini.closure(pynini.union(word, digit, sep), 1), 0, 6)
        url = pynini.union(scheme + pynini.closure(www, 0, 1), www) + domain + path + pynini.closure(pynutil.delete("/"), 0, 1)
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(domain + path, 0.5)))).optimize()
