import pytest

from tests.conftest import load_golden

TN = load_golden("it/tn.tsv")
ITN = load_golden("it/itn.tsv", with_xfail=True)


@pytest.fixture(scope="module")
def it_tn():
    from damga import TextNormalizer
    return TextNormalizer(lang="it", use_cache=False)


@pytest.fixture(scope="module")
def it_itn():
    from damga import InverseNormalizer
    return InverseNormalizer(lang="it", use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_golden_it_tn(it_tn, written, spoken):
    assert it_tn.normalize(written) == spoken


@pytest.mark.parametrize("spoken,written", ITN)
def test_golden_it_itn(it_itn, spoken, written):
    assert it_itn.normalize(spoken) == written


# Variants: the other readings speakers use, and the choice of the one a recording supports.
@pytest.fixture(scope="module")
def it_tnv():
    from damga import TextNormalizer
    return TextNormalizer(lang="it", variants=True, use_cache=False)


@pytest.mark.parametrize("written,spoken", TN, ids=[c[0][:40] for c in TN])
def test_it_first_variant_is_the_default(it_tnv, written, spoken):
    assert it_tnv.normalize_variants(written, n=5)[0] == spoken


@pytest.mark.parametrize("written,expected", [
    ("Nel 2016", ["Nel duemila e sedici", "Nel venti sedici"]),
    ("1500 persone", ["mille e cinquecento persone"]),
    ("2,5 miliardi di euro", ["due miliardi e mezzo di euro"]),
    ("2,5 km", ["due chilometri e mezzo"]),
    ("il 10%", ["il dieci per cento"]),
    ("Il 2 febbraio", ["Il due di febbraio"]),
    ("alle 9.30", ["alle nove e mezza"]),
    ("alle 9.15", ["alle nove e un quarto"]),
    ("nel 1986", ["nel millenovecentottantasei"]),
    ("un aumento 5-10%", ["un aumento dal cinque al dieci percento", "un aumento tra il cinque e il dieci percento"]),
    ("8-11 anni", ["dall'otto all'undici anni", "tra l'otto e l'undici anni"]),
])
def test_it_variants(it_tnv, written, expected):
    variants = it_tnv.normalize_variants(written, n=20)
    for e in expected:
        assert e in variants


@pytest.mark.parametrize("written,unexpected", [
    ("un aumento del 5-10%", "del dal"),          # a range after a preposition keeps its plain reading
    ("dall'8-11 marzo", "dall'dal"),
    ("0,5", "zero e mezzo"),
    ("1,50 €", "e mezzo"),
])
def test_it_no_wrong_variant(it_tnv, written, unexpected):
    assert not any(unexpected in v for v in it_tnv.normalize_variants(written, n=20))


@pytest.mark.parametrize("written,heard,expected", [
    ("Nel 2016 abbiamo speso 2,5 miliardi di euro.", "nel duemila e sedici abbiamo speso due miliardi e mezzo di euro",
     "Nel duemila e sedici abbiamo speso due miliardi e mezzo di euro."),
    ("giovedì 5 ottobre", "giovedì cinque di ottobre", "giovedì cinque di ottobre"),
    ("Nel 2016", "nel duemilasedici", "Nel duemilasedici"),          # ties keep the default
])
def test_it_matching(it_tnv, written, heard, expected):
    assert it_tnv.normalize_matching(written, heard) == expected


def test_it_default_has_one_reading(it_tn):
    assert it_tn.normalize_variants("Nel 2016 alle 9.30", n=10) == [it_tn.normalize("Nel 2016 alle 9.30")]
