import pytest

from tests.conftest import load_golden

CASES = load_golden("itn.tsv", with_xfail=True)


@pytest.mark.parametrize("spoken,written", CASES)
def test_golden_itn(itn, spoken, written):
    """Spoken → written.  Lines preceded by ``# xfail:`` are tracked gaps (strict: they fail when they start passing)."""
    assert itn.normalize(spoken) == written
