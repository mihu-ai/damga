# Adding a language

Damga ships Turkish (`tr`), English (`en`), German (`de`), French (`fr`),
Spanish (`es`), Italian (`it`) and Russian (`ru`), and is laid out so that
another language is a new folder, not a code change elsewhere.

```
damga/
  core/            language-independent engine, cache, Unicode helpers, token model
  streaming/       language-independent streaming wrapper and sentence splitter
  tr/              Turkish
    itn/           normalizer.py, readers/, writers/, data/*.tsv
    tn/            normalizer.py, readers/, writers/, data/*.tsv
  en/ de/ fr/ …     the other languages, same layout
```

## Contract

A language package `damga/<lang>/` must provide:

| module | class | constructor | methods |
|---|---|---|---|
| `damga/<lang>/itn/normalizer.py` | `InverseNormalizer` | `(categories=None, strict=False, custom_vocab=None, cache_dir=None, use_cache=True, preserve_case=True, diagnostics=False, **lang_specific)` | `normalize(text) -> str`, `normalize_with_details(text) -> NormalizationResult`, `normalize_batch(texts) -> list[str]` |
| `damga/<lang>/tn/normalizer.py` | `TextNormalizer` | same shape | same |
| `damga/<lang>/lexicon.py` | — | — | pure data, no pynini: `STREAMING_CONTINUATION` and `STREAMING_ATTACH_NEXT` frozensets for the streaming commit policy (plus whatever word lists the grammars share) |

Both classes build their grammars with the shared `damga.core.engine.Engine`
(reader FST + writer FST, FAR cache keyed by the grammar sources) and the
shared `Rule` base class; see `damga/tr/itn/normalizer.py` for the
reference implementation (about 60 lines).

Readers emit `class(field="value")` tokens, writers unwrap them; the
`word` and `punctuation` fallbacks are language-independent and can be imported
from `damga.tr.itn.readers.word` or copied.

## Registering

Add one entry to `LANGUAGES` in `damga/api.py`, for example Dutch:

```python
LANGUAGES = {"tr": "damga.tr", "en": "damga.en", …, "nl": "damga.nl"}
```

and the language is available everywhere:

```python
from damga import Normalizer, InverseNormalizer, available_languages
available_languages()                      # [..., "nl", ...]
Normalizer(mode="itn", lang="nl")
InverseNormalizer(lang="nl")
StreamingNormalizer(mode="itn", lang="nl")  # uses damga.nl.lexicon for its commit policy
```

The lexicon also gives the language's lower-casing rules (`CASING`, a `damga.core.unicode.Casing`; Turkish
is the default, where `I` lower-cases to `ı`).

`lang` defaults to `damga.DEFAULT_LANG` (`"tr"`), so existing callers keep working.

## Data files

Put TSV tables under `damga/<lang>/itn/data/` and `damga/<lang>/tn/data/`;
`pyproject.toml` already packages `*/itn/data/*.tsv` and `*/tn/data/*.tsv`
for every language folder.  Record the source and licence of each table in
`damga/<lang>/itn/data/README.md` (Apache-2.0 compatible sources only).

## Tests

Mirror `tests/golden/` with `tests/golden/<lang>/itn.tsv` and `tn.tsv`
(`input<TAB>expected`) and parametrize `tests/golden/test_golden_itn.py` over
the language folders.  Golden lines must be reviewed by a native speaker.
