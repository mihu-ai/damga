"""The Spanish unit and currency tables, read without pynini (the normalizer needs the units' gender and the
currency symbols at run time)."""
from __future__ import annotations

import pathlib

DATA = pathlib.Path(__file__).resolve().parent / "data" / "units.tsv"


def load_units() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            written, sg, pl, gender = line.split("\t")
            rows.append((written, sg, pl, gender))
    return rows


# (symbols and codes) → singular, plural, feminine, plural of the minor unit (None: amounts with decimals are read as
# decimals, "12,05 ¥" → "doce coma cero cinco yenes").  "$" is the dollar; the peso has its own codes.
CURRENCIES: list[tuple[tuple[str, ...], str, str, bool, str | None]] = [
    (("€", "EUR", "eur"), "euro", "euros", False, "céntimos"),
    (("$", "USD", "usd", "US$", "us$", "U$S"), "dólar", "dólares", False, "centavos"),
    (("£", "GBP", "gbp"), "libra", "libras", True, "peniques"),
    (("¥", "JPY", "jpy"), "yen", "yenes", False, None),
    (("CHF", "chf"), "franco suizo", "francos suizos", False, "céntimos"),
    (("₩", "KRW", "krw"), "won", "wones", False, None),
    (("₧", "pta", "ptas", "Pta", "Ptas"), "peseta", "pesetas", True, None),
    (("MXN", "mxn", "MX$", "Mex$", "mex$"), "peso mexicano", "pesos mexicanos", False, "centavos"),
    (("ARS", "ars"), "peso argentino", "pesos argentinos", False, "centavos"),
    (("COP", "cop"), "peso colombiano", "pesos colombianos", False, "centavos"),
    (("CLP", "clp"), "peso chileno", "pesos chilenos", False, "centavos"),
    (("UYU", "uyu"), "peso uruguayo", "pesos uruguayos", False, "centésimos"),
    (("DOP", "dop"), "peso dominicano", "pesos dominicanos", False, "centavos"),
    (("PEN", "S/"), "sol", "soles", False, "céntimos"),
    (("BRL", "brl", "R$"), "real", "reales", False, "centavos"),
    (("₹", "INR", "inr", "Rs", "Rs.", "rs"), "rupia", "rupias", True, None),
    (("₽", "RUB", "rub"), "rublo", "rublos", False, None),
    (("CNY", "cny"), "yuan", "yuanes", False, None),
    (("₡", "CRC", "crc"), "colón", "colones", False, "céntimos"),
    (("GTQ", "gtq"), "quetzal", "quetzales", False, "centavos"),
    (("HNL", "hnl"), "lempira", "lempiras", False, "centavos"),
    (("NIO", "nio"), "córdoba", "córdobas", False, "centavos"),
    (("PAB", "pab"), "balboa", "balboas", False, "centésimos"),
    (("₲", "PYG", "pyg"), "guaraní", "guaraníes", False, None),
    (("BOB",), "boliviano", "bolivianos", False, "centavos"),
    (("VES",), "bolívar", "bolívares", False, "céntimos"),
    (("SEK", "sek"), "corona sueca", "coronas suecas", True, None),
    (("NOK", "nok"), "corona noruega", "coronas noruegas", True, None),
    (("DKK", "dkk"), "corona danesa", "coronas danesas", True, None),
    (("kr",), "corona", "coronas", True, None),
    (("HKD", "hkd", "HK$"), "dólar de Hong Kong", "dólares de Hong Kong", False, "centavos"),
    (("CAD", "cad", "CA$"), "dólar canadiense", "dólares canadienses", False, "centavos"),
    (("AUD", "aud", "A$"), "dólar australiano", "dólares australianos", False, "centavos"),
]
CURRENCY_SYMBOLS = sorted({s for symbols, *_ in CURRENCIES for s in symbols}, key=len, reverse=True)
# read only after the amount: "COP 26" is the climate conference
AFTER_ONLY = {"COP", "cop"}
