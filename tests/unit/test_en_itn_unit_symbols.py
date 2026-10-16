import ast
import pathlib

import pytest

from damga import InverseNormalizer, Normalizer
from damga.en.itn.units import apply_unit_symbols


@pytest.fixture(scope="module")
def units():
    return InverseNormalizer(lang="en", unit_symbols=True)


@pytest.fixture(scope="module")
def plain():
    return InverseNormalizer(lang="en")


CASES = [
    ("two hundred meters", "200 m"),
    ("one meter", "1 m"),
    ("Two Hundred Meters.", "200 m."),
    ("two hundred kilometers per hour", "200 km/h"),
    ("one hundred twenty kilometers an hour", "120 km/h"),
    ("sixty miles per hour", "60 mph"),
    ("ten meters per second", "10 m/s"),
    ("fifty six point three kilograms", "56.3 kg"),
    ("five thousand meters", "5,000 m"),
    ("three hundred kilometres, then left", "300 km, then left"),
    ("twelve feet", "12 ft"),
    ("two inches", "2 in"),
    ("point five liters", "0.5 l"),
    ("two hundred fifty milliliters", "250 ml"),
    ("three hundred milliseconds", "300 ms"),
    ("twenty seconds", "20 s"),
    ("forty five minutes", "45 min"),
    ("the room is twenty five square meters.", "the room is 25 m²."),
    ("one thousand two hundred cubic centimeters", "1,200 cm³"),
    ("one hundred megabytes per second", "100 MB/s"),
    ("sixty four gigabytes", "64 GB"),
    ("fifty megabits per second", "50 Mbps"),
    ("three gigahertz", "3 GHz"),
    ("five kilowatt hours", "5 kWh"),
    ("twenty kilowatt-hours", "20 kWh"),
    ("twenty five degrees celsius", "25 °C"),
    ("minus five degrees celsius", "-5 °C"),
    ("it is five meters away", "it is 5 m away"),
    # negatives: no number before the unit, unknown unit, ambiguous singular after a word number
    ("meters away", "meters away"),
    ("the kilometers we drove", "the kilometers we drove"),
    ("two hundred parsecs", "200 parsecs"),
    ("wait one second", "wait one second"),
    ("one foot in the door", "one foot in the door"),
    ("ten percent", "10%"),
    ("five pounds", "£5"),
    ("two hundred metersticks", "200 metersticks"),
]


@pytest.mark.parametrize("src,dst", CASES)
def test_unit_symbols(units, src, dst):
    assert units.normalize(src) == dst


@pytest.mark.parametrize("src", [s for s, _ in CASES])
def test_default_unchanged(plain, units, src):
    # The option is a pure post-step: switching it off gives the plain ITN output.
    out = plain.normalize(src)
    assert apply_unit_symbols(out) == units.normalize(src)
    assert InverseNormalizer(lang="en").normalize("two hundred meters") == "200 meters"


def test_details_and_generic_api(units):
    result = units.normalize_with_details("two hundred meters")
    assert result.text == "200 m" and result.changed
    assert Normalizer(mode="itn", lang="en", unit_symbols=True).normalize("one meter") == "1 m"
    assert units.normalize_batch(["two meters", "meters"]) == ["2 m", "meters"]


def test_no_pynini_in_unit_path():
    import damga.en.itn.units as module
    src = pathlib.Path(module.__file__).read_text(encoding="utf-8")
    imported = {a.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"__future__", "re"}
