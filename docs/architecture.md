# Architecture

```
input text
   │  core/unicode.preprocess: NFC, apostrophes, whitespace, Turkish lower-case (ITN)
   ▼
reader FST  (tr/itn/readers/sentence.py — union of all readers + word fallback)
   │  shortest path  →  record, e.g.
   │  word="toplam" cardinal(integer="25600") word="adet"
   ▼
writer FST (tr/itn/writers/sentence.py — union of all writers)
   │  shortest path  →  "toplam 25.600 adet"
   ▼
core/engine.postprocess: spacing around punctuation
```

Both transducers are compiled once per process (or loaded from a FAR cache) and
reused; a request is two compositions and two shortest-path searches, linear
in the input length (≈0.3–1 ms per utterance on a laptop CPU).

## Token-based, not tokenless

The intermediate record is the design decision everything else follows
from.  A *tokenless* normalizer is one transducer that rewrites spoken text to
written text directly; it is one composition cheaper but every rule lives in
one grammar, precedence is implicit in rule order and context, and the only
things you can inspect are the input and the output.  Damga's *token-based*
pipeline splits the problem:

| | token-based (Damga) | single-pass rewrite |
|---|---|---|
| adding a class | one reader + one writer, independent of the others | every rule interacts with every other rule |
| precedence | one weight per class in `DEFAULT_WEIGHTS` | rule order and context |
| debugging | `diagnostics=True` exposes the record | input and output only |
| TN ↔ ITN | same token protocol both ways; TN numbers are the inverse of ITN numbers | unrelated grammars |
| formatting | change a writer, readers untouched | touch the recognition rules |
| cost | two compositions per utterance | one |

The token protocol is `class(field="value" …)` with fields in a fixed
order, plain words as `word="…"`, punctuation as its own `word` token, and
`"`/`\` inside values escaped.  Because the order is fixed there is no Python
between the two passes: the record goes straight into the writer.

## Readers and writers

Every semantic class is a pair of small `Rule` subclasses:

* **reader** – spoken (or written, for TN) text → `class(field="value" …)`.
  Fields are emitted in a fixed order, so the writer needs no re-ordering.
* **writer** – `class(…)` → final text.

A class sets `name` and `kind` and returns its transducer from `build()`:

```python
class MoneyReader(Rule):
    name = "money"
    kind = "read"

    def build(self, cardinal, decimal, variants: bool = False):
        ...
        return self.wrap(graph)
```

`variants=True` makes a reader also produce the other spoken readings of a
form (`2012` → *twenty twelve* next to *two thousand twelve*).  It is what
`TextNormalizer(variants=True)` turns on, under the same name.  ITN
readers ignore it.

The sentence reader unions all readers with **weights**
(`DEFAULT_WEIGHTS`): a semantic class costs ≈1, the word fallback costs 100
per token, so the shortest path prefers any grammar that matches and, among
grammars, the more specific one (telephone < money < cardinal …).

## Numbers

`tr/itn/readers/cardinal.py` is the foundation: fixed-width zero-padded
sub-graphs (`two_digit`, `three_digit`, thousands, millions …) composed with a
leading-zero stripper.  Every other class reuses these sub-graphs, and TN
writers use their **inverse** (`tr/tn/writers/number.py`), which
guarantees that TN and ITN agree on every number.

Ambiguity is resolved with tiny path weights rather than code: "bir yüz"
(non-standard) carries a penalty so the inverse prefers "yüz"; a group ending
on a round word ("otuz", "iki yüz") carries a penalty in telephone grouping so
"beş yüz otuz iki yüz yirmi üç" is read 532 | 123.

## Safety rules

* Entities with a fixed digit count (phone, IBAN) are composed with a format
  acceptor; if the count does not match, the grammar has no path and the words
  stay words.  Nothing is padded.
* A lone "bir" is not converted (it is the indefinite article far more often
  than the number one).
* Bare four-digit numbers are not years; a year needs a month or a year keyword.

## Shared word lists

`damga/tr/lexicon.py` holds the pure-data word lists (digit and tie words,
scale words, month names, year keywords, currency and separator words) with no
pynini import.  The readers build their grammars from it and the streaming
wrapper derives its commit policy (`STREAMING_CONTINUATION`,
`STREAMING_ATTACH_NEXT`) from the same lists, so the grammars and the
streaming boundary rules cannot drift apart.  The module is loaded by
`damga.api.language_lexicon(lang)`; a new language provides its own.
`damga/tr/morph.py` is the other pynini-free helper: it generates the case
suffix forms of a word (vowel harmony, `beşte`/`altıda`, `dördü`), which the
cardinal, percent and date readers use to read a suffix glued to the last
number word (`yirmi altıda` → `26'da`).

## Caching

`core/cache.py` writes `read` and `write` to a FAR file named by a
hash of the grammar sources, the package version, the Pynini version and the
configuration (categories, custom vocabulary).  Any change invalidates the key,
so a stale cache cannot be served.  Default location `~/.cache/damga`
(`DAMGA_CACHE_DIR` overrides).

## Backend boundary

All FST construction goes through `core/rules.py`; the engine only needs
"compose + shortest path + string" from the runtime.  A compiled-FST runtime
(C++ OpenFst with the same FAR files, or a future Rust/C port) can replace the
Pynini calls in `core/engine.py` without touching grammars.

## Runtime backends

* **native** (default in wheels): `damga._fstrt` loads `read.fst` and `write.fst` from
  `damga/<lang>/<mode>/compiled/` (written by `python -m damga.build`) and runs
  *input chain ∘ FST → shortest path* in C++ (OpenFst statically linked). No pynini at run time;
  `custom_vocab` is applied as a whole-word post-pass; custom category selections are not available.
* **pynini**: grammars are built (or loaded from the FAR cache) and run through pynini. Selected
  automatically when pynini is installed and the compiled grammars are older than the grammar
  sources, when categories are customised, or with `backend="pynini"` / `DAMGA_BACKEND=pynini`.

Both backends execute the same transducers, so their output is identical (checked in
`tests/unit/test_native_runtime.py`).
