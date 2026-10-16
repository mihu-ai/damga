from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import resource
import statistics
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SHORT = ["yirmi beş bin", "saat dokuz otuz", "yüzde on iki virgül beş", "on beş ekim iki bin yirmi altı"]
MEDIUM = ["telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi, e-posta adresim derya nokta öztürk et gmail nokta com",
          "toplam tutar iki bin beş yüz lira kırk kuruş, indirim yüzde on iki virgül beş, teslimat on beş ekimde"]
LONG = [" ".join(MEDIUM * 8)]
TN_INPUTS = ["Toplam 25.600 adet, %12,5 indirim, 2,50 TL, 15.10.2026 saat 09:30, 0532 123 45 67."]

def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]

def rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024

def time_calls(fn, inputs, iters):
    lat = []
    t0 = time.perf_counter()
    for i in range(iters):
        s = inputs[i % len(inputs)]
        a = time.perf_counter(); fn(s); lat.append((time.perf_counter() - a) * 1000)
    total = time.perf_counter() - t0
    return {"p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95), "p99_ms": pct(lat, 99), "mean_ms": statistics.mean(lat),
            "utt_per_s": iters / total}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=2000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    import pynini

    from damga import InverseNormalizer, TextNormalizer, __version__
    from damga.streaming import StreamingNormalizer

    rep: dict = {"env": {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(),
                         "pynini": pynini.__version__, "damga": __version__, "cpu_count": os.cpu_count()}}
    cache = pathlib.Path(tempfile.mkdtemp())
    m0 = rss_mb()
    t = time.perf_counter(); itn = InverseNormalizer(cache_dir=cache, use_cache=True); cold = time.perf_counter() - t
    t = time.perf_counter(); itn2 = InverseNormalizer(cache_dir=cache, use_cache=True); warm = time.perf_counter() - t
    assert itn2.engine.loaded_from_cache
    far_mb = itn.engine.far_file.stat().st_size / 1e6
    t = time.perf_counter(); tn = TextNormalizer(cache_dir=cache, use_cache=True); tn_cold = time.perf_counter() - t
    rep["init"] = {"itn_cold_compile_s": cold, "itn_warm_far_load_s": warm, "itn_far_size_mb": far_mb, "tn_cold_compile_s": tn_cold,
                   "tn_far_size_mb": tn.engine.far_file.stat().st_size / 1e6, "rss_after_init_mb": rss_mb() - m0}
    rep["itn_short"] = time_calls(itn.normalize, SHORT, args.iters)
    rep["itn_medium"] = time_calls(itn.normalize, MEDIUM, args.iters)
    rep["itn_long_200w"] = time_calls(itn.normalize, LONG, max(200, args.iters // 10))
    rep["tn_sentence"] = time_calls(tn.normalize, TN_INPUTS, args.iters)
    t = time.perf_counter(); itn.normalize_batch(MEDIUM * 500); bt = time.perf_counter() - t
    rep["batch"] = {"utterances": 1000, "seconds": bt, "utt_per_s": 1000 / bt}
    sn = StreamingNormalizer(mode="itn", cache_dir=cache)
    words = MEDIUM[0].split(); lat = []
    for _ in range(max(20, args.iters // 100)):
        sn.reset()
        for i in range(1, len(words) + 1):
            a = time.perf_counter(); sn.update(" ".join(words[:i]), is_final=(i == len(words))); lat.append((time.perf_counter() - a) * 1000)
    rep["streaming_update"] = {"p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95), "p99_ms": pct(lat, 99), "updates": len(lat)}
    rep["memory_peak_rss_mb"] = rss_mb()

    lines = [f"# Damga benchmark ({time.strftime('%Y-%m-%d %H:%M')})", "", "| key | value |", "|---|---|"]
    for k, v in rep["env"].items():
        lines.append(f"| {k} | {v} |")
    lines += ["", "## Initialization (compile vs load)", "", "| metric | value |", "|---|---|"]
    for k, v in rep["init"].items():
        lines.append(f"| {k} | {v:.3f} |")
    lines += ["", "## Per-utterance latency (ms) and throughput", "", "| set | p50 | p95 | p99 | mean | utt/s |", "|---|---|---|---|---|---|"]
    for k in ("itn_short", "itn_medium", "itn_long_200w", "tn_sentence"):
        r = rep[k]; lines.append(f"| {k} | {r['p50_ms']:.3f} | {r['p95_ms']:.3f} | {r['p99_ms']:.3f} | {r['mean_ms']:.3f} | {r['utt_per_s']:.0f} |")
    r = rep["streaming_update"]
    lines += ["", f"Batch: {rep['batch']['utt_per_s']:.0f} utt/s (1000 medium utterances in {rep['batch']['seconds']:.2f} s)",
              f"Streaming update latency: p50 {r['p50_ms']:.3f} ms, p95 {r['p95_ms']:.3f} ms, p99 {r['p99_ms']:.3f} ms ({r['updates']} updates)",
              f"Peak RSS: {rep['memory_peak_rss_mb']:.0f} MB", "",
              "Method: single process, single thread, inputs cycled from fixed Turkish lists (see benchmarks/bench.py); "
              "latency is wall-clock per normalize() call after warm-up through the cache; compile time is measured with an empty cache dir."]
    md = "\n".join(lines)
    print(md)
    if args.out:
        p = pathlib.Path(args.out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(md + "\n\n```json\n" + json.dumps(rep, indent=1) + "\n```\n")

if __name__ == "__main__":
    main()
