"""German ITN ``fraction_digits``: spoken fractions as digits with a slash, opt-in."""
import pytest

import damga
from damga.core import engine as engine_mod
from damga.de.itn.fractions import fractions_to_digits


@pytest.fixture(scope="module")
def on():
    return damga.Normalizer(mode="itn", lang="de", fraction_digits=True)


@pytest.fixture(scope="module")
def off():
    return damga.Normalizer(mode="itn", lang="de")


CONVERTED = [
    ("ein halb", "1/2"),
    ("einhalb", "1/2"),
    ("drei viertel", "3/4"),
    ("ein drittel", "1/3"),
    ("zwei fünftel", "2/5"),
    ("neun zehntel", "9/10"),
    ("ein hundertstel", "1/100"),
    ("ein tausendstel", "1/1000"),
    ("ein zwanzigstel", "1/20"),
    ("dreizehn sechzehntel", "13/16"),
    ("fünf zweiunddreißigstel", "5/32"),
    ("dreiundzwanzig viertel", "23/4"),
    ("vier halbe", "4/2"),
    ("dreiviertel", "3/4"),
    ("drei Viertel Liter", "3/4 Liter"),
    ("minus ein halb", "-1/2"),
    ("ein halb.", "1/2."),
    # mixed numbers
    ("zwei ein halb", "2 1/2"),
    ("zweieinhalb", "2 1/2"),
    ("zweieinhalb Stunden", "2 1/2 Stunden"),
    ("zwei und ein halb", "2 1/2"),
    ("zwei und drei viertel", "2 3/4"),
    ("eineinhalb", "1 1/2"),
    ("anderthalb Stunden", "1 1/2 Stunden"),
    ("zwanzig einhalb", "20 1/2"),
]

UNCHANGED = [
    "die Hälfte",
    "ein Viertel der Stadt",
    "drei viertel des Weges",
    "das Stadtviertel",
    "viertel nach drei",
    "drei viertel acht",
    "eine halbe Stunde",
    "ein halbes Brot",
    "ich habe zwei halbe Brote",
    "eins halb",
    "im ersten Viertel",
]


@pytest.mark.parametrize("spoken,written", CONVERTED)
def test_fraction_digits(on, spoken, written):
    assert on.normalize(spoken) == written


@pytest.mark.parametrize("spoken", UNCHANGED)
def test_not_a_fraction(on, off, spoken):
    assert on.normalize(spoken) == off.normalize(spoken)


@pytest.mark.parametrize("spoken", [s for s, _ in CONVERTED])
def test_default_keeps_words(off, spoken):
    assert "/" not in off.normalize(spoken)


def test_default_byte_identical(off):
    assert off.normalize("ein halb") == "ein halb"
    assert off.normalize("drei viertel") == "drei viertel"
    assert off.normalize("zweieinhalb Stunden") == "zweieinhalb Stunden"


def test_details_marked_changed(on):
    res = on.normalize_with_details("drei viertel")
    assert res.text == "3/4" and res.changed


def test_other_numbers_still_normalized(on):
    assert on.normalize("es kostet fünfundzwanzigtausend Euro und ein drittel bleibt") == "es kostet 25.000 Euro und 1/3 bleibt"


def test_post_processor_alone():
    assert fractions_to_digits("23 viertel und 3 halbe") == "23/4 und 3/2"
    assert fractions_to_digits("") == ""


@pytest.mark.skipif(not engine_mod.native_available(), reason="native runtime not built")
def test_native_backend_precompiled():
    n = damga.InverseNormalizer(lang="de", backend="native", fraction_digits=True)
    assert n.engine.backend == "native"
    assert n.normalize("zwei ein halb Liter und drei viertel") == "2 1/2 Liter und 3/4"
