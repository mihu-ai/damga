from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ...numbers import DIGIT_WORD
from ...tn.readers.email_url import TLDS
from .cardinal import text


class EmailUrlReader(Rule):
    """``ali point veli arobase gmail point com`` → ``ali.veli@gmail.com``; spelled letters and digits are joined
    (``g mail`` → ``gmail``).  It must end in a known top-level domain, and the first part is one word or starts with
    a spelled letter, so the words before it stay out."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyz")
        word = pynini.closure(letter, 1)
        digit = pynini.union(pynini.invert(DIGIT_WORD), pynini.cross("une", "1"))
        part = pynini.union(word, pynini.invert(DIGIT_WORD))
        glue = pynutil.delete(" ")
        run = pynini.union(letter, digit) + pynini.closure(glue + pynini.union(letter, digit))   # a b trois → ab3
        # a digit said alone is the digit (point trois → .3), any other word is itself
        word = pynini.difference(word, pynini.project(digit, "input"))
        spelled = pynini.union(word, run, word + glue + run, run + glue + word)                  # g mail → gmail
        first = pynini.union(word, letter + pynini.closure(glue + pynini.union(letter, digit)))
        join = pynini.union(pynini.cross(" point ", "."), pynini.cross(" tiret bas ", "_"), pynini.cross(" tiret ", "-"))
        name = first + pynini.closure(join + spelled, 0, 6)
        tld = pynini.union(*TLDS, *[pynini.cross(" ".join(t), t) for t in TLDS if len(t) > 1])     # e d u → edu
        dot = pynini.cross(" point ", ".")
        host = spelled + pynini.closure(dot + spelled, 0, 3) + dot + tld
        email = name + pynini.cross(pynini.union(" arobase ", " at "), "@") + host
        url = pynini.cross("w w w point ", "www.") + host + pynini.closure(pynini.cross(" slash ", "/") + word, 0, 4)
        bare = part + pynini.closure(dot + part, 0, 3) + dot + pynini.union(*TLDS)
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(bare, 0.5)))).optimize()
