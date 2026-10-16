import pytest

from tests.conftest import load_golden

CASES = load_golden("tn.tsv")

@pytest.mark.parametrize("written,spoken", CASES, ids=[c[0][:40] for c in CASES])
def test_golden_tn(tn, written, spoken):
    assert tn.normalize(written) == spoken
