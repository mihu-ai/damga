from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import DIGIT_WORD
from .cardinal import text

TLDS = ["com", "org", "net", "eu", "gouv", "fr", "be", "ch", "lu", "ca", "int", "info", "io", "de", "es", "it", "uk",
        "nl", "edu", "gov"]


class EmailUrlReader(Rule):
    """``ali.veli@gmail.com`` → ``ali point veli arobase gmail point com``, ``www.europa.eu`` → ``w w w point europa
    point eu``."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        word = pynini.closure(letter, 1)
        digit = pynutil.insert(" ") + DIGIT_WORD + pynutil.insert(" ")
        sep = pynini.union(pynini.cross(".", " point "), pynini.cross("-", " tiret "), pynini.cross("_", " tiret bas "))
        part = pynini.closure(pynini.union(word, digit), 1)
        local = part + pynini.closure(sep + part)
        tld = pynini.union(*TLDS)
        domain = part + pynini.closure(pynini.cross(".", " point ") + part) + pynini.cross(".", " point ") + tld
        email = local + pynini.cross("@", " arobase ") + domain
        scheme = pynini.union(pynini.cross("https://", "h t t p s deux points slash slash "),
                              pynini.cross("http://", "h t t p deux points slash slash "))
        www = pynini.cross("www.", "w w w point ")
        path = pynini.closure(pynini.cross("/", " slash ") + pynini.closure(pynini.union(word, digit, sep), 1), 0, 6)
        url = pynini.union(scheme + pynini.closure(www, 0, 1), www) + domain + path + pynini.closure(pynutil.delete("/"), 0, 1)
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(domain + path, 0.5)))).optimize()
