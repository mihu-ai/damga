"""Invariants found by round-trip fuzzing: a phone number never gains a digit, and a unit is not a plate."""
import re

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings
from hypothesis import strategies as st

from damga import InverseNormalizer, TextNormalizer

itn = InverseNormalizer(use_cache=False)
tn = TextNormalizer(use_cache=False)

MOBILE_TAIL = st.text(alphabet="0123456789", min_size=7, max_size=7)
MOBILE_HEAD = st.text(alphabet="0123456", min_size=1, max_size=1)


def _spoken_digits(digits: str) -> str:
    return " ".join(tn.normalize(c) for c in digits)


@settings(max_examples=150, deadline=None)
@given(MOBILE_HEAD, MOBILE_TAIL)
def test_mobile_hundred_then_single_digits_keeps_every_digit(head, tail):
    """``sıfır beş yüz <rest digit by digit>``: the ``yüz`` belongs to the digit before it, no ``1`` is invented."""
    d = "5" + head + "0" + tail
    spoken = "sıfır " + tn.normalize(d[:3]) + " " + _spoken_digits(d[3:])
    assert itn.normalize(spoken) == f"0{d[:3]} {d[3:6]} {d[6:8]} {d[8:]}"


@settings(max_examples=150, deadline=None)
@given(MOBILE_HEAD, MOBILE_TAIL)
def test_mobile_all_single_digits(head, tail):
    d = "5" + head + tail[:1] + tail
    d = d[:10]
    spoken = "sıfır " + _spoken_digits(d)
    assert itn.normalize(spoken) == f"0{d[:3]} {d[3:6]} {d[6:8]} {d[8:]}"


NON_NUMBER_WORDS = ["lira", "dolar", "saat", "nokta", "gmail", "merhaba", "teşekkür", "ederim", "evet", "hayır", "ben",
                    "ev", "araba", "kitap", "güzel", "çok", "gün", "sonra", "adım", "telefon", "adresim", "kat"]


@settings(max_examples=200, deadline=None)
@given(st.lists(st.sampled_from(NON_NUMBER_WORDS), min_size=1, max_size=10))
def test_no_digits_appear_without_a_number_word(words):
    out = itn.normalize(" ".join(words))
    assert not re.search(r"\d", out)


@pytest.mark.parametrize("unit", ["km", "kg", "cm", "mm", "ml", "lt", "gr", "dk", "sn", "mb", "gb", "kb"])
def test_written_number_unit_number_is_not_a_plate(unit):
    text = f"70 {unit} 180"
    assert itn.normalize(text) == text
