# One reading or all readings (variants)

*Türkçe: [variants.tr.md](variants.tr.md)*

Damga has two TN modes.

- **Deterministic (default):** one input, one output.  `09:30` is always
  *dokuz otuz*.  This is also the only mode of ITN.
- **Variants, `variants=True` (non-deterministic):** one input, several valid
  outputs.  `09:30` is *dokuz otuz* or *dokuz buçuk*; which one fits is decided
  by what was heard (`normalize_matching`) or by a language model
  (`normalize_in_context`), not by the input alone.  The list of readings is
  reproducible (the same readings in the same order every time), and
  `normalize()` still returns the one default reading.

| | One reading (default) | Variants |
| --- | --- | --- |
| Deterministic | **yes**: one input, one output | **no**: one input, several outputs (the list itself is reproducible) |
| How to get it | `TextNormalizer()` | `TextNormalizer(variants=True)` |
| Readings per written form | one | the default plus the other common readings |
| `normalize()` | the one reading | the same one reading, unchanged |
| `normalize_variants()` | `[normalize(text)]` | every reading, default first |
| `normalize_matching(text, heard)` | the default | the reading closest to `heard` |
| `normalize_in_context(text, score)` | the default | the reading a language model scores highest |
| Use it for | voice agents, IVR, reading text aloud, anything live | TTS and ASR training data, fair ASR evaluation |
| ITN | always | not available |

## One reading (default)

The same input always gives the same output.  `2,5` is always *iki virgül
beş*, `09:30` always *dokuz otuz*, `250 TL` always *iki yüz elli Türk lirası*.
Every reading is a line in `tests/golden/tn.tsv`.

This is what a voice needs: the caller hears amounts, times and phone numbers
read the same way in every call, and a test that passes today passes tomorrow.

**For voice AI (voice agents, IVR, live calls), use the default mode.**
There is no recording to match: the agent is the one speaking, so whatever
reading TN gives is what the caller hears.  What matters is that it is the
same every time and that it is fast.  Choosing a reading with a language model
adds latency to every sentence before the TTS can start:

| | Time per sentence | Same output every call |
| --- | ---: | --- |
| Default TN (`normalize()`) | ~1 ms | yes |
| Reading chosen by a Turkish GPT-2 (`normalize_in_context`) | ~0.3 s | yes, for the same model version |
| Reading chosen by a small local LLM (Gemma class, 2B) | ~1.5–2 s | not guaranteed |

Measured on one CPU (Apple M2, 4 threads, native backend, short call-center
sentences).  If you want a different reading in calls (*lira* rather than
*Türk lirası*), change the default reading instead: it then applies in every
call at no cost.  Variants are for preparing training data
offline.

```python
from damga import TextNormalizer

tn = TextNormalizer()
tn.normalize("Saat 09:30'da, 2,5 kg, 250 TL.")
# 'Saat dokuz otuzda, iki virgül beş kilogram, iki yüz elli Türk lirası.'
```

## Variants

People do not read written forms one way.  A speaker recording a TTS dataset
says *dokuz buçuk* for `09:30`; an ASR test set says *iki buçuk lira* where the
text has `2,50 TL`.  If the training or reference text keeps the default
reading, text and audio disagree: the TTS model learns the wrong words and the
ASR model is scored as wrong for being right.

With `variants=True`, TN lists the readings and picks the one that
matches the audio:

```python
tn = TextNormalizer(variants=True)

tn.normalize_variants("Saat 21:45")
# ['Saat yirmi bir kırk beş', 'Saat dokuz kırk beş', 'Saat ona çeyrek var']

tn.normalize_matching("Saat 21:45", heard="saat ona çeyrek var")
# 'Saat ona çeyrek var'
```

`heard` is the transcript of the recording, usually from a recognizer.  The
choice is not random and always gives the same result:

1. **Wording.**  Every variant is compared with the transcript word by word:
   how many words would have to be inserted, deleted or replaced, case and
   punctuation ignored.  Digits the recognizer wrote (`3`, `16-45`, `730'da`)
   stand for any number words, so only the other words count: `üç bin Türk
   lirası` is 2 words away from `Toplam 3 bin lira`, `üç bin lira` 0.  This
   decides *buçuk* / *otuz*, *çeyrek geçe*, *lira* / *Türk lirası*, *yarım*.
2. **Value.**  The digits of the variant's written form (Damga's ITN) are
   compared with the digits of the transcript.  `16-45` supports *on altı kırk
   beş* and not *dört kırk beş*; `730'da` supports *yedi otuzda*, not *on dokuz
   otuzda*.  A leading `0` the recognizer wrote counts as the word *sıfır*, so
   `532 944 …` supports a phone number read without it.
3. The two distances are added and the smallest total wins.  A tie goes to the
   earlier variant, so when the transcript does not tell the readings apart the
   default stays.

The recognizer only decides between readings; the words always come from the
written text.  On recordings ([`examples/tn_variants_asr.py`](../examples/tn_variants_asr.py),
Mihu Turkish STT on CPU):

| Written | Recognizer heard | Chosen |
| --- | --- | --- |
| Toplam 3.000 TL tutuyor. | Toplam 3 bin lira tutuyor | Toplam üç bin lira tutuyor. |
| … %20 indirimle 4.200 TL ödeyeceksiniz. | … yüzde yirmi indirimle 420 lira ödeyeceksiniz | … dört bin iki yüz lira ödeyeceksiniz. |
| … saat 09:30'a aldım. | … saat 930'a aldım | … saat dokuz otuza aldım. (default) |

In the second row the recognizer misheard the amount, yet the amount stays
right: it comes from the text, the recognizer only told *lira* from *Türk
lirası*.

### Measured on 1000 recordings

1000 sentences, each spoken in a reading drawn at random from its variants (so
about half not in the default), by a TTS voice, transcribed by Mihu Turkish STT
on CPU (39% word error rate, many numbers written as digits).  On a held-out
set, `normalize_matching` returns the reading that was spoken for **92.2%**,
the default reading for 49.6%: time 97.1%, money 96.8%, decimals 98.3%, phone
numbers 78.2%.  The misses are mostly phone numbers spoken digit by digit and
transcribed as bare digits, which carry no trace of the grouping.  Method, all
numbers and the misses: [benchmarks/results/tn-variants-20261012.md](../benchmarks/results/tn-variants-20261012.md);
reproduce with `benchmarks/tn_variants.py` and any TTS and recognizer.

### When the transcript matches no reading

`normalize_matching` always returns the closest reading, even when the
transcript belongs to another sentence or the recognizer misheard most of it.
`rank_matching` shows how close each reading is, and `max_distance` falls back
to the default when even the best one is too far:

```python
tn.rank_matching("Saat 09:30'da geldi.", "saat dokuz buçukta geldi")
# [('Saat dokuz buçukta geldi.', 0.0), ('Saat dokuz otuzda geldi.', 0.25)]

tn.normalize_matching("Toplam 3.000 TL tutuyor.", "bambaşka bir cümle bu", max_distance=0.5)
# 'Toplam üç bin Türk lirası tutuyor.'   (best distance 2.25: the default)
```

The distance is about differences per heard word: 0 is a perfect match.  Use
it to sort or filter recordings rather than to fall back: on the 1000
recordings below, the closest reading is still right 80% of the time when its
distance is above 0.3, better than the default alone, so `max_distance` is for
transcripts that may belong to another sentence (a misaligned file), not for
ordinary recognizer errors.  Keeping only distances up to 0.3 kept 72% of the
recordings with 94.8% of their readings right (91% for all).

### Without a recording: choosing by context

When there is no recording, a language model can pick the reading that sounds
most natural in the sentence: *iki buçuk su bardağı* in a recipe.  `normalize_in_context` takes any scorer, a
function from readings to one number each (higher is better), and keeps the
default unless another reading scores more than `margin` higher:

```python
tn.normalize_in_context("Tarifte 2,5 su bardağı un var.", score)
# 'Tarifte iki buçuk su bardağı un var.'
```

Damga ships no model and depends on none.
[`examples/tn_variants_lm.py`](../examples/tn_variants_lm.py) scores with a
Turkish BERT (or any causal model) on the CPU.  It is meant for preparing text
offline; it is too slow for a live voice agent, where the default
is the right choice.

A left-to-right model trained on text close to speech works better than one
trained on written text, which tends to prefer written-style readings.  A recording, when you have one, is the better judge:
`normalize_matching` chooses by what was actually said.

### Which forms have alternatives

| Written | Default | Alternatives |
| --- | --- | --- |
| `09:30` | dokuz otuz | dokuz buçuk |
| `09:30'da` | dokuz otuzda | dokuz buçukta |
| `21:45` | yirmi bir kırk beş | dokuz kırk beş · ona çeyrek var |
| `09:10` | dokuz on | dokuzu on geçe |
| `13:15` | on üç on beş | bir on beş · biri çeyrek geçe |
| `2,5 kg` | iki virgül beş kilogram | iki buçuk kilogram · iki nokta beş kilogram |
| `0,5 lt` | sıfır virgül beş litre | yarım litre · sıfır nokta beş litre |
| `%2,5'e` | yüzde iki virgül beşe | yüzde iki buçuğa · yüzde iki nokta beşe |
| `93,85` | doksan üç virgül seksen beş | doksan üç nokta seksen beş · doksan üç seksen beş |
| `1.6 milyon` | bir nokta altı milyon | bir virgül altı milyon · bir altı milyon |
| `6.97` | altı doksan yedi | altı nokta doksan yedi · altı virgül doksan yedi |
| `17.30'da` | on yedi otuzda | … nokta otuzda · … virgül otuzda · beş otuzda · on yedi buçukta · beş buçukta |
| `250 TL` | iki yüz elli Türk lirası | iki yüz elli lira |
| `2,50 TL` | iki lira elli kuruş | iki Türk lirası elli kuruş · iki buçuk lira |
| `0532 123 45 67` | sıfır beş yüz otuz iki yüz yirmi üç kırk beş altmış yedi | beş yüz otuz iki … (no trunk 0) · sıfır beş üç iki bir iki üç dört beş altı yedi |
| `30.04.2024` | otuz nisan iki bin yirmi dört | otuz sıfır dört … · otuz dört … |
| `toplamı 3. Güzel` | toplamı üç. Güzel | toplamı üçüncü Güzel |

Everything else (dates with a month name, ordinals before a lower-case word,
plain numbers, IBANs, plates, e-mail) has one reading in both modes.

A sentence with several ambiguous tokens gets their combinations: first the
default, then one token changed at a time from left to right, then two, and so
on, at most `n` (`normalize_variants(text, n=10)`; `normalize_matching`
looks at 50).

```python
tn.normalize_variants("Saat 09:30, tutar 250 TL.")
# ['Saat dokuz otuz, tutar iki yüz elli Türk lirası.',
#  'Saat dokuz buçuk, tutar iki yüz elli Türk lirası.',
#  'Saat dokuz otuz, tutar iki yüz elli lira.',
#  'Saat dokuz buçuk, tutar iki yüz elli lira.']
```

### How it works

The reader runs exactly as in the default mode, so every token is
recognised the same way.  Each token is then written on its own with the
default grammar (that is the first reading), and the tokens listed above
add their alternatives from `damga/tr/tn/variants.py`.  The case suffix moves
with the reading (`09:30'da` → *dokuz buçukta*, `%2,5'e` → *yüzde iki
buçuğa*); a clock idiom that cannot carry the suffix (*dokuzu on geçe* + *de*)
is not offered.

The tests check that the first variant equals `normalize()` for every line of
`tests/golden/tn.tsv`, and that the native and pynini backends give the same
variants.

### Other languages

English, German, French, Spanish, Italian and Russian have the same API
(`TextNormalizer(lang="en", variants=True)` and so on).  Their readings
come from a second grammar compiled next to the default one
(`compiled/variants.fst`): it holds the default reading and, weighted behind it,
the other ways speakers read the same form.  The readings of a sentence are its
n best paths; Italian and parts of German vary the default reading word by word
in Python instead, which keeps their grammars small.  Every alternative is a
way speakers actually say the form, for example:

| Language | Written | Default | Other readings |
| --- | --- | --- | --- |
| en | `in 2013` | *two thousand thirteen* | *twenty thirteen*, *two thousand and thirteen* |
| en | `1.5%` | *one point five percent* | *one and a half percent* |
| de | `2012` | *zweitausendzwölf* | *zwanzig zwölf* |
| fr | `2,5 millions` | *deux virgule cinq millions* | *deux millions et demi* |
| es | `2,5 millones` | *dos coma cinco millones* | *dos millones y medio* |
| it | `2016` | *duemilasedici* | *duemila e sedici* |
| ru | `составляет 1000` | *составляет тысячу* | *составляет одну тысячу*, *составляет тысяча* |

## Why ITN has no variants

ITN turns what the recognizer heard into the one written form people and
systems use.  `sıfır beş otuz iki yüz yirmi üç kırk beş altmış yedi` has one
correct form, `0532 123 45 67`; offering a second one means guessing, and a
wrong phone number or amount is worse than words left as words.
`InverseNormalizer(variants=True)` raises `ValueError`.

## Adding an alternative

Turkish: add a branch for the token class in `damga/tr/tn/variants.py` (it
receives the parsed token, its default reading and a function that reads a
number) and a case to `tests/unit/test_variants.py`.  The other languages: add
the reading to the language's variants grammar (`rewrites()` in its
`tn/readers/sentence.py` for a change of words, the reader for a
change of order) with a weight that keeps it behind the default, and a case to
its `tests/golden/test_golden_<lang>.py`.  List only readings that change the
words a speaker says, not style, and only readings speakers actually use.

## Old name (1.0)

In 1.0 the option was called `deterministic`: `deterministic=False` is `variants=True`.
The old name still works and gives a `DeprecationWarning`; it will be removed in 2.0.
