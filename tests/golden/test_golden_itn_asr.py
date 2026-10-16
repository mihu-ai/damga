import pytest

from tests.conftest import load_golden

CASES = load_golden("itn_asr.tsv", with_xfail=True)


@pytest.mark.parametrize("spoken,written", CASES)
def test_golden_itn_asr(itn, spoken, written):
    """Real recognizer output → expected written form.  Lines preceded by ``# xfail:`` are tracked gaps."""
    assert itn.normalize(spoken) == written
