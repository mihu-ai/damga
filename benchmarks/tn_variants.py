"""End-to-end test of TN with variants: does normalize_matching() find the reading a speaker used?

    python benchmarks/tn_variants.py make  --n 1000 --out set.jsonl     # written sentences + the reading to speak
    # speak every "truth" with any TTS, transcribe with any recognizer, write {"id", "heard"} lines to heard.jsonl
    python benchmarks/tn_variants.py score --set set.jsonl --heard heard.jsonl [--report report.md]

make: sentences with times, amounts, decimals and phone numbers (plus control sentences with nothing ambiguous).
For each one the reading to speak ("truth") is drawn uniformly from normalize_variants(), so the default is the
truth only about as often as any other reading.  score: normalize_matching(text, heard) must return the truth.
The "default only" column is what the default TN would score on the same audio.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys

from damga import TextNormalizer
from damga.core.variants import _edit_distance, _words

BACK, HARD = set("aıou"), set("çfhkpsşt")


def _last_vowel(word: str) -> str:
    return next((c for c in reversed(word) if c in "aeıioöuü"), "e")


def loc(word: str) -> str:
    """Written locative after a number read as ``word``: 09:30'da, 09:15'te."""
    return ("t" if word[-1] in HARD else "d") + ("a" if _last_vowel(word) in BACK else "e")


def dat(word: str) -> str:
    """Written dative: 09:30'a, 10:05'e, 06:00'ya."""
    return ("y" if word[-1] in "aeıioöuü" else "") + ("a" if _last_vowel(word) in BACK else "e")


def make(n: int, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    tn = TextNormalizer()
    tnv = TextNormalizer(variants=True)

    def clock() -> str:
        return f"{rnd.randint(0, 23):02d}:{rnd.choice([0, 5, 10, 15, 20, 25, 30, 30, 35, 40, 45, 45, 50, 55]):02d}"

    def suffixed(t: str, kind) -> str:
        return f"{t}'{kind(tn.normalize(t).split()[-1])}"

    def amount() -> str:
        return f"{rnd.choice([rnd.randint(1, 99), rnd.randint(100, 999), rnd.randint(1, 99) * 100]):,}".replace(",", ".")

    def phone() -> str:
        return f"0{rnd.choice(['532', '505', '542', '555', '212', '216', '850'])} {rnd.randint(100, 999)} {rnd.randint(10, 99)} {rnd.randint(10, 99)}"

    templates = {
        "time": [
            lambda: f"Randevunuz saat {clock()}.",
            lambda: f"Toplantı {suffixed(clock(), loc)} başlıyor.",
            lambda: f"Servis {suffixed(clock(), dat)} kadar açık.",
            lambda: f"Aracınızı saat {clock()} gibi teslim alabilirsiniz.",
        ],
        "money": [
            lambda: f"Toplam {amount()} TL tutuyor.",
            lambda: f"Borcunuz {amount()},{rnd.choice(['50', '50', '25', '75', '40'])} TL.",
            lambda: f"Kampanyalı fiyat {amount()} TL olarak güncellendi.",
        ],
        "decimal": [
            lambda: f"{rnd.randint(0, 9)},5 kg un aldım.",
            lambda: f"Fiyatlar %{rnd.randint(1, 40)},5 arttı.",
            lambda: f"Depoya {rnd.randint(0, 60)},5 lt yakıt koyduk.",
            lambda: f"Mesafe {rnd.randint(1, 300)},5 km.",
        ],
        "telephone": [
            lambda: f"Numaram {phone()}.",
            lambda: f"Bizi {phone()} numarasından arayabilirsiniz.",
        ],
        "mixed": [
            lambda: f"Saat {clock()} randevusu için ödeme {amount()} TL.",
            lambda: f"{suffixed(clock(), loc)} sizi {phone()} numarasından arayacağız.",
        ],
        "control": [
            lambda: f"Teslim tarihi {rnd.randint(1, 28)}.{rnd.randint(1, 12)}.2026 olarak belirlendi.",
            lambda: f"Stokta {rnd.randint(2, 900)} adet ürün var.",
            lambda: f"Aracınız {rnd.randint(2, 9)}. sırada bekliyor.",
        ],
    }
    weights = {"time": 0.25, "money": 0.2, "decimal": 0.15, "telephone": 0.15, "mixed": 0.15, "control": 0.1}
    rows, seen = [], set()
    while len(rows) < n:
        cat = rnd.choices(list(weights), list(weights.values()))[0]
        text = rnd.choice(templates[cat])()
        if text in seen:
            continue
        seen.add(text)
        variants = tnv.normalize_variants(text, n=50)
        truth = rnd.choice(variants)
        rows.append({"id": f"v{len(rows):04d}", "category": cat, "text": text, "variants": variants,
                     "default": variants[0], "truth": truth})
    return rows


def score(rows: list[dict], heard: dict[str, str]) -> str:
    tnv = TextNormalizer(variants=True)
    by = collections.defaultdict(lambda: collections.Counter())
    errors, wer_e, wer_n = [], 0, 0
    for r in rows:
        if r["id"] not in heard:
            continue
        h = heard[r["id"]]
        chosen = tnv.normalize_matching(r["text"], h)
        ok, base, oracle = chosen == r["truth"], r["default"] == r["truth"], tnv.normalize_matching(r["text"], r["truth"]) == r["truth"]
        for key in (r["category"], "all"):
            c = by[key]
            c["n"] += 1
            c["ok"] += ok
            c["base"] += base
            c["oracle"] += oracle
            c["ambiguous"] += len(r["variants"]) > 1
            c["nondefault"] += not base
            c["nondefault_ok"] += ok and not base
        t = _words(tnv.normalize(h))
        wer_e += _edit_distance(t, _words(r["truth"]))
        wer_n += len(_words(r["truth"]))
        if not ok:
            errors.append((r, h, chosen))
    lines = ["| category | n | ambiguous | Damga picks the spoken reading | default only | truth ≠ default: found | perfect transcript |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key in ["time", "money", "decimal", "telephone", "mixed", "control", "all"]:
        c = by.get(key)
        if not c:
            continue
        pct = lambda a, b: f"{100 * a / b:.1f}%" if b else "–"  # noqa: E731
        lines.append(f"| {'**all**' if key == 'all' else key} | {c['n']} | {c['ambiguous']} | {pct(c['ok'], c['n'])} | "
                     f"{pct(c['base'], c['n'])} | {pct(c['nondefault_ok'], c['nondefault'])} | {pct(c['oracle'], c['n'])} |")
    lines.append(f"\nRecognizer word error rate against the spoken reading: {100 * wer_e / max(wer_n, 1):.1f}%\n")
    lines.append(f"Misses ({len(errors)}):\n")
    for r, h, chosen in errors[:40]:
        lines.append(f"- `{r['text']}`\n  - spoken: {r['truth']}\n  - heard: {h}\n  - chosen: {chosen}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--n", type=int, default=1000)
    m.add_argument("--seed", type=int, default=7)
    m.add_argument("--out", required=True)
    s = sub.add_parser("score")
    s.add_argument("--set", required=True)
    s.add_argument("--heard", required=True)
    s.add_argument("--report")
    a = ap.parse_args()
    if a.cmd == "make":
        rows = make(a.n, a.seed)
        with open(a.out, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        amb = sum(len(r["variants"]) > 1 for r in rows)
        nd = sum(r["truth"] != r["default"] for r in rows)
        print(f"{len(rows)} sentences, {amb} with more than one reading, {nd} to be spoken in a non-default reading → {a.out}")
    else:
        rows = [json.loads(line) for line in open(a.set, encoding="utf-8")]
        heard = {}
        for line in open(a.heard, encoding="utf-8"):
            d = json.loads(line)
            heard[d["id"]] = d["heard"]
        report = score(rows, heard)
        print(report)
        if a.report:
            with open(a.report, "w", encoding="utf-8") as f:
                f.write(report + "\n")


if __name__ == "__main__":
    sys.exit(main())
