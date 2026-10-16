from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ....en.tn.readers.email_url import TLDS
from ...numbers import DIGIT_WORD
from .cardinal import text


class EmailUrlReader(Rule):
    """``ali.veli@gmx.de`` → ``ali punkt veli at gmx punkt de``."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZäöüÄÖÜß")
        word = pynini.closure(letter, 1)
        digit = pynutil.insert(" ") + DIGIT_WORD + pynutil.insert(" ")
        sep = pynini.union(pynini.cross(".", " punkt "), pynini.cross("-", " bindestrich "), pynini.cross("_", " unterstrich "))
        part = pynini.closure(pynini.union(word, digit), 1)
        local = part + pynini.closure(sep + part)
        tld = pynini.union(*TLDS)
        domain = part + pynini.closure(pynini.cross(".", " punkt ") + part) + pynini.cross(".", " punkt ") + tld
        email = local + pynini.cross("@", " at ") + domain
        scheme = pynini.union(pynini.cross("https://", "h t t p s doppelpunkt slash slash "),
                              pynini.cross("http://", "h t t p doppelpunkt slash slash "))
        www = pynini.cross("www.", "w w w punkt ")
        path = pynini.closure(pynini.cross("/", " slash ") + pynini.closure(pynini.union(word, digit, sep), 1), 0, 6)
        url = pynini.union(scheme + pynini.closure(www, 0, 1), www) + domain + path + pynini.closure(pynutil.delete("/"), 0, 1)
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(domain + path, 0.5)))).optimize()
