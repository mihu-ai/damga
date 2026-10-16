# TN variants, end to end: 2 × 1000 recordings

Date: 2026-10-12.  Script: `benchmarks/tn_variants.py`.

## Method

1. `tn_variants.py make` writes 1000 sentences with times, amounts, decimals, phone numbers, mixed sentences
   and control sentences with nothing ambiguous.  For each, the reading to speak is drawn **uniformly** from
   `normalize_variants()`, so about half of the recordings use a non-default reading.
2. That reading is spoken by a Turkish TTS voice (one voice, CPU).
3. Mihu Turkish STT (on-prem, CPU) transcribes the audio.  It writes many numbers as digits
   (`16-45`, `730'da`, `532812.43-76`); word error rate against the spoken reading is 39%.
4. `tn_variants.py score`: `normalize_matching(text, transcript)` must return the spoken reading.

Columns: *Damga picks the spoken reading* = TN with `variants=True` and the recognizer;
*default only* = the default reading on the same audio; *truth ≠ default: found* = among recordings spoken in a
non-default reading, how many were recovered; *perfect transcript* = the same with the spoken text itself as the
transcript (checks that every reading can be told apart).

The selection was developed on set 1 (seed 7).  Set 2 (seed 2026) was generated, spoken and transcribed
afterwards and not looked at before scoring: it is the number to quote.

## Set 2 — held out (seed 2026)

| category | n | ambiguous | Damga picks the spoken reading | default only | truth ≠ default: found | perfect transcript |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| time | 245 | 179 | 97.1% | 60.4% | 92.8% | 100.0% |
| money | 221 | 221 | 96.8% | 51.1% | 94.4% | 100.0% |
| decimal | 115 | 115 | 98.3% | 40.9% | 97.1% | 100.0% |
| telephone | 174 | 174 | 78.2% | 36.2% | 67.6% | 100.0% |
| mixed | 156 | 156 | 84.6% | 23.1% | 80.8% | 100.0% |
| control | 89 | 0 | 100.0% | 100.0% | – | 100.0% |
| **all** | 1000 | 845 | 92.2% | 49.6% | 85.3% | 100.0% |

Recognizer word error rate against the spoken reading: 39.0%

## Set 1 — development (seed 7)

| category | n | ambiguous | Damga picks the spoken reading | default only | truth ≠ default: found | perfect transcript |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| time | 260 | 192 | 95.0% | 58.8% | 88.8% | 100.0% |
| money | 218 | 218 | 96.3% | 55.5% | 92.8% | 100.0% |
| decimal | 104 | 104 | 97.1% | 55.8% | 93.5% | 100.0% |
| telephone | 172 | 172 | 76.2% | 32.0% | 65.0% | 100.0% |
| mixed | 168 | 168 | 83.3% | 22.6% | 80.8% | 100.0% |
| control | 78 | 0 | 100.0% | 100.0% | – | 100.0% |
| **all** | 1000 | 854 | 90.7% | 50.3% | 82.3% | 100.0% |

Recognizer word error rate against the spoken reading: 39.0%

## What the misses are (set 2, first ones)

Mostly phone numbers spoken digit by digit and transcribed as digits: `05.28915` carries no trace of how the
digits were grouped, so the default (grouped) reading is kept.  The rest are recognizer errors that remove the
distinguishing word (`43,5 lt` heard as `43 litre`, `Türk lirası` heard as `tırası`).

- `00:55'te sizi 0216 477 56 69 numarasından arayacağız.`
  - spoken: sıfır elli beşte sizi sıfır iki bir altı dört yedi yedi beş altı altı dokuz numarasından arayacağız.
  - heard: sıfır 55'te sizi sıfır 2647 75.69 numarasından arayacağız.
  - chosen: sıfır elli beşte sizi sıfır iki yüz on altı dört yüz yetmiş yedi elli altı altmış dokuz numarasından arayacağız.
- `Bizi 0216 580 79 42 numarasından arayabilirsiniz.`
  - spoken: Bizi sıfır iki bir altı beş sekiz sıfır yedi dokuz dört iki numarasından arayabilirsiniz.
  - heard: Bizi sıfır iki ve 65-87942. Numarasından arayabilirsiniz.
  - chosen: Bizi sıfır iki yüz on altı beş yüz seksen yetmiş dokuz kırk iki numarasından arayabilirsiniz.
- `Borcunuz 8.300,75 TL.`
  - spoken: Borcunuz sekiz bin üç yüz Türk lirası yetmiş beş kuruş.
  - heard: Borcunuz 830 lirası 75 kuruş.
  - chosen: Borcunuz sekiz bin üç yüz lira yetmiş beş kuruş.
- `11:15'te sizi 0542 809 72 69 numarasından arayacağız.`
  - spoken: on bir on beşte sizi sıfır beş dört iki sekiz sıfır dokuz yedi iki altı dokuz numarasından arayacağız.
  - heard: 11-15'te sizi 05-4-2809.7-2-69 numarasından arayacağız.
  - chosen: on bir on beşte sizi sıfır beş yüz kırk iki sekiz yüz dokuz yetmiş iki altmış dokuz numarasından arayacağız.
- `Numaram 0505 223 89 15.`
  - spoken: Numaram sıfır beş sıfır beş iki iki üç sekiz dokuz bir beş.
  - heard: Numaram 05.28915.
  - chosen: Numaram sıfır beş yüz beş iki yüz yirmi üç seksen dokuz on beş.
- `Numaram 0555 423 87 37.`
  - spoken: Numaram sıfır beş beş beş dört iki üç sekiz yedi üç yedi.
  - heard: Numaram 05.54-238737.
  - chosen: Numaram sıfır beş yüz elli beş dört yüz yirmi üç seksen yedi otuz yedi.
- `Numaram 0532 646 37 99.`
  - spoken: Numaram sıfır beş üç iki altı dört altı üç yedi dokuz dokuz.
  - heard: Numaram 05.264, 679
  - chosen: Numaram sıfır beş yüz otuz iki altı yüz kırk altı otuz yedi doksan dokuz.

## Limits

One synthetic voice; real speakers vary more.  Reproduce with any TTS and recognizer: speak the `truth` field of
`make`'s output and give `score` a JSONL of `{"id", "heard"}`.
