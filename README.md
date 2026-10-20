# Damga — Text Normalization (TN) & Inverse Text Normalization (ITN)

[Türkçe README](https://github.com/mihu-ai/damga/blob/main/README.tr.md)

**Damga** (`damga` on PyPI) is an open-source, offline, deterministic
text-normalization engine built on weighted finite-state transducers,
with Turkish as the default language
([languages](#languages)).  It turns what a speech recognizer *hears* into what people
*write* (ITN), and what a language model or a database *writes* into what a
TTS voice should *say* (TN):

| Direction | Input | Output |
|---|---|---|
| ITN (spoken → written) | `yirmi beş bin altı yüz` | `25.600` |
| ITN | `yüz elli türk lirası` | `150 TL` |
| ITN | `saat dokuz otuzda` | `saat 09:30'da` |
| ITN | `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi` | `0532 123 45 67` |
| ITN | `derya nokta öztürk et gmail nokta com` | `derya.ozturk@gmail.com` |
| ITN | `otuz dört a b c sekiz yüz kırk iki` | `34 ABC 842` |
| TN (written → spoken) | `25.600` | `yirmi beş bin altı yüz` |
| TN | `2,50 TL` | `iki lira elli kuruş` |
| TN | `15.10.2026 saat 09:30` | `on beş ekim iki bin yirmi altı saat dokuz otuz` |

Why a grammar engine and not a model:

* **Deterministic.** The same input always gives the same output; every
  behaviour is a line in a golden file you can read and change.
* **Safe on sensitive entities.** Phone numbers, IBANs and plates are never
  padded or "repaired": if the digit count is wrong the words stay words.
* **Fast and small.** Sub-millisecond per utterance on one CPU core, no GPU, no
  network, no LLM; the wheel installs with zero dependencies.
* **Built for real recognizers.** The grammars accept the mixed forms ASR
  systems actually emit: written digits inside spoken numbers, punctuation in
  the middle of a phone number, glued separators, mis-heard e-mail domains.
* **Two directions, one set of grammars.** TN number writing is the exact
  inverse of the ITN cardinal grammar, so the two directions can never disagree.

## Install

```bash
pip install damga                 # Linux, macOS, Windows — no other dependency
pip install "damga[build]"        # + pynini, only for writing or changing grammars
```

The wheel contains the precompiled grammars of all seven languages and a small native runtime
(`damga._fstrt`, OpenFst statically linked), so nothing is compiled on the
user's machine and pynini is not needed at run time.  Grammar authors install
the `build` extra (pynini has Linux wheels on PyPI; on macOS use
`conda install -c conda-forge pynini`) and run `python -m damga.build` after
editing a grammar.  With pynini present, `backend="pynini"` (or
`DAMGA_BACKEND=pynini`) runs the grammars live; custom category selections
automatically use it.

## Quick start: your microphone, on your machine

The fastest way to see Damga work is live speech.  Mihu Turkish STT runs on
your CPU (no GPU, no cloud, no API key), Damga turns what it hears into written
text while you speak:

```bash
git clone https://github.com/mihu-ai/damga && cd damga
pip install damga turkish-stt sounddevice     # Linux: sudo apt install libportaudio2 first
python examples/mic_streaming.py              # --list shows input devices, --device N picks one
```

Say *"telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi"*:

```
 … telefon numaram 0 5 32 123
[01] STT : telefon numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi
     ITN : telefon numaram 0532 123 45 67
```

The line updates while you talk; when you pause the final line is printed.
The recognizer model (about 70 MB) downloads once on the first run.  On macOS
allow microphone access for your terminal (System Settings → Privacy &
Security → Microphone).  More engines (Mihu STT cloud, ElevenLabs, Whisper,
Ollama): [`examples/`](https://github.com/mihu-ai/damga/blob/main/examples/README.md).

## Usage

```python
from damga import InverseNormalizer, TextNormalizer, Normalizer

itn = InverseNormalizer()
itn.normalize("yüz elli lira")                    # '150 TL'
itn.normalize_batch(["on beş ekim", "yüzde on"])  # ['15 Ekim', '%10']

tn = TextNormalizer()
tn.normalize("Toplam 25.600 adet, %12,5 indirim.")
# 'Toplam yirmi beş bin altı yüz adet, yüzde on iki virgül beş indirim.'

Normalizer(mode="itn").normalize("yirmi beş bin")   # '25.000'
```

Options (all keyword arguments, all optional):

| option | meaning |
|---|---|
| `categories=[...]` | enable a subset of `cardinal ordinal decimal money percent measure time date telephone iban plate email address spelling lexicon_entry` (needs pynini) |
| `strict=True` | conservative ITN: bare numbers stay words, only keyword/structure-driven classes fire (needs pynini) |
| `custom_vocab={"e te es tur": "ETS Tur"}` | your own spoken → written terms (take precedence) |
| `cache_dir=...` / `use_cache=False` | where compiled grammars (FAR) are stored (default `~/.cache/damga`, override with `DAMGA_CACHE_DIR`) |
| `group_thousands=False` | write `25600` instead of `25.600` |
| `group_four_digits=False` | ITN: no thousands dot in four-digit numbers (`2024 seçimleri`, `1500 kişi`); five digits and more keep it (needs pynini) |
| `scale_words=True` | ITN: round millions and up keep their scale word (`beş milyon` → `5 milyon`, `elli altı milyar` → `56 milyar`) instead of `5.000.000` (needs pynini) |
| `preserve_case=False` | lower-case everything instead of keeping the recognizer's casing on untouched words |
| `diagnostics=True` | `normalize_with_details()` keeps the intermediate record |
| `repair_spelling=True` | restore diacritic-less (`yuz elli`) and glued (`onbeş`) number words before the grammars run; `False` feeds the text as is |
| `backend="auto" \| "native" \| "pynini"` | runtime selection (see below) |
| `variants=True` | TN only: `normalize_variants()` also lists the other ways a form is read (see below) |

Writing-style options for the other languages (off by default; plain post-processing, so they work without pynini):

| language / mode | option | effect |
|---|---|---|
| `en` ITN | `unit_symbols=True` | units after a number as symbols: `two hundred kilometers per hour` → `200 km/h`, `twenty five square meters` → `25 m²`, `minus five degrees celsius` → `-5 °C` |
| `es` TN | `formal_ordinals=True` | ordinals 11–100 as ordinal words instead of the cardinal: `el 80.º aniversario` → *el octogésimo aniversario*, `la 11.ª edición` → *la undécima edición* |
| `ru` ITN | `ordinal_digits=True` | ordinals 1–9 as digits with the short ending: `восьмого` → `8-го`, `на пятом этаже` → `на 5-м этаже` (10 and up are digits already) |
| `de` ITN | `fraction_digits=True` | fractions with a slash: `drei viertel` → `3/4`, `zweieinhalb Stunden` → `2 1/2 Stunden`; `die Hälfte`, `ein Viertel der Stadt` stay words |

```python
from damga import InverseNormalizer
InverseNormalizer(lang="en", unit_symbols=True).normalize("two hundred kilometers per hour")   # "200 km/h"
```

### One reading (default) or variants

By default Damga gives **one reading**: one written form, one spoken form,
every time.  That is what a voice agent needs, and `normalize()` always works
this way: about 1 ms per sentence on one CPU core, the same reading in every
call.  Choosing a reading with a language model would add 0.3–2 s per sentence
before the TTS starts, so for voice AI keep the default.

Some forms are read in more than one way by Turkish speakers (`09:30` is
*dokuz otuz* or *dokuz buçuk*).  With `variants=True`, TN also lists those
readings, default first.  Use it to prepare **TTS or ASR training text** that
matches what a speaker actually said:

```python
tn = TextNormalizer(variants=True)
tn.normalize("Saat 09:30'da")             # 'Saat dokuz otuzda'  (unchanged)
tn.normalize_variants("Saat 09:30'da")    # ['Saat dokuz otuzda', 'Saat dokuz buçukta']
tn.normalize_variants("2,50 TL")          # ['iki lira elli kuruş', 'iki Türk lirası elli kuruş', 'iki buçuk lira']
tn.normalize_matching("Saat 09:30'da", heard="saat dokuz buçukta")   # 'Saat dokuz buçukta'
```

ITN has no variants: a phone number or an amount has one written form, and
guessing between several is exactly what ITN must not do.  In 1.0 the option
was called `deterministic` (`deterministic=False`); the old name still works
with a `DeprecationWarning`.  Details:
[docs/variants.md](https://github.com/mihu-ai/damga/blob/main/docs/variants.md).

### Streaming ITN for live ASR

```python
from damga.streaming import StreamingNormalizer

sn = StreamingNormalizer(mode="itn")
sn.update("yirmi beş", is_final=False).text              # '25'        (provisional)
sn.update("yirmi beş bin", is_final=False).text          # '25.000'    (still provisional — nothing committed)
sn.update("yirmi beş bin altı yüz", is_final=True).text  # '25.600'    (final, state reset)
```

`update()` always receives the **latest full hypothesis** of the current
utterance.  A prefix is committed only when it has been stable for
`stable_after` updates *and* does not end inside a span a grammar could still
extend, so a number is never frozen too early.  The final result is always the
batch normalization of the whole utterance.  See [docs/streaming.md](https://github.com/mihu-ai/damga/blob/main/docs/streaming.md).

## How it works: a token-based, two-pass WFST pipeline

Damga is a **token-based** normalizer.  Normalization is not one big
spoken → written rewrite; it is two transducers with a structured, inspectable
token string in between:

```
"toplam yirmi beş bin altı yüz lira kırk kuruş ödedim"
        │
        │  pass 1 — reader FST (union of all readers, weighted)
        ▼
word="toplam" money(integer="25600" fractional="40" currency="TL") word="ödedim"
        │
        │  pass 2 — writer FST (union of all writers)
        ▼
"toplam 25.600,40 TL ödedim"
```

* **Pass 1, reading.** Every semantic class (`cardinal`, `money`, `time`,
  `telephone`, `email`, …) is a small grammar that maps a spoken span to a
  token `class(field="value" …)`.  Words no class claims fall through to
  `word="…"`.  The sentence reader is the weighted union of all class readers; the best
  analysis is the **shortest path** through the lattice.  A semantic class costs
  about 1, the word fallback costs 100 per token, so any grammar that matches
  beats leaving the words alone, and among grammars the more specific one wins
  (`iban` < `email` < `telephone` < `money` < `cardinal`).
* **Pass 2, writing.** Each class has a writer that renders its
  token: `money` puts the currency symbol after the amount, `time` zero-pads
  and re-attaches the case suffix (`saat 09:30'da`), `telephone` groups digits
  the Turkish way.  Fields are emitted in a fixed order by the reader, so there
  is **no Python re-ordering stage** between the two passes: the whole pipeline
  is two compositions and two shortest-path searches.

Why token-based rather than a single "tokenless" transducer that rewrites
text directly?

| | token-based (Damga) | single-pass rewrite |
|---|---|---|
| adding a class | one reader + one writer, independent of the others | every new rule interacts with every existing rule in one grammar |
| precedence | one weight per class, in one table | encoded implicitly in rule order and context |
| debugging | `diagnostics=True` shows the record, so you see *what* was recognised before *how* it was written | only input and output |
| TN ↔ ITN | the same token protocol in both directions; TN number writers are the inverse of the ITN cardinal grammar | two unrelated grammars |
| formatting changes | change a writer, readers untouched (`100 $` vs `$100`, `25600` vs `25.600`) | touch the recognition rules |
| cost | two compositions per utterance | one |

The second composition is cheap (the writer has a few hundred states), so
the token layer costs well under a millisecond and buys composability, a
readable intermediate form and golden tests at the tag level.  The numbers
grammar is the foundation: fixed-width, zero-padded sub-graphs (two digits,
three digits, thousands, millions …) composed with a leading-zero stripper,
reused by every class that contains a number.  Ambiguity is resolved with path
weights, not code: a non-standard `bir yüz` carries a penalty, a telephone
group ending on a round word (`otuz`, `iki yüz`) is penalised so
`beş yüz otuz iki yüz yirmi üç` is read `532 | 123`.  Details in
[docs/architecture.md](https://github.com/mihu-ai/damga/blob/main/docs/architecture.md).

### Runtime

Grammars are written in Pynini and compiled once into two OpenFst files per
language and direction (`damga/<lang>/<mode>/compiled/`).  At run time the
native extension `damga._fstrt` (OpenFst statically linked, ~2 MB) loads them
and runs *input chain ∘ FST → shortest path* in C++; the GIL is released during
the search.  With pynini installed you can also run the grammars live
(`backend="pynini"`), which is what grammar authors and custom category
selections use.  Both backends execute the same transducers and are tested to
give identical output.

## Using Damga with speech recognizers and language models

Damga sits between the recognizer and whatever consumes the text, and between
the text generator and the TTS voice:

```
microphone → ASR (Mihu STT, Whisper, …) → Damga ITN → written text → LLM / CRM / display
LLM (Ollama, …) / database → written text → Damga TN → spoken text → TTS
```

### Mihu Turkish STT

[`turkish-stt`](https://github.com/mihu-ai/turkish-stt) (model:
[`mihuai/turkish-stt-66m-v2`](https://huggingface.co/mihuai/turkish-stt-66m-v2)) is a real-time,
CPU-only Turkish recognizer with turn-end detection.  It writes numbers as
words; Damga turns them into their written form.  Damga does not depend on it.
Since turkish-stt 2.0, `mihu_stt.transcribe(..., itn=True)` (`pip install "turkish-stt[itn]"`) runs
Damga for you; the explicit form below gives you streaming control:

```python
import mihu_stt                                # pip install turkish-stt (on-prem, CPU)
from damga import InverseNormalizer
from damga.streaming import StreamingNormalizer

itn = InverseNormalizer()
print(itn.normalize(mihu_stt.transcribe("audio.wav")))   # "… sıfır beş otuz iki …" → "… 0532 …"

stt, sn = mihu_stt.StreamingSTT(), StreamingNormalizer(mode="itn")
for pcm16_chunk in audio_frames():             # 16 kHz int16 bytes, as they arrive
    text, is_final = stt.accept_pcm16(pcm16_chunk, 16000)
    if text.strip():
        res = sn.update(text, is_final=is_final)
        show(res.text)                         # best current rendering, tail may still change
        if is_final:                           # recognizer detected end of turn
            handle(res.text)                   # == itn.normalize(text)
```

The same recognizer is available as a cloud API; its transcripts go through
`itn.normalize` the same way.  `examples/mihu_stt_onprem.py`,
`examples/mihu_stt_cloud.py` and `examples/elevenlabs_stt_tts.py` (ElevenLabs
STT + TTS) are complete scripts; [docs/voice-pipeline.md](https://github.com/mihu-ai/damga/blob/main/docs/voice-pipeline.md)
walks through a live call and a batch transcription step by step.

### Whisper, Ollama and other pipelines

[docs/integrations.md](https://github.com/mihu-ai/damga/blob/main/docs/integrations.md) and the [`examples/`](https://github.com/mihu-ai/damga/blob/main/examples/README.md) folder show
how to put Damga behind **Whisper / faster-whisper** (batch and segment-wise
ITN, and why Whisper's mixed `40 bir` output needs it), in front of a TTS voice
fed by **Ollama** or any other LLM (sentence-wise TN on the streamed reply),
and inside a generic streaming recognizer loop (Vosk, sherpa-onnx, cloud ASR
partials).  The core rule for any streaming source: send Damga the recognizer's
*latest full hypothesis*, never a delta.

## Using Damga for NLP and data work

Damga is not only for voice products.  Anything that reads spoken or
transcribed Turkish (or English, German, …) gets numbers, dates, amounts and
identifiers in one written form, the form NER models, regular expressions,
databases and language models handle best:

```python
from damga import InverseNormalizer, TextNormalizer
itn = InverseNormalizer()

itn.normalize("müşteri yirmi beş bin lira iade istiyor")
# müşteri 25.000 TL iade istiyor
itn.normalize("on dört haziranda saat dokuz buçukta arayın, numaram sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi")
# 14 Haziran'da saat 09:30'ta arayın, numaram 0532 123 45 67
itn.normalize("plakam otuz dört a b c yüz yirmi üç, e posta adresim ali nokta yılmaz et gmail nokta com")
# plakam 34 ABC 123, e posta adresim ali.yilmaz@gmail.com
```

* **Call-centre and meeting analytics:** amounts become numbers you can sum and
  filter (complaints above 5.000 TL), dates and times become comparable.
* **Information extraction:** phone numbers, IBANs, plates, e-mail addresses,
  dates and amounts come out in the shape your NER model or regex expects.
* **Search:** a call in which *on dört haziran* was said is found by `14 Haziran`.
* **Language model input:** consistent written numbers, fewer tokens, better
  arithmetic.
* **Fair ASR evaluation:** normalize both the reference and the hypothesis, so
  *yirmi beş kişi* against `25 kişi` is not counted as two errors.
* **TTS and ASR training data:** `normalize_matching` writes each sentence the
  way it was actually said in its recording:

```python
tn = TextNormalizer(variants=True)
tn.normalize_matching("Saat 09:30'da 250 TL ödendi.", "saat dokuz buçukta iki yüz elli lira ödendi")
# Saat dokuz buçukta iki yüz elli lira ödendi.
```

Damga normalizes forms that are written differently from how they are said
(numbers, dates, times, money, measures, phone numbers, IBANs, plates, e-mail
and web addresses).  It is not a general text cleaner: slang, spelling errors
and stemming are left to tools such as Zemberek, which work well next to it.

## What is covered

ITN: cardinals (with a glued case suffix: `yirmi altıda` → `26'da`), ordinals, negatives, decimals, money (TL/$/€/£ + kuruş/sent),
percent/permille, measurements (km, kg, lt, m², °, MB …), clock times
(`saat dokuz otuz`, `dokuzu çeyrek geçe`, `dokuza on kala`, case suffixes),
dates (`on beş ekim iki bin yirmi altı`, `ekimde`, `yılında`, `iki bin yirmi altıda` → `2026'da`), Turkish phone
numbers (any grouping, `+90`), IBAN, vehicle plates (letters, letter names or
the phonetic alphabet), e-mail and web addresses, street addresses
(`numara on iki daire yedi` → `No: 12 Daire: 7`), the Turkish letter-coding
habit (`Diyarbakır'ın D'si Edirne'nin E'si …` → `De…`), abbreviations and
brands, custom vocabulary.  TN covers the same classes in the written → spoken
direction, including apostrophe suffixes (`2026'da`, `25'te`, `3'üncüsü`).

Known limitations are listed in [docs/grammars.md](https://github.com/mihu-ai/damga/blob/main/docs/grammars.md) (for
example: a lone `bir` is treated as the article, bare four-digit numbers are not
read as years, inflected ordinals such as `üçüncüsü` are not converted by ITN).

## Brands, domains and custom terms

Three data layers, all plain TSV under `damga/tr/itn/data/` (see its README
for sources and licences):

* `brands.tsv` — hand-written brand/product names with official casing and
  Turkish mis-hearings (`vatsap` → WhatsApp, `peypal` → PayPal, `a ve es` → AWS);
* `brands_extra.tsv` — ~700 well-known businesses, brands and Turkish
  institutions, common Turkish words filtered out;
* `domains.tsv` + `email_providers.tsv` — mis-heard mail domains
  (`cimil` → gmail, `yahu` → yahoo) and ~7 800 free-mail provider labels from
  `free-email-domains` (MIT), used to recover a dropped "et" before a known
  provider.  Spellings outside the table (`giymiel` for gmail) are left as heard:
  that is a recognizer error, and the fix is contextual biasing (hotwords) in
  the recognizer with these same lists, not guessing in the normalizer.

Your own terms go in `custom_vocab={...}` (they win over every table).  None
of this requires retraining the recognizer; for recognizer-level coverage use
contextual biasing (hotwords) with the same lists.

## Real recognizer output

Recognizers do not emit clean spoken forms.  Mihu STT, for example, produces
`Sabit hattımız sıfır 5, 3-74, bir dokuz, sekiz yedi bir sekiz` or
`Burak Nokta Koçet örnek banka nokta kom nokta Tier`.  The ITN grammars therefore
accept written digits inside spoken sequences, punctuation inside numbers,
glued separators (`koçet`, `noktaçelik`, `etörnek`), mis-heard TLDs
(`kom`, `tier`, `ay`) and a table of mis-heard domains
(`damga/tr/itn/data/domains.tsv`).

Measured on 575 real Mihu-STT transcripts of synthetic phone/e-mail prompts
(`tests/golden/itn_asr.tsv` holds 84 of them): telephone numbers 256/256
exact, e-mail addresses 274/319 exact (the rest are recognizer errors such as a
dropped "et" or an unrecognisable domain — Damga leaves those as words rather
than guessing).  On the held-out KPI set (300 phone + 300 e-mail clips, 8
unseen voices, Mihu STT v1.2 with hotwords) exact-match is 84% for phone
numbers and 97% for e-mail addresses; the misses are digits dropped by the
recognizer, not normalization errors.

End-to-end (TTS → Mihu STT v1.2 → Damga) on 1 200 synthetic
sentences spoken by 8 unseen voices: money 100%, percent 100%, dates 100%,
times 100%, brands 97%, e-mail 92%, phone numbers 83%, addresses 63%,
letter-by-letter spelling 52% — overall 79.0% exact (the previous regex
normalizer: 52%, with 0% on money, addresses and spelling).  Vehicle plates
on a separate 100-clip set: 74%.  Of the misses, 86% are recognizer errors
(dropped digits, mis-heard letter names); the rest are normalization gaps
tracked in `tests/golden/itn_asr.tsv`.

Safety on ordinary speech is tested the other way round: plain Turkish
sentences pass through with no change other than number, ordinal, date,
money and unit conversions — the
phone, e-mail, plate and spelling grammars never fire on plain text, untouched
words keep their casing, and `normalize(normalize(x)) == normalize(x)`.  The
recognizer frequently emits *written* numbers ("99 lira", "saat 13.30",
"40 bir" = 41); the context grammars accept those mixed forms, bare numbers
are left untouched so identifiers are never regrouped.

## Tests and benchmarks

```bash
pytest                          # unit + golden (TSV) + property + integration tests
python benchmarks/latency.py    # quick per-sentence latency on the shipped runtime (no pynini)
python benchmarks/bench.py --out benchmarks/results/my-machine.md   # full report, needs pynini
```

Golden sets live in `tests/golden/*.tsv` (`input<TAB>expected`); adding a case
is a one-line change.  Measured numbers are in `benchmarks/results/`; on a
2026 MacBook running Python under Rosetta (x86_64 conda build, single thread):
ITN compile 6.4 s once / cached load 26 ms (5.3 MB FAR), p50 latency 1.1 ms
(short utterance), 4.9 ms (two sentences with phone + e-mail), 86 ms (200
words); TN p50 2.2 ms; streaming update p50 1.2 ms; ≈490 MB RSS after a cold
compile (less when loaded from the cache).  Native arm64 or Linux builds are
faster.

## Languages

Turkish (`tr`) is the default language.  Grammars live
under `damga/<lang>/{itn,tn}/`; the engine, cache, streaming wrapper and API
are language-independent.  A new language is a new folder plus one registry
line (`damga/api.py`), after which `Normalizer(mode="itn", lang="en")`,
`InverseNormalizer(lang="en")` and `available_languages()` work — see
[docs/adding-a-language.md](https://github.com/mihu-ai/damga/blob/main/docs/adding-a-language.md).

This release includes Turkish (`tr`), English (`en`), German (`de`), French
(`fr`), Spanish (`es`), Italian (`it`) and Russian (`ru`), TN and ITN for each:

```python
from damga import TextNormalizer, InverseNormalizer
TextNormalizer(lang="en").normalize("EUR 10 million on 6 December 2012")
# ten million euros on the sixth of December two thousand twelve
InverseNormalizer(lang="de").normalize("fünfundzwanzig Prozent")   # 25 Prozent
```

Readings follow what speakers actually say.  The test lines of the languages
other than Turkish still need review by native speakers.

## Contributing

Grammars are plain Python files under `damga/tr/itn/readers`,
`damga/tr/itn/writers`, `damga/tr/tn/...`; data tables are TSV files
under `.../data/`.  Failing golden lines are the best bug reports.  See
[CONTRIBUTING.md](https://github.com/mihu-ai/damga/blob/main/CONTRIBUTING.md) and [docs/architecture.md](https://github.com/mihu-ai/damga/blob/main/docs/architecture.md).

## License

Apache License 2.0 — see [LICENSE](https://github.com/mihu-ai/damga/blob/main/LICENSE).  Pynini and OpenFst are Apache 2.0 as well.
