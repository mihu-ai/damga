from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ....en.tn.readers.email_url import TLDS
from ...numbers import DIGIT_WORD
from .cardinal import text


class EmailUrlReader(Rule):
    """``ali punkt veli at gmx punkt de`` → ``ali.veli@gmx.de``; the address must end in a known top-level domain.
    A name may be spelled letter by letter and carry digits."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyzäöüß")
        digit = pynini.invert(DIGIT_WORD)
        word = pynini.difference(pynini.closure(letter, 1), pynini.project(digit, "input"))   # "drei" is a 3
        glue = pynutil.delete(" ")
        # spelled letters and digits, optionally joined to a word (g mail)
        spelled = (pynini.closure(word + glue, 0, 1) + pynini.union(letter, digit)
                   + pynini.closure(glue + pynini.union(letter, digit)) + pynini.closure(glue + word, 0, 1))
        part = pynini.union(word, digit, spelled)
        join = pynini.union(pynini.cross(" punkt ", "."), pynini.cross(" unterstrich ", "_"),
                            pynini.cross(" minus ", "-"), pynini.cross(" bindestrich ", "-"))
        name = part + pynini.closure(join + part, 0, 6)
        tld = pynini.union(*TLDS, *[pynini.cross(" ".join(t), t) for t in TLDS if len(t) > 1])
        host = part + pynini.closure(pynini.cross(" punkt ", ".") + part, 0, 3) + pynini.cross(" punkt ", ".") + tld
        email = name + pynini.cross(pynini.union(" at ", " ät "), "@") + host
        scheme = pynini.union(*[pynini.cross(pynini.union(s, " ".join(s)) + " doppelpunkt slash slash ", s + "://")
                                for s in ("https", "http")])
        url = pynini.closure(scheme, 0, 1) + pynini.cross("w w w punkt ", "www.") + host
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(host, 0.5)))).optimize()
