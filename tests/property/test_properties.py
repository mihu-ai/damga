import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings
from hypothesis import strategies as st

from damga import InverseNormalizer, TextNormalizer

itn = InverseNormalizer(use_cache=False)
tn = TextNormalizer(use_cache=False)

def grouped(n: int) -> str:
    return f"{n:,}".replace(",", ".")

@settings(max_examples=300, deadline=None)
@given(st.integers(min_value=0, max_value=999_999_999_999))
def test_cardinal_roundtrip(n):
    spoken = tn.normalize(str(n))
    assert itn.normalize(spoken) == (grouped(n) if n != 1 else "bir")

@settings(max_examples=200, deadline=None)
@given(st.integers(min_value=0, max_value=99), st.integers(min_value=1, max_value=99))
def test_money_roundtrip(lira, kurus):
    written = f"{lira},{kurus:02d} TL"
    assert itn.normalize(tn.normalize(written)) == written

@settings(max_examples=200, deadline=None)
@given(st.text(alphabet="abcçdefgğhıijklmnoöprsştuüvyz ", min_size=1, max_size=40))
def test_plain_words_unchanged(text):
    words = [w for w in text.split() if w]
    if not words:
        return
    cleaned = " ".join(words)
    out = itn.normalize(cleaned)
    assert len(out.split()) <= len(words)
    assert all(ch.isalnum() or ch in " .,'-%:@_+°²³/" for ch in out)

@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=9), min_size=11, max_size=11))
def test_phone_never_invents_digits(digits):
    if digits[0] != 0:
        return
    words = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    spoken = " ".join(words[d] for d in digits)
    out = itn.normalize(spoken).replace(" ", "")
    assert out == "".join(map(str, digits))
