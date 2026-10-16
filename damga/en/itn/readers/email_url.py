from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import DIGIT_WORD
from ...tn.readers.email_url import TLDS
from .cardinal import text


def _joined(unit: pynini.Fst) -> pynini.Fst:
    """``a b c`` → ``abc``: units said one by one are written together."""
    return (unit + pynini.closure(pynutil.delete(" ") + unit)).optimize()


class EmailUrlReader(Rule):
    """``ali dot veli at gmail dot com`` → ``ali.veli@gmail.com``.  The address must end in a known top-level domain
    (or follow ``at``, ``www`` or ``http``), so "at" and "dot" in a sentence stay words."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyz")
        digit = pynini.invert(DIGIT_WORD)
        # a digit word in an address is a digit (a one b two → a1b2)
        word = pynini.difference(pynini.closure(letter, 1), pynini.project(digit, "input"))
        # a part of a name: a word, spelled letters and digits, or both (g mail)
        spelled = _joined(pynini.union(letter, digit))
        part = pynini.union(word, digit, spelled, spelled + pynutil.delete(" ") + word)
        join = pynini.union(pynini.cross(" dot ", "."), pynini.cross(" underscore ", "_"),
                            pynini.cross(" dash ", "-"), pynini.cross(" hyphen ", "-"))
        name = part + pynini.closure(join + part, 0, 6)
        dot = pynini.cross(" dot ", ".")
        known = pynini.union(*TLDS)
        tld = pynini.union(known, _joined(letter) @ known)                    # com, c o m
        # a country code after a generic domain: .com.sm, .co.uk
        country = dot + (pynini.union(word, _joined(letter)) @ pynini.closure(letter, 2, 2))
        host = part + pynini.closure(dot + part, 0, 3) + dot + tld + pynini.closure(country, 0, 1)
        # after "at", "www" or "http" it is an address whatever its last part (g mail dot a b c)
        any_host = pynutil.add_weight(part + pynini.closure(dot + part, 1, 4), 0.1)
        email = name + pynini.cross(" at ", "@") + pynini.union(host, any_host)
        www = pynini.cross(pynini.union("w w w dot ", "www dot "), "www.")
        scheme = pynini.union(pynini.cross(pynini.union("h t t p s", "https") + " colon slash slash ", "https://"),
                              pynini.cross(pynini.union("h t t p", "http") + " colon slash slash ", "http://"))
        path = pynini.closure(pynini.cross(" slash ", "/") + part + pynini.closure(join + part, 0, 4), 0, 4)
        url = pynini.union(
            www + host + path,
            pynini.closure(scheme, 0, 1) + www + any_host + path,
            scheme + pynini.union(host, any_host) + path,
        )
        site = pynutil.add_weight(host, 0.5)
        return self.wrap(text(pynini.union(email, url, site))).optimize()
