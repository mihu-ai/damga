from __future__ import annotations

import pynini
from pynini.lib import pynutil

from ....core.rules import DIGIT, Rule
from ...lexicon import CASE_MARKS, GENDER_MARKS
from ...numbers import ordinal
from .common import text

# Written suffix → (case, gender/number).  An ambiguous suffix takes one fixed reading.
SUFFIXES = {
    "й": ("nom", "m"), "ый": ("nom", "m"), "ой": ("nom", "m"), "ий": ("nom", "m"),
    "го": ("gen", "m"), "ого": ("gen", "m"), "его": ("gen", "m"),
    "му": ("dat", "m"), "ому": ("dat", "m"),
    "м": ("prep", "m"), "ом": ("prep", "m"), "ым": ("ins", "m"),
    "я": ("nom", "f"), "ая": ("nom", "f"), "ья": ("nom", "f"),
    "ю": ("acc", "f"), "ую": ("acc", "f"),
    "е": ("nom", "n"), "ое": ("nom", "n"),
    "х": ("gen", "pl"), "ых": ("gen", "pl"), "ые": ("nom", "pl"), "ми": ("ins", "pl"), "ыми": ("ins", "pl"),
}


class OrdinalReader(Rule):
    """``21-го`` → двадцать первого, ``1930-х`` → тысяча девятьсот тридцатых.  After a preposition ``-й`` is the
    feminine of that case (``в 3-й главе`` → в третьей главе)."""

    name = "ordinal"
    kind = "read"

    def build(self, variants: bool = False):
        digits = pynini.union("0", pynini.union(*"123456789") + pynini.closure(DIGIT))
        decade = pynini.closure(DIGIT, 2) + "0"
        gender = pynini.closure(pynutil.delete(pynini.union(*GENDER_MARKS.values())), 0, 1)
        branches = []
        for suffix, (case, gnum) in SUFFIXES.items():
            if suffix in ("е", "ое"):
                # 1890-е (годы) is plural, 5-е (место) neuter
                branches.append(gender + (decade @ ordinal("nom", "pl")) + pynutil.delete("-" + suffix))
                branches.append(gender + (pynini.difference(digits, decade) @ ordinal(case, gnum)) + pynutil.delete("-" + suffix))
            else:
                branches.append(gender + (digits @ ordinal(case, gnum)) + pynutil.delete("-" + suffix))
        plain = pynini.union(*branches)
        marked = []
        for mark, case in (("gen", "gen"), ("dat", "dat"), ("ins", "ins"), ("prep", "prep"), ("v", "prep")):
            # в 3-й главе → в третьей главе
            marked.append(pynutil.delete(CASE_MARKS[mark]) + gender + (digits @ ordinal(case, "f")) + pynutil.delete("-й"))
        other_marks = pynutil.delete(pynini.union(*CASE_MARKS.values()))
        graph = pynini.union(pynutil.add_weight(pynini.union(*marked), -0.1), plain, other_marks + plain)
        return self.wrap(text(graph)).optimize()
