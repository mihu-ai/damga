"""Opt-in unit symbols for English ITN output (``InverseNormalizer(unit_symbols=True)``).

A deterministic pass over the finished ITN text, so it needs no grammar compilation (and no pynini): a number
written by ITN followed by a spelled unit becomes the number and the unit symbol, ``200 meters`` → ``200 m``,
``120 kilometers per hour`` → ``120 km/h``. A unit word not preceded by a number is left alone (``meters away``).
ITN keeps lone numbers below ten as words, so ``one`` … ``nine`` directly before a unit are written as digits too
(``one meter`` → ``1 m``), except before units that are common in other senses (``one second``, ``one foot``).
"""
from __future__ import annotations

import re

_SMALL = {w: str(i) for i, w in enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
                                           "nine"))}

# symbol: spoken forms (singular and plural, US and UK spellings).
_LENGTH = {
    "mm": ("millimeter", "millimeters", "millimetre", "millimetres"),
    "cm": ("centimeter", "centimeters", "centimetre", "centimetres"),
    "m": ("meter", "meters", "metre", "metres"),
    "km": ("kilometer", "kilometers", "kilometre", "kilometres"),
    "in": ("inch", "inches"),
    "ft": ("foot", "feet"),
    "yd": ("yard", "yards"),
    "mi": ("mile", "miles"),
}
_UNITS: dict[str, tuple[str, ...]] = {
    **_LENGTH,
    "mg": ("milligram", "milligrams", "milligramme", "milligrammes"),
    "g": ("gram", "grams", "gramme", "grammes"),
    "kg": ("kilogram", "kilograms", "kilogramme", "kilogrammes", "kilo", "kilos"),
    "t": ("tonne", "tonnes", "metric ton", "metric tons"),
    "oz": ("ounce", "ounces"),
    "lb": ("pound", "pounds"),
    "ml": ("milliliter", "milliliters", "millilitre", "millilitres"),
    "l": ("liter", "liters", "litre", "litres"),
    "ms": ("millisecond", "milliseconds"),
    "s": ("second", "seconds"),
    "min": ("minute", "minutes"),
    "h": ("hour", "hours"),
    "km/h": tuple(f"{k} {p} hour" for k in _LENGTH["km"] for p in ("per", "an", "a")),
    "mph": tuple(f"{k} {p} hour" for k in _LENGTH["mi"] for p in ("per", "an", "a")),
    "m/s": tuple(f"{k} per second" for k in _LENGTH["m"]),
    "KB": ("kilobyte", "kilobytes"),
    "MB": ("megabyte", "megabytes"),
    "GB": ("gigabyte", "gigabytes"),
    "TB": ("terabyte", "terabytes"),
    "MB/s": ("megabytes per second", "megabyte per second"),
    "GB/s": ("gigabytes per second", "gigabyte per second"),
    "kbps": ("kilobits per second", "kilobit per second"),
    "Mbps": ("megabits per second", "megabit per second"),
    "Gbps": ("gigabits per second", "gigabit per second"),
    "Hz": ("hertz",),
    "kHz": ("kilohertz",),
    "MHz": ("megahertz",),
    "GHz": ("gigahertz",),
    "W": ("watt", "watts"),
    "kW": ("kilowatt", "kilowatts"),
    "MW": ("megawatt", "megawatts"),
    "kWh": tuple(f"kilowatt{s}{h}" for s in (" ", "-") for h in ("hour", "hours")),
    "V": ("volt", "volts"),
    "°C": ("degree celsius", "degrees celsius", "degree centigrade", "degrees centigrade"),
    "°F": ("degree fahrenheit", "degrees fahrenheit"),
}
for _sym in ("mm", "cm", "m", "km", "in", "ft", "yd", "mi"):
    _UNITS[_sym + "²"] = tuple(f"square {w}" for w in _LENGTH[_sym]) + tuple(f"{w} squared" for w in _LENGTH[_sym])
    _UNITS[_sym + "³"] = tuple(f"cubic {w}" for w in _LENGTH[_sym]) + tuple(f"{w} cubed" for w in _LENGTH[_sym])

# Spoken numbers below ten stay words in ITN output; before these units they usually do not count a measure
# ("wait one second", "one foot in the door", "one hour later"), so only digits trigger them.
_DIGITS_ONLY = {"second", "seconds", "minute", "minutes", "hour", "hours", "foot", "pound", "ounce"}

SYMBOLS: dict[str, str] = {form: sym for sym, forms in _UNITS.items() for form in forms}

_NUMBER = r"-?(?:\d[\d,]*(?:\.\d+)?|\.\d+)"
_PATTERN = re.compile(
    r"(?<![\w.,:/-])(" + _NUMBER + "|" + "|".join(_SMALL) + r") ("
    + "|".join(re.escape(f).replace(r"\ ", r"\s").replace(r"\-", r"[-\s]")
               for f in sorted(SYMBOLS, key=len, reverse=True))
    + r")(?![\w-])",
    re.IGNORECASE,
)


def _replace(m: re.Match) -> str:
    number, unit = m.group(1), re.sub(r"[-\s]+", " ", m.group(2).lower())
    if number.lower() in _SMALL:
        if unit in _DIGITS_ONLY:
            return m.group(0)
        number = _SMALL[number.lower()]
    return f"{number} {SYMBOLS[unit]}"


def apply_unit_symbols(text: str) -> str:
    """``200 meters`` → ``200 m`` in finished ITN output; everything else is left as it is."""
    return _PATTERN.sub(_replace, text)
