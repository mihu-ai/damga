from __future__ import annotations

from typing import Callable

import pynini
from pynini.lib import pynutil

from ...lexicon import CASE_MARKS, GENDER_MARKS

OBLIQUE = ("gen", "dat", "acc", "ins", "prep")


def text(fst: pynini.Fst) -> pynini.Fst:
    return pynutil.insert('text="') + fst + pynutil.insert('"')


# variants mode: the case a number takes when the pre-hook's guess is wrong or missing (a verb governs it:
# составляет тысячу; a date read as a heading: первое мая), each weighted behind the marked reading.  Only the
# cases speakers mix up; a dative, instrumental or prepositional the text does not ask for (тремя книги) is not
# a reading.
OTHER_CASE_WEIGHT = {"nom": 0.6, "gen": 0.6, "acc": 0.7}
OTHER_GENDER_WEIGHT = 0.7
ANY_CASE_MARK = pynini.closure(pynutil.delete(pynini.union(*CASE_MARKS.values())), 0, 1).optimize()
ANY_GENDER_MARK = pynini.closure(pynutil.delete(pynini.union(*GENDER_MARKS.values())), 0, 1).optimize()


def case_heads(v_case: str = "acc", default: str = "nom") -> dict[str, list[pynini.Fst]]:
    """The marks that select each case: none → ``default``, the case's own mark, "в" → ``v_case``."""
    heads: dict[str, list[pynini.Fst]] = {c: [] for c in ("nom", *OBLIQUE)}
    heads[default].append(pynini.accep(""))
    for case in OBLIQUE:
        heads[case].append(pynutil.delete(CASE_MARKS[case]))
    heads[v_case].append(pynutil.delete(CASE_MARKS["v"]))
    heads["nom"].append(pynutil.delete(CASE_MARKS["nom"]))
    return heads


def head(own: list[pynini.Fst], case: str, variants: bool) -> pynini.Fst | None:
    """The marks that lead to ``case``; in variants mode any mark (or none) leads there too, at a cost."""
    paths = list(own)
    if variants and case in OTHER_CASE_WEIGHT:
        paths.append(pynutil.add_weight(ANY_CASE_MARK, OTHER_CASE_WEIGHT[case]))
    return pynini.union(*paths).optimize() if paths else None


def cased(build: Callable[[str], pynini.Fst], v_case: str = "acc", default: str = "nom",
          variants: bool = False) -> pynini.Fst:
    """``build(case)`` for the case the pre-hook marked before the number (none: ``default``); "в" means
    ``v_case``.  A gender mark the reading does not need is dropped."""
    gender = ANY_GENDER_MARK
    if not variants:
        branches = [gender + build(default)]
        for case in OBLIQUE:
            branches.append(pynutil.delete(CASE_MARKS[case]) + gender + build(case))
        branches.append(pynutil.delete(CASE_MARKS["v"]) + gender + build(v_case))
        branches.append(pynutil.delete(CASE_MARKS["nom"]) + gender + build("nom"))
        return pynini.union(*branches).optimize()
    branches = []
    for case, own in case_heads(v_case, default).items():
        h = head(own, case, variants)
        if h is not None:
            branches.append(h + gender + build(case))
    return pynini.union(*branches).optimize()


def gendered(build: Callable[[str, str], pynini.Fst], case: str, variants: bool = False) -> pynini.Fst:
    """``build(case, gender)`` for the gender the pre-hook marked (none: masculine)."""
    if not variants:
        return pynini.union(build(case, "m"), pynutil.delete(GENDER_MARKS["f"]) + build(case, "f"),
                            pynutil.delete(GENDER_MARKS["n"]) + build(case, "n")).optimize()
    other = pynutil.add_weight(ANY_GENDER_MARK, OTHER_GENDER_WEIGHT)
    return pynini.union(pynini.union(pynini.accep(""), other) + build(case, "m"),
                        pynini.union(pynutil.delete(GENDER_MARKS["f"]), other) + build(case, "f"),
                        pynini.union(pynutil.delete(GENDER_MARKS["n"]), other) + build(case, "n")).optimize()


def cased_gendered(build: Callable[[str, str], pynini.Fst], v_case: str = "acc",
                   variants: bool = False) -> pynini.Fst:
    if not variants:
        branches = [gendered(build, "nom")]
        for case in OBLIQUE:
            branches.append(pynutil.delete(CASE_MARKS[case]) + gendered(build, case))
        branches.append(pynutil.delete(CASE_MARKS["v"]) + gendered(build, v_case))
        branches.append(pynutil.delete(CASE_MARKS["nom"]) + gendered(build, "nom"))
        return pynini.union(*branches).optimize()
    branches = []
    for case, own in case_heads(v_case).items():
        h = head(own, case, variants)
        if h is not None:
            branches.append(h + gendered(build, case, variants))
    return pynini.union(*branches).optimize()
