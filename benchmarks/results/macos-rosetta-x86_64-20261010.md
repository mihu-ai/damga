# Damga benchmark (2026-10-10 15:10)

| key | value |
|---|---|
| platform | macOS-15.6-x86_64-i386-64bit |
| machine | x86_64 |
| python | 3.11.17 |
| pynini | 2.1.7 |
| damga | 0.1.0 |
| cpu_count | 8 |

## Initialization (compile vs load)

| metric | value |
|---|---|
| itn_cold_compile_s | 6.425 |
| itn_warm_far_load_s | 0.026 |
| itn_far_size_mb | 5.306 |
| tn_cold_compile_s | 2.744 |
| tn_far_size_mb | 14.000 |
| rss_after_init_mb | 488.973 |

## Per-utterance latency (ms) and throughput

| set | p50 | p95 | p99 | mean | utt/s |
|---|---|---|---|---|---|
| itn_short | 1.109 | 1.721 | 1.777 | 1.075 | 930 |
| itn_medium | 4.877 | 5.108 | 5.495 | 4.744 | 211 |
| itn_long_200w | 86.126 | 90.690 | 111.025 | 87.210 | 11 |
| tn_sentence | 2.073 | 2.153 | 2.218 | 2.086 | 479 |

Batch: 213 utt/s (1000 medium utterances in 4.70 s)
Streaming update latency: p50 1.236 ms, p95 4.928 ms, p99 7.606 ms (440 updates)
Peak RSS: 648 MB

Method: single process, single thread, inputs cycled from fixed Turkish lists (see benchmarks/bench.py); latency is wall-clock per normalize() call after warm-up through the cache; compile time is measured with an empty cache dir.

```json
{
 "env": {
  "platform": "macOS-15.6-x86_64-i386-64bit",
  "machine": "x86_64",
  "python": "3.11.17",
  "pynini": "2.1.7",
  "damga": "0.1.0",
  "cpu_count": 8
 },
 "init": {
  "itn_cold_compile_s": 6.424706291989423,
  "itn_warm_far_load_s": 0.025721417012391612,
  "itn_far_size_mb": 5.305565,
  "tn_cold_compile_s": 2.7444491669884883,
  "tn_far_size_mb": 14.000229,
  "rss_after_init_mb": 488.97265625
 },
 "itn_short": {
  "p50_ms": 1.1092500062659383,
  "p95_ms": 1.7212919774465263,
  "p99_ms": 1.7765840166248381,
  "mean_ms": 1.0754597029008437,
  "utt_per_s": 929.6718362996974
 },
 "itn_medium": {
  "p50_ms": 4.87674999749288,
  "p95_ms": 5.108208017190918,
  "p99_ms": 5.495124991284683,
  "mean_ms": 4.74401453032624,
  "utt_per_s": 210.78215631488297
 },
 "itn_long_200w": {
  "p50_ms": 86.12616700702347,
  "p95_ms": 90.68979200674221,
  "p99_ms": 111.02533401572146,
  "mean_ms": 87.2100956000213,
  "utt_per_s": 11.466437728625824
 },
 "tn_sentence": {
  "p50_ms": 2.0725840004161,
  "p95_ms": 2.152957982616499,
  "p99_ms": 2.21800000872463,
  "mean_ms": 2.0863722353678895,
  "utt_per_s": 479.2515959163173
 },
 "batch": {
  "utterances": 1000,
  "seconds": 4.7019030840019695,
  "utt_per_s": 212.67984093556896
 },
 "streaming_update": {
  "p50_ms": 1.2362090055830777,
  "p95_ms": 4.927874979330227,
  "p99_ms": 7.606000028317794,
  "updates": 440
 },
 "memory_peak_rss_mb": 648.265625
}
```
