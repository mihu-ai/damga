from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import Rule
from ....en.tn.readers.email_url import TLDS
from ...numbers import DIGIT_WORD
from .cardinal import text


class EmailUrlReader(Rule):
    """``mario punto rossi chiocciola gmail punto com`` → ``mario.rossi@gmail.com``; the address must end in a known
    top-level domain."""

    name = "email_url"
    kind = "read"

    def build(self, variants: bool = False):
        letter = pynini.union(*"abcdefghijklmnopqrstuvwxyz")
        part = pynini.union(pynini.closure(letter, 1), pynini.invert(DIGIT_WORD))
        join = pynini.union(pynini.cross(" punto ", "."), pynini.cross(" trattino basso ", "_"),
                            pynini.cross(" trattino ", "-"))
        name = part + pynini.closure(join + part, 0, 6)
        host = part + pynini.closure(pynini.cross(" punto ", ".") + part, 0, 3) + pynini.cross(" punto ", ".") + pynini.union(*TLDS)
        email = name + pynini.cross(" chiocciola ", "@") + host
        www = pynini.cross(pynini.union("vu vu vu punto ", "www punto "), "www.")
        url = www + host + pynini.closure(pynini.cross(" barra ", "/") + pynini.closure(letter, 1), 0, 4)
        return self.wrap(text(pynini.union(email, url, pynutil.add_weight(host, 0.5)))).optimize()
