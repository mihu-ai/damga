"""Russian ITN ``ordinal_digits``: ordinals below ten written with digits and the short ending (наращение)."""
from __future__ import annotations

import pytest

import damga
from damga.ru.itn.normalizer import InverseNormalizer


@pytest.fixture(scope="module")
def on():
    return InverseNormalizer(ordinal_digits=True)


@pytest.fixture(scope="module")
def off():
    return InverseNormalizer()


CASES = [
    # masculine
    ("первый", "1-й"),
    ("шестой", "6-й"),
    ("восьмого", "8-го"),
    ("сотому", "100-му"),
    ("третьим", "3-м"),
    ("втором", "2-м"),
    ("четвертому", "4-му"),
    # feminine
    ("первая", "1-я"),
    ("третья глава", "3-я глава"),
    ("первую", "1-ю"),
    ("во второй части", "во 2-й части"),
    # neuter
    ("первое", "1-е"),
    ("седьмое небо", "7-е небо"),
    ("пятого числа", "5-го числа"),
    # plural
    ("третьих", "3-х"),
    ("пятых", "5-х"),
    ("вторые сутки", "2-е сутки"),
    ("первыми", "1-ми"),
    ("девятым", "9-м"),
    # ё, capitals, context
    ("Четвёртого числа", "4-го числа"),
    ("на пятом этаже", "на 5-м этаже"),
    ("он пришел первым", "он пришел 1-м"),
    # compounds and ten-up (already digits by default)
    ("двадцать первого", "21-го"),
    ("двести первом", "201-м"),
    ("одиннадцатый", "11-й"),
    ("в тысяча девятьсот тридцатых годах", "в 1930-х годах"),
    # dates and centuries unchanged
    ("пятнадцатого октября", "15 октября"),
    ("восьмого марта", "8 марта"),
    ("третьего мая две тысячи двадцатого года", "3 мая 2020 года"),
    ("в двадцать первом веке", "в XXI веке"),
    # fraction denominators stay words
    ("две третьих", "две третьих"),
    ("одна вторая", "одна вторая"),
    ("три пятых", "3 пятых"),
]


@pytest.mark.parametrize(("spoken", "written"), CASES)
def test_ordinal_digits(on, spoken, written):
    assert on.normalize(spoken) == written


@pytest.mark.parametrize("spoken", ["восьмого", "третьих", "первая", "на пятом этаже", "второе место", "первыми"])
def test_default_unchanged(off, spoken):
    assert off.normalize(spoken) == spoken


def test_details_and_api_passthrough():
    n = damga.Normalizer(mode="itn", lang="ru", ordinal_digits=True)
    assert n.normalize("шестой урок") == "6-й урок"
    result = InverseNormalizer(ordinal_digits=True).normalize_with_details("второй")
    assert result.text == "2-й" and result.changed


def test_strict_disables():
    pytest.importorskip("pynini")                 # strict is a non-default grammar configuration
    assert InverseNormalizer(strict=True, ordinal_digits=True, backend="pynini").normalize("восьмого") == "восьмого"
