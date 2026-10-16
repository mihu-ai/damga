import pytest

from tests.conftest import load_golden

TN = load_golden("en/tn.tsv")
ITN = load_golden("en/itn.tsv", with_xfail=True)


@pytest.fixture(scope="module")
def en_tn():
    from damga import TextNormalizer
    return TextNormalizer(lang="en", use_cache=False)


@pytest.fixture(scope="module")
def en_itn():
    from damga import InverseNormalizer
    return InverseNormalizer(lang="en", use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_golden_en_tn(en_tn, written, spoken):
    assert en_tn.normalize(written) == spoken


@pytest.mark.parametrize("spoken,written", ITN)
def test_golden_en_itn(en_itn, spoken, written):
    assert en_itn.normalize(spoken) == written


@pytest.fixture(scope="module")
def en_tnv():
    from damga import TextNormalizer
    return TextNormalizer(lang="en", variants=True)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_first_variant_is_the_default_reading(en_tnv, written, spoken):
    assert en_tnv.normalize_variants(written, n=5)[0] == spoken


@pytest.mark.parametrize("written,alternative", [
    ("in 2013", "in twenty thirteen"),
    ("in 2005", "in two thousand five"),
    ("about 1300 persons", "about thirteen hundred persons"),
    ("105 jobs", "one hundred five jobs"),
    ("It grew 1.5%", "It grew one and a half percent"),
    ("0.7 of GNI", "point seven of GNI"),
    ("on 6 December", "on December the sixth"),
    ("on 6 December", "on six December"),
    ("the 1990s", "the nineties"),
    ("€5 million", "five million euro"),
    ("$1 million", "a million dollars"),
    ("call 020 7946 0958", "call oh two oh seven nine four six oh nine five eight"),
])
def test_alternative_readings(en_tnv, written, alternative):
    assert alternative in en_tnv.normalize_variants(written, n=30)


def test_no_broken_readings(en_tnv):
    """Readings never leave a written form half read (no digits left when the default has none)."""
    for written in ("In 2013 we paid €5 million.", "on 6 December 2012", "105 jobs in the 1990s"):
        for v in en_tnv.normalize_variants(written, n=30):
            assert not any(c.isdigit() for c in v), v


@pytest.mark.parametrize("written,heard,expected", [
    ("In 2013 we paid €5 million.", "in twenty thirteen we paid five million euro", "In twenty thirteen we paid five million euro."),
    ("2008. We do not", "twenty oh eight we do not", "twenty oh eight. We do not"),
    ("in 2005", "in two thousand and five", "in two thousand and five"),
])
def test_matching_picks_what_was_said(en_tnv, written, heard, expected):
    assert en_tnv.normalize_matching(written, heard) == expected


def test_matching_keeps_the_default_for_an_unrelated_transcript(en_tnv):
    assert en_tnv.normalize_matching("in 2005", "something else entirely", max_distance=0.5) == "in two thousand and five"


def test_default_mode_gives_one_reading(en_tn):
    assert en_tn.normalize_variants("in 2013", n=10) == ["in two thousand thirteen"]
