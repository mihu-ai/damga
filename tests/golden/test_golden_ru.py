import pytest

from tests.conftest import load_golden

TN = load_golden("ru/tn.tsv")
ITN = load_golden("ru/itn.tsv", with_xfail=True)


@pytest.fixture(scope="module")
def ru_tn():
    from damga import TextNormalizer
    return TextNormalizer(lang="ru", use_cache=False)


@pytest.fixture(scope="module")
def ru_itn():
    from damga import InverseNormalizer
    return InverseNormalizer(lang="ru", use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_golden_ru_tn(ru_tn, written, spoken):
    assert ru_tn.normalize(written) == spoken


@pytest.mark.parametrize("spoken,written", ITN)
def test_golden_ru_itn(ru_itn, spoken, written):
    assert ru_itn.normalize(spoken) == written


# Variants: the other readings, the default first.

@pytest.fixture(scope="module")
def ru_tv():
    from damga import TextNormalizer
    return TextNormalizer(lang="ru", variants=True, use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_first_variant_is_the_default_reading(ru_tv, written, spoken):
    assert ru_tv.normalize_variants(written, n=5)[0] == spoken


@pytest.mark.parametrize("written,alternative", [
    ("Население 1205 человек.", "Население одна тысяча двести пять человек."),
    ("через 1,5 часа", "через полтора часа"),
    ("длина 2,5 км", "длина два с половиной километра"),
    ("длина 3,5 км", "длина три целых пять десятых километра"),
    ("1 мая — праздник", "первого мая — праздник"),
    ("Проверено 7 августа 2014.", "Проверено седьмое августа две тысячи четырнадцатого года."),
    ("Проверено 7 августа 2014.", "Проверено седьмого августа две тысячи четырнадцатого."),
    ("около 3 часов", "около трёх часов"),
    ("весом 5 кг", "весом пять килограмм"),
    ("СССР распался", "с с с р распался"),
])
def test_alternative_readings(ru_tv, written, alternative):
    assert alternative in ru_tv.normalize_variants(written, n=20)


@pytest.mark.parametrize("written,heard,expected", [
    ("Население составляло 1205 человек.", "население составляло тысяча двести пять человек",
     "Население составляло тысяча двести пять человек."),
    ("через 1,5 часа", "через полтора часа", "через полтора часа"),
    ("1 мая — праздник", "первого мая праздник", "первого мая — праздник"),
    ("СССР распался", "с с с р распался", "с с с р распался"),
    ("Население 1205 человек.", "население тысяча двести пять человек", "Население тысяча двести пять человек."),
])
def test_matching_picks_what_was_said(ru_tv, written, heard, expected):
    assert ru_tv.normalize_matching(written, heard) == expected


def test_default_mode_has_one_reading(ru_tn):
    assert ru_tn.normalize_variants("через 1,5 часа", n=10) == [ru_tn.normalize("через 1,5 часа")]
