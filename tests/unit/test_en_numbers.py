"""The English number grammars give every number exactly one reading: the native runtime picks one best path, so
two readings at the same weight would make the output depend on the grammar's state order."""
import random

import pytest

pynini = pytest.importorskip("pynini")

from damga.en import numbers as N  # noqa: E402

random.seed(1)
NUMBERS = list(range(0, 2100)) + [random.randrange(10 ** k) for k in range(4, 16) for _ in range(40)]


def outputs(fst, s):
    lattice = pynini.escape(s) @ fst
    return set() if lattice.start() == pynini.NO_STATE_ID else set(lattice.paths().ostrings())


@pytest.mark.parametrize("name", ["CARDINAL", "CARDINAL_NO_AND", "ORDINAL"])
def test_one_reading_per_number(name):
    fst = getattr(N, name)
    bad = [(n, o) for n in NUMBERS if len(o := outputs(fst, str(n))) != 1 and not (name == "ORDINAL" and n == 0)]
    assert not bad, bad[:5]


def test_one_reading_per_year():
    bad = [(y, o) for y in range(1000, 2100) if len(o := outputs(N.YEAR, str(y))) > 1]
    assert not bad, bad[:5]


@pytest.mark.parametrize("digits,words", [("105", "one hundred and five"), ("1005", "one thousand and five"),
                                          ("25000", "twenty five thousand"), ("1984", None), ("2013", None)])
def test_readings(digits, words):
    if words:
        assert pynini.shortestpath(pynini.escape(digits) @ N.CARDINAL).string() == words
    assert outputs(N.YEAR_SPOKEN, digits) or digits not in ("1984", "2013")
