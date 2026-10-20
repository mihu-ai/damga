# Changelog

All notable changes to this project are documented here.  The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Turkish ITN: number-word idioms stay words instead of turning into digits — "üç beş kuruş" was
  `3 0,05 TL`, "bin bir gece masalları" was `1.001 gece masalları`, "üç beş kişi" was `3 5 kişi`.  The list
  is `damga/tr/itn/data/idioms.tsv` (one phrase per line; `*` allows suffixes, `+` needs a following word).
  The same words still convert when they are quantities: "bin bir lira" → `1.001 TL`, "beş kuruş" →
  `0,05 TL`, "saat üç beş" → `saat 03:05`, and digit-by-digit dictation ("sıfır beş üç beş …") is unchanged.

## [1.0.2] — 2026-10-17

### Changed
- The option that turns on the other spoken readings of TN is now `variants=True`
  (`TextNormalizer(variants=True)`, all seven languages).  The 1.0 name `deterministic` still works
  (`deterministic=False` is `variants=True`) and gives a `DeprecationWarning`; it will be removed in 2.0.
  ITN rejects `variants=True` with `ValueError`, as before.  `docs/deterministic.md` is now `docs/variants.md`.

### Fixed
- Russian TN variants no longer list a dative, instrumental or prepositional form of a number the sentence
  does not ask for (*я купил тремя книги*, *пятью килограммами*); the other nominative, accusative and
  genitive readings stay, for `normalize_matching`.
- `docs/variants.md`: the Russian example had the default and the alternative reading swapped.

## [1.0.1] — 2026-10-17

### Added
- Turkish ITN: spelled codes and names, both with example words ("K yani Kayseri, M yani Muş" → `KM`)
  and with letter names ("ye ı le me a ze" → `YILMAZ`, "de a yumuşak ge" → `DAĞ`)
- Turkish ITN: phone numbers with a case ending on the last group ("… otuz dörtten" → `0532 645 12 34'ten`)
- Turkish ITN: car model names (`Hyundai i20`, `Audi A4`)

### Fixed
- Links in the README now point to GitHub, so they also work on PyPI
- Python 3.13 classifier

## [1.0.0] — 2026-10-16

Initial release.  Turkish, English, German, French, Spanish, Italian and Russian support.

### Added
- Self-contained runtime: `damga._fstrt`, a small C++ extension with OpenFst 1.8.4 statically linked
  (`third_party/openfst`, Apache-2.0), runs the precompiled grammars shipped in the wheel
  (`damga/<lang>/<mode>/compiled/`); `pip install damga` works on Linux, macOS and Windows with no
  other dependency and no first-run compile. pynini is the optional `build` extra
  (`python -m damga.build` compiles grammars); `backend="auto"|"native"|"pynini"` and `DAMGA_BACKEND`
  select the engine, both backends are tested to give identical output.
- Per-language layout: grammars under `damga/<lang>/{itn,tn}/` (Turkish = `damga/tr`), language
  registry in `damga/api.py`, `lang=` parameter on `Normalizer`/`InverseNormalizer`/`TextNormalizer`
  (default `tr`), `available_languages()`; adding a language is a new folder plus one registry line.
- WFST engine (Pynini/OpenFst): reader → writer pipeline (`readers/`, `writers/`), FAR cache keyed by
  grammar source hash + version, Turkish-aware Unicode preprocessing.
- ITN grammars: cardinal, ordinal, negative, decimal, money, percent/permille,
  measure, time (incl. `geçe`/`kala` and case suffixes), date, telephone, IBAN,
  plate, e-mail/web, address, spelling, lexicon entries + custom vocabulary.
- TN grammars for the same classes, including apostrophe suffixes.
- `Normalizer`, `InverseNormalizer`, `TextNormalizer` APIs with batch support,
  category selection, strict mode, `preserve_case` and diagnostics.
- `StreamingNormalizer` with revision-aware partial hypotheses, safe-boundary
  commits (3-word lag, attach-next back-off), bounded buffering, `flush()`/`reset()`;
  the final result is always re-normalized from the whole utterance
  (final == batch on 1 200/1 200 simulated utterances).
- `address` ITN class: `numara on iki daire yedi` → `No: 12 Daire: 7` (`no`/`numara`, `kat`, `daire`).
- `spelling` ITN class for the Turkish letter-coding habit `Diyarbakır'ın D'si, Edirne'nin E'si …` → `Derya`.
  The mnemonic's first letter decides; the letter token is accepted loosely as recognizers mangle it
  (`desi`, `ağası`, `üyesi`, `nisi`, `NS'i`, `H S`, `es`, glued `niğde'ninesi`, bare `konya'nın ke`).
  All Turkish letters are covered (ğ via `yumuşak ge'si`; mnemonics starting with â/î/û map to a/i/u).
  Guarded against ordinary speech: loose letter tokens only after a possessive mnemonic, function words
  (`ve`, `ile`, …) are never mnemonics, 3+ letter acronyms (`BBC ve ITV`) are not letter tokens.
- Brand/domain tables: `brands.tsv`, `brands_extra.tsv`, `domains.tsv`, `email_providers.tsv`
  (free-email-domains, MIT); inflected brands keep their suffix (`mercedes'iniz` → `Mercedes'iniz`).
  Entries that are ordinary Turkish words (`boş`, `krom`, `garanti`, `pınar`, `martı`, `metro`, `koç`, `meta`,
  `safari`, …) are deliberately absent: context-free capitalisation corrupts normal speech
  (`boş zaman` → `Bosch zaman`); multi-word forms (`Garanti BBVA`, `Koç Holding`) are kept.
- Recognizer-tolerant grammars: written digits and punctuation inside spoken numbers, ROUND penalty and
  follower guard for telephone/IBAN grouping, `graph_mixed` (`40 bir` = 41) inside context classes,
  glued `et`/`nokta`, `dat`/`dot`, `noktacom`, TLD aliases (`kom`, `ay`) next to a *spoken* dot only,
  known-domain recovery, Levenshtein domain aliases, phonetic alphabet and spelled letters in plates.
  Two bare words are glued into an e-mail local part only across a plain space (never a comma); a bare,
  already-written domain (`Gezginler.com`) is left untouched unless something in it was spoken.
- `preprocess(keep_caps=True)`: 1–3 letter ALL-CAPS recognizer tokens are kept (spelled letters);
  an ALL-CAPS utterance is lower-cased as a whole so `YİRMİ BEŞ` still becomes `25`.
- `preserve_case=True` (default): words the grammar leaves untouched keep the recognizer's casing.
- Quotes and backslashes inside tokens are escaped in the token record and re-attached from the source spacing.
- Golden test sets (ITN/TN/real recognizer output), property-based tests, streaming and adapter tests;
  benchmark script with measured results.
- Validation: 1 200 end-to-end TTS → Mihu STT → Damga sentences (79% exact; the previous regex
  normalizer 52%), 600-clip phone/e-mail KPI set, and a false-positive scan on plain Turkish sentences (no
  change other than number/ordinal/date/money/unit conversions).
- Six languages besides Turkish, TN and ITN each: English (`en`), German (`de`), French (`fr`), Spanish (`es`), Italian
  (`it`) and Russian (`ru`), with `lang="…"` everywhere (`TextNormalizer`, `InverseNormalizer`, `Normalizer`,
  `StreamingNormalizer`).  Readings follow what speakers actually say: English years 2010–2019 *two thousand
  thirteen* and from 2020 *twenty twenty four*, German numbers
  written as one word, French *mille neuf cent*, Spanish gender agreement (*veintiuna personas*), Italian
  *duemilasedici*; Russian agrees numbers with case and gender (*до пяти лет*, *в две тысячи двенадцатом году*).
- The core takes a language's casing rules (`damga.core.unicode.Casing`); Turkish stays the default.
- Non-deterministic TN for all seven languages: `TextNormalizer(lang=…, deterministic=False)` gives
  `normalize_variants`, `normalize_matching` and `normalize_in_context` (`damga.core.readings`).  The readings of
  the new languages come from a variants grammar compiled next to the default one (`compiled/variants.fst`) and
  read by the native runtime's new n-best search (`Grammar.rewrite_nbest`); see `docs/deterministic.md`.
- `damga.core.variants.best`: the closest reading without computing the value signal of readings that cannot win
  (same result as `rank(...)[0]`).
- Turkish coverage round.
  TN: point decimals (`1.6 milyon` → *bir nokta altı milyon*, `6.97` → *altı doksan yedi*, `%3.6`), ranges and
  scores (`3-5`, `%30-40`, `7.-8. sınıf`, `2-1`), letters with numbers (`Covid-19`, `F-35'ler`,
  `F16`), ordinals before names (`1. Dünya Savaşı` → *birinci*), glued ordinals (`6.sınıf`), `+`/`−` signs and a
  free-standing `-` next to a one-letter variable (`15 - b` → *on beş eksi b*; between two whole numbers it is a range, `2 - 1` → *iki bir*, otherwise it stays a dash), `3.50 TL` as money, `5-li` as `5'li`, `,5'luk` → *buçukluk*, numeric dates with a suffix,
  abbreviated years (`'19`).  Variants: `nokta`/`virgül`/bare decimal readings, point decimals as clock times, a
  numeric month read as a number, `N.` before a capitalised word as an ordinal.
  ITN: `bir nokta dokuz` → `1,9`; a scale word after a decimal stays a word (`on iki virgül üç milyon` →
  `12,3 milyon`, was `12,3000000`; `iki buçuk milyon` → `2,5 milyon`, was `2,5 1.000.000`); every inflection of
  the last word of a multi-word number (`kırk beşin` → `45'in`, was `40 beşin`; `yüz elliydi` → `150'ydi`;
  `yirmi dokuzunda` → `29'unda`) and after `yüzde` (`yüzde on altısı` → `%16'sı`, `yüzde onluk` → `%10'luk`);
  decade words alone with plural/`-li`/`-lik`/genitive (`doksanlı yıllar` → `90'lı yıllar`, `yetmişler`);
  genitive of single digit words (`sekizin` → `8'in`); years before plural year words (`1950 yılları`); month
  names written with an apostrophe (`bir Mayıs'ta` → `1 Mayıs'ta`).  New options `group_four_digits=False` and
  `scale_words=True` (defaults unchanged).
- Non-deterministic TN: `TextNormalizer(deterministic=False)` adds `normalize_variants()` (every reading of a
  written form, the default first: `09:30` → *dokuz otuz*, *dokuz buçuk*; `2,5` → *iki buçuk*; `250 TL` → *… lira*;
  `21:45` → *ona çeyrek var*; phone numbers digit by digit) and `normalize_matching(text, heard)` (the reading
  closest to a transcript, for TTS/ASR training text).  Deterministic stays the default and `normalize()` output
  is unchanged; ITN rejects `deterministic=False`.  See `docs/deterministic.md`.
- `normalize_matching(..., max_distance=)` and `rank_matching()`: every reading with its distance to the
  transcript (about differences per heard word), to filter recordings; `max_distance` falls back to the default
  for a transcript that may belong to another sentence.
- `normalize_in_context(text, score, margin=)`: choose a reading without a recording, with any scorer (e.g. a
  language model); the default stays unless another reading wins by more than `margin`.  Damga ships no model;
  `examples/tn_variants_lm.py` uses a Turkish GPT-2 on the CPU.
- `benchmarks/tn_variants.py`: end-to-end test of `normalize_matching` (sentences → reading drawn at random → any
  TTS → any recognizer → score).  With Mihu Turkish STT on a held-out 1000 recordings: 92.2% of spoken readings
  recovered vs 49.6% for deterministic TN (`benchmarks/results/tn-variants-20261012.md`).
- ITN `repair_spelling=True` (default): diacritic-less (`yuz elli`, `uc`, `bes`, `sifir`) and glued
  (`yirmibeş`, `onbeş`, `üçyüzkırkbeş`) number words are restored before the grammars run, so recognizer output
  no longer ends up half-converted (`seksen bes` → `80 bes`).  Closed vocabulary only; `binbir`, `uç` and
  words such as `yüzbaşı` are left alone.  See `damga/tr/itn/repair.py`.
- E-mail: `alt tire` / `altı tire` as underscore, `ko` / `cım` / `kım` / `kem` as spoken `com`.
- ~115 brand and ~40 mail-domain mis-hearing variants, 25 spelled acronyms (GSM, SMS, ATM, VIP, QR, CPU, API, KPI,
  CEO, TCDD, …) in the data tables.
- ~650 new golden cases (ITN and TN), property tests for phone digit preservation and unit-vs-plate, and strict
  xfails for the gaps that remain.
- ITN: `sıfır sıfır` / `sıfır beş` minutes after the hour (`saat yirmi iki sıfır sıfır` → `saat 22:00`), `çeyrek var` /
  `on var` (`sekize çeyrek var` → `07:45`), `https iki nokta bölü bölü mihu nokta ai` → `https://mihu.ai`
  (with `bölü` path parts), `bilgi@` as a local part, plate letter name `ka`, spelled acronyms of three or more
  consonant letter names (`a be ce` → `ABC`, `ka pe ka` → `KPK`), idioms kept as words (`beş parasız`, `yüz yüze`),
  fractions kept as words (`üçte bir`, `onda biri`; `saat üçte bir toplantı` still reads the time).
- `repair_spelling` also restores ASCII-folded suffixed forms (`sifirdan`, `bese`, `dortte`, `altmisa`); accusative
  and genitive forms are not touched because `besi` / `beste` are real words.
- E-mail: a two-word domain label glued to the TLD (`et örnek mağaza.com` → `@ornekmagaza.com`), capitalized
  spoken TLDs (`nokta TR`), a recognizer comma after a role word (`iletişim, Özdemir`), and the `giymiel` family of
  gmail mis-hearings.
- Streaming: ASCII-folded number words count as continuation words, like their diacritic spellings.
- `tests/golden/itn_asr.tsv` is now asserted (`test_golden_itn_asr.py`); `# xfail: <why>` comment lines mark
  tracked gaps as strict xfails.  The expected column follows `preserve_case` (untouched words keep the
  recognizer's casing).
- `examples/mic_streaming.py`: live microphone → Mihu STT → streaming ITN.
- `benchmarks/latency.py`: quick pynini-free latency check on the native runtime.
- `docs/integrations.md`: Whisper / faster-whisper, generic streaming recognizers (Vosk, sherpa-onnx, cloud
  partials), Ollama and other LLMs (sentence-wise TN before TTS), TTS engines, voice-agent frameworks.
  Examples `examples/whisper_itn.py` and `examples/ollama_tn_tts.py` (stdlib only).
- `damga.streaming.split_sentences()` / `SentenceSplitter`: cuts streamed text (LLM tokens) into sentences only
  where the punctuation is followed by whitespace, so `25.600` or `15.10.2026` arriving token by token stays whole;
  ordinals (`3. sırada`) and common abbreviations are not sentence ends.  Use it before TN on a streamed reply.
- Examples: `examples/mihu_stt_onprem.py` (Mihu STT on your CPU, batch + simulated stream, `--model-dir`),
  `examples/mihu_stt_cloud.py` (Mihu STT cloud API, file upload and WebSocket stream),
  `examples/elevenlabs_stt_tts.py` (ElevenLabs Scribe → ITN, TN → ElevenLabs voice, and a round trip).
- `docs/voice-pipeline.md` / `docs/voice-pipeline.tr.md`: how Damga works in a live call and in batch
  transcription, on-prem and cloud, with what the pipeline tests verify (English and Turkish).
- `tests/integration/test_voice_pipeline.py`: Damga inside a voice pipeline without network or models — live
  captions from streaming STT hypotheses (committed text only grows, final equals batch ITN), a full voice-agent
  turn (ITN into the LLM, sentence-wise TN of a token-streamed reply into the voice, speech starting before the
  reply ends), turns that start clean, per-segment ITN of recordings, and concurrent calls.
- `damga/tr/lexicon.py`: pure-data word lists (digits, ties, scales, months, year/currency/separator words)
  shared by the grammars and the streaming commit policy; `damga.api.language_lexicon(lang)`;
  `StreamingNormalizer(lang=...)`.
- README: "How it works" section explaining the token-based two-pass pipeline and why it is not a single-pass
  rewrite; integration overview.
- TN: an IBAN is read digit by digit with a pause between the written groups (`TR33 0006 1005 …` → *te re üç üç,
  sıfır sıfır sıfır altı, bir sıfır sıfır beş, …*); fractions (`3/4` → *dörtte üç*, `1/2` → *ikide bir*, up to /100)
  and `7/24` → *yedi yirmi dört*; speed units `km/s`, `km/h`, `m/s`; a range of numbers with three or more digits
  takes *ile* (`1914-1918` → *bin dokuz yüz on dört ile bin dokuz yüz on sekiz*), short ranges and scores stay as
  said (`3-5` → *üç beş*, `2-1`).
- TN, Turkish: after a bank word (`hesap numarası`, `hesap no`, `şube kodu`, `müşteri numarası`) a number is
  dictated digit by digit with a pause between the written groups (`Hesap no 1234-5678-90` → *bir iki üç dört, beş
  altı yedi sekiz, dokuz sıfır*).
- TN, every other language: IBANs of any country are spelled and read digit by digit with a pause between the
  groups (`DE89 3704 …` → *D E acht neun, drei sieben null vier, …*), and domestic bank numbers after their keyword
  are read digit by digit: English sort code, account and routing number; German BLZ and Kontonummer; French RIB,
  code banque/guichet; Spanish número de cuenta and CCC; Italian ABI, CAB and conto; Russian р/с, к/с, БИК, ИНН,
  КПП, ОГРН.  `m/s` (`м/с`) is read in all six; `24/7` → *vingt-quatre sur sept* (it was read as a fraction),
  *veinticuatro siete*, *ventiquattro su sette*, *двадцать четыре на семь*; fractions in Spanish (`3/4` → *tres
  cuartos*, `1/2 kilo` → *medio kilo*), Italian (*tre quarti*) and Russian (*три четвертых*, with case); scores
  are no longer read as ranges in German (`2-1` → *zwei zu eins*) and Russian (*два один*); year ranges take a
  connector in French (`1914-1918` → *… à …*; the juxtaposed reading stays a variant) and Italian (*… al …*,
  `100-200` → *cento a duecento*).  New TN categories: `bank` (en, de, es), `fraction` (es, it), `iban` and
  `bank_account` (it).
- TN telephone numbers in German, Spanish, Italian and Russian (there was no telephone grammar; `030 1234567` was
  *null drei null eine Million …*) and North American formats in English (`(212) 555-1234` → *two one two, five
  five five, one two three four*, `1-800-…` → *one, eight hundred, …*, `ext. 123`): read the way each language
  dictates them (digit by digit in German, Italian and English; 2-digit groups as numbers in Spanish; groups as
  numbers in Russian, `+7 (495) 123-45-67` → *плюс семь, четыреста девяносто пять, сто двадцать три, …*), with
  a pause between the written groups.  English UK and international numbers get the pauses too.  A keyword
  (`Tel.`, `Teléfono`, `Cellulare`, `тел.` …) allows more shapes; without one only the national phone shapes count.
  Turkish: a suffix after a phone number (`0212 123 45 67'den`) no longer breaks the number apart.
- TN, German: acronyms said as a word are written as one (`SCHUFA-Auskunft` → *Schufa-Auskunft*, `TÜV`, `BAföG`,
  `NATO`, `DAX` …; table `de/tn/data/acronym_words.tsv`), so a TTS voice does not spell them; spelled ones
  (`ADAC`, `GmbH`) stay.  New TN category `telephone` in de, es and it.
- ITN telephone numbers in English, German, French, Spanish, Italian and Russian (they stayed words or came out
  half converted, `plus 33 un 23 …`): `call plus four four two zero seven nine four six zero nine five eight` →
  `call +44 20 7946 0958`, `plus vier neun drei null …` → `+49 30 12345678`, `zéro six douze trente-quatre …` →
  `06 12 34 56 78`, `más treinta y cuatro nueve uno dos …` → `+34 912 345 678`, `più trentanove zero sei …` →
  `+39 06 12345678`, `плюс семь четыреста девяносто пять …` → `+7 495 123-45-67`; digits spoken one by one or in
  groups, `double`/`oh`/`zwo`, national layouts (UK, North American, French pairs, Spanish 3-3-3, Russian
  3-3-2-2).  Bare short runs and ordinary numbers stay as they are.  Turkish: a 90 said right before a mobile
  number is the country code when the recognizer dropped `artı` (`doksan beş yüz otuz iki …` → `+90 532 …`).
- TN international formats: `+CC-…` with dashes, `00CC`, a `(0)` trunk or an area code in parentheses, and glued
  `+CC…` numbers (a known country code is split off) in every language; Turkish `+90-532-…` (it was read as a
  range with *ile*) and `0090 …`.  French phone numbers get a pause between their pairs.
- Fixes across the languages:
  - English: ITN values (`… point five eight thousand` was `164.5 8,000`, `ninety nine hundred … dollars`,
    `one fifty five dollars`), clock phrases (`half past three` → `3:30`, `a quarter to four`), spelled e-mails and
    URLs, IP addresses; TN dates and decades, codes, digits after `card ending in`/PIN/OTP, `2 1/2`, money per unit
    and ranges, street abbreviations (`Elm St.` was *saint*), more units.
  - German: TN `Er wurde 3. von 120.` → *dritter* (was *drei.*), fractions with any denominator, `eineinhalb`, money
    with lower-case scale words, per-unit measures, times with seconds; ITN numbers said in pieces (`zwei hundert
    vier und fünfzig` → `254`), `neunzehn achtzig` → `1980`, money with cents, spelled e-mails.
  - French: ITN `au moins vingt pays` was `au -20 pays` (a frequent phrase), wrong values in years and
    `onze cents`, glued scale words, clock phrases (`midi moins le quart` → `11 h 45`), money agreement, spelled
    e-mails, fractions after `de`; TN numeric dates, `1 1/2` → *un et demi*, day lists, titles `Mᵐᵉ`, `Dʳ`.
  - Spanish: TN `1.000` was read as a clock time (*1:000*), `1 enero` → *uno de enero*, ordinals `1.ᵉʳ`/`2da`,
    fractions (`1/21` → *un veintiunavo*), cents (`5,01 €` → *… con un céntimo*), 30 more currencies, times with
    a.m./p.m. and seconds, abbreviations; ITN decimals said in groups, money, clock phrases, compound ordinals,
    spelled e-mails.
  - Italian: space-grouped thousands (`3 000 000 000 euro` was read digit by digit), money with cents (`€ 1.234,56`
    → *… euro e cinquantasei*), `un milione di euro`, times with seconds, e-mail/URL reading, 20 abbreviations.
  - Russian: TN money with kopecks/cents (`25 600,50 руб.` → *… рублей пятьдесят копеек*, was a decimal), `4-х` →
    *четырех*, more date formats; ITN values (`тридцать одного рубля` was `30 одного`, `одна тысяча девятьсот …`
    was `1000 996-го`), fractions, `часов и … минут`, a new spelled e-mail/URL reader.
- Writing-style options, off by default and applied after the grammars (no pynini needed): English ITN
  `unit_symbols=True` (`two hundred kilometers per hour` → `200 km/h`), Spanish TN `formal_ordinals=True`
  (`el 80.º aniversario` → *el octogésimo aniversario*), Russian ITN `ordinal_digits=True` (`восьмого` → `8-го`),
  German ITN `fraction_digits=True` (`drei viertel` → `3/4`).
- A sentence that ends in an abbreviation keeps its full stop (`Я заплатил 25 руб.` → *… двадцать пять рублей.*);
  ITN no longer doubles it (`und so weiter.` → `usw.`).  English `hr`/`hrs`/`mins`/`sec`/`secs`, Italian
  `mln`/`mld`, and Italian country codes said as a number (`+39` → *più trentanove*).

### Known limitations
- `beş yüz altı yüz yetmiş beş …` is genuinely ambiguous (500 | 675 or 506 | 175); the
  reading with fewer round groups wins.
