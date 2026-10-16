import pytest

from tests.conftest import load_golden

TN = load_golden("fr/tn.tsv")
ITN = load_golden("fr/itn.tsv", with_xfail=True)


@pytest.fixture(scope="module")
def fr_tn():
    from damga import TextNormalizer
    return TextNormalizer(lang="fr", use_cache=False)


@pytest.fixture(scope="module")
def fr_itn():
    from damga import InverseNormalizer
    return InverseNormalizer(lang="fr", use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_golden_fr_tn(fr_tn, written, spoken):
    assert fr_tn.normalize(written) == spoken


@pytest.mark.parametrize("spoken,written", ITN)
def test_golden_fr_itn(fr_itn, spoken, written):
    assert fr_itn.normalize(spoken) == written


# Variants: other readings speakers use, the default always first.
@pytest.fixture(scope="module")
def fr_tnv():
    from damga import TextNormalizer
    return TextNormalizer(lang="fr", variants=True, use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_first_variant_is_the_default(fr_tnv, written, spoken):
    assert fr_tnv.normalize_variants(written)[0] == spoken


@pytest.mark.parametrize("written,other", [
    ("2,5 millions de personnes", "deux millions et demi de personnes"),
    ("1,5 milliard €", "un milliard et demi d'euros"),
    ("le 1er janvier", "le un janvier"),
    ("92 voix", "nonante-deux voix"),
    ("75 %", "septante-cinq pour cent"),
    ("0,7 %", "virgule sept pour cent"),
    ("en 1971", "en dix-neuf cent soixante et onze"),
    ("à 12 h", "à midi"),
    ("à 0 h", "à minuit"),
    ("2,5 km", "deux kilomètres et demi"),
    ("1,5 t", "une tonne et demie"),
    ("la période 2014-2020", "la période deux mille quatorze à deux mille vingt"),
])
def test_other_readings(fr_tnv, written, other):
    assert other in fr_tnv.normalize_variants(written, n=20)


@pytest.mark.parametrize("written,heard,expected", [
    ("Il y a 2,5 millions de chômeurs.", "il y a deux millions et demi de chômeurs",
     "Il y a deux millions et demi de chômeurs."),
    ("Il y a 2,5 millions de chômeurs.", "il y a deux virgule cinq millions de chômeurs",
     "Il y a deux virgule cinq millions de chômeurs."),
    ("le 1er janvier 1971", "le un janvier dix-neuf cent soixante et onze", "le un janvier dix-neuf cent soixante et onze"),
    ("92 voix pour", "nonante deux voix pour", "nonante-deux voix pour"),
    ("92 voix pour", "quatre-vingt-douze voix pour", "quatre-vingt-douze voix pour"),
])
def test_matching_picks_what_was_said(fr_tnv, written, heard, expected):
    assert fr_tnv.normalize_matching(written, heard) == expected


def test_default_has_one_reading(fr_tn):
    assert fr_tn.normalize_variants("2,5 millions en 1971") == [fr_tn.normalize("2,5 millions en 1971")]
