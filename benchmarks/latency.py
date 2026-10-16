"""Quick latency check on the shipped (native) runtime; no pynini needed.

    python benchmarks/latency.py            # default sentences
    python benchmarks/latency.py --iters 200 --file my_sentences.txt

Reports import + grammar load time, per-sentence p50/p95/max over real recognizer-style sentences, and the
per-update cost of the streaming normalizer.  benchmarks/bench.py is the full report (compile times, FAR
cache, TN) and needs pynini.
"""
from __future__ import annotations

import argparse
import pathlib
import statistics
import sys
import time

SENTENCES = [
    "Merhaba.",
    "Deniz, et ahmet nokta com.",
    "1849 Taksim 4, No7, daire beş, Beşiktaş, Fransa.",
    "On beş yirmi beş, seksen beş doksan beş, 75.85.",
    "9, 9, 7, 7, 8, 8, 6, 6, 5, 5, 4, 4, 7, yedi yirmi yedi bin doksan bir.",
    "Yarın saat on dört otuzdaki diş randevumu 16'ya alabilir miyiz?",
    "Hayır, e-posta adresim deniz et gmail nokta com, telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş "
    "altmış yedi. Toplam tutar iki bin beş yüz lira kırk kuruş.",
]


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=100, help="repetitions per sentence")
    ap.add_argument("--file", help="one sentence per line instead of the built-in list")
    ap.add_argument("--mode", choices=["itn", "tn"], default="itn")
    args = ap.parse_args()
    sentences = SENTENCES
    if args.file:
        sentences = [line.strip() for line in pathlib.Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip()]

    t0 = time.perf_counter()
    from damga import Normalizer
    from damga.streaming import StreamingNormalizer
    t1 = time.perf_counter()
    norm = Normalizer(mode=args.mode)
    t2 = time.perf_counter()
    print(f"import {1000 * (t1 - t0):.0f} ms | grammar load {1000 * (t2 - t1):.0f} ms | backend {norm._impl.engine.backend}")
    for s in sentences:
        norm.normalize(s)

    print(f"\n{'words':>5} {'p50 ms':>7} {'p95 ms':>7} {'max ms':>7}  sentence")
    all_lat: list[float] = []
    for s in sentences:
        lat = []
        for _ in range(args.iters):
            a = time.perf_counter()
            norm.normalize(s)
            lat.append((time.perf_counter() - a) * 1000)
        all_lat += lat
        print(f"{len(s.split()):>5} {statistics.median(lat):>7.2f} {pct(lat, 95):>7.2f} {max(lat):>7.2f}  {s[:60]}")
    print(f"\nall sentences: p50 {statistics.median(all_lat):.2f} ms, p95 {pct(all_lat, 95):.2f} ms, "
          f"{len(all_lat) / (sum(all_lat) / 1000):.0f} utt/s")

    if args.mode == "itn":
        sn = StreamingNormalizer(mode="itn")
        words = max(sentences, key=lambda s: len(s.split())).split()
        lat = []
        for _ in range(max(5, args.iters // 10)):
            sn.reset()
            for i in range(1, len(words) + 1):
                a = time.perf_counter()
                sn.update(" ".join(words[:i]), is_final=(i == len(words)))
                lat.append((time.perf_counter() - a) * 1000)
        print(f"streaming update ({len(words)}-word utterance): p50 {pct(lat, 50):.2f} ms, p95 {pct(lat, 95):.2f} ms, "
              f"max {max(lat):.2f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
