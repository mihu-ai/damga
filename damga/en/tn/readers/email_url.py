from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import DIGIT_WORD
from .cardinal import text

TLDS = ["com", "org", "net", "eu", "gov", "edu", "int", "io", "ai", "info", "uk", "de", "fr", "es", "it", "nl", "be",
        "ie", "at", "ch", "se", "dk", "fi", "pl", "pt", "gr", "cz", "tr", "ru", "us", "ca", "au", "co"]


class EmailUrlReader(Rule):
    """``ali.veli@gmail.com`` → ``ali dot veli at gmail dot com``, ``www.europa.eu`` → ``w w w dot europa dot eu``."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        word = pynini.closure(letter, 1)
        digit = pynutil.insert(" ") + DIGIT_WORD + pynutil.insert(" ")
        sep = pynini.union(pynini.cross(".", " dot "), pynini.cross("-", " dash "), pynini.cross("_", " underscore "))
        part = pynini.closure(pynini.union(word, digit), 1)
        local = part + pynini.closure(sep + part)
        tld = pynini.union(*TLDS)
        dot = pynini.cross(".", " dot ")
        domain = part + pynini.closure(dot + part) + dot + tld
        # after "@", "www." or "http://" any last part will do (abc@gmail.abc, www.ourdailynews.com.sm)
        any_domain = pynutil.add_weight(part + pynini.closure(dot + part, 1), 0.1)
        email = local + pynini.cross("@", " at ") + pynini.union(domain, any_domain)
        scheme = pynini.union(pynini.cross("https://", "h t t p s colon slash slash "),
                              pynini.cross("http://", "h t t p colon slash slash "))
        www = pynini.cross("www.", "w w w dot ")
        path = pynini.closure(pynini.cross("/", " slash ") + pynini.closure(pynini.union(word, digit, sep), 1), 0, 6)
        host = pynini.union(domain, any_domain)
        # https://www.… reads its www like a bare www.… does
        url = (pynini.union(scheme + www + host, scheme + pynutil.add_weight(host, 0.05), www + host) + path
               + pynini.closure(pynutil.delete("/"), 0, 1))
        bare = domain + path   # europa.eu, ec.europa.eu/info
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(bare, 0.5)))).optimize()
