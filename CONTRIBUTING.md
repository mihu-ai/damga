# Contributing to Damga

Thank you for helping make Turkish text normalization better.  Most
contributions are one of three kinds, in increasing order of effort:

## 1. Add test cases (no code)

Golden files are tab-separated: `tests/golden/itn.tsv` (spoken → written) and
`tests/golden/tn.tsv` (written → spoken).  Add a line, run `pytest`.  If the
case fails, open a PR anyway and put a `# xfail: <why>` comment on the line
above it; the test then expects the failure and flags it when it starts
passing.  Failing goldens are the best bug reports.  `tests/golden/itn_asr.tsv`
holds real recognizer output: its expected column is what Damga should produce
from that transcript, not what the speaker said.

## 2. Extend a data table

`damga/tr/itn/data/*.tsv` and `damga/tr/tn/data/*.tsv` hold currencies,
units, abbreviations and fixed lexicon entries.  Keep spoken forms in lower case
(Turkish lower case: `İ → i`, `I → ı`), one entry per line, `#` for comments.

## 3. Change or add a grammar

Each class has a **reader** (`.../readers/<class>.py`, spoken/written →
`class(field="value" …)`) and a **writer** (`.../writers/<class>.py`,
record → output).  Follow these rules:

* Build with Pynini primitives from `damga/core/rules.py`; never
  compile per request — a grammar is built once, in its `build()` method.
* Reuse `CardinalReader` sub-graphs (`graph`, `two_digit`, `three_digit`) for
  numbers so all classes agree on how numbers are read.
* Prefer *not converting* over guessing.  A grammar must not create digits,
  letters or units that are not in the input.
* Express precedence with weights in `readers/sentence.py`
  (`DEFAULT_WEIGHTS`), not with ad-hoc Python.
* Add golden cases for every new behaviour, including a negative case
  (an input that must stay unchanged).
* Run `pytest`, `ruff check .`, and `python benchmarks/bench.py` if you
  touched the sentence reader (compile time matters).

Grammar sources are hashed into the FAR cache key, so edits are picked up
automatically; no cache clearing is needed.

## Development setup

```bash
conda create -n damga -c conda-forge python=3.11 pynini pybind11
conda activate damga
pip install -e ".[dev]"
python setup.py build_ext --inplace   # native runtime (damga/_fstrt*.so); needs a C++17 compiler
python -m damga.build                 # compiled grammars under damga/tr/{itn,tn}/compiled/
pytest                                # auto backend
DAMGA_BACKEND=pynini pytest           # grammar sources, live
DAMGA_BACKEND=native pytest           # the compiled grammars, as shipped in the wheel
```

The compiled grammars and the extension are git-ignored (CI builds them); after
editing a grammar run `python -m damga.build` again, otherwise the native
backend keeps serving the old transducers (with pynini installed the engine
notices the stale fingerprint and falls back to pynini automatically).
Shared word lists (digits, months, currency words, streaming boundary words)
live in `damga/tr/lexicon.py`; add new keywords there, not in two places.

## Style

`ruff` (line length 120), type hints where they help, docstrings that show an
input → output example.  Comments explain *why* (a Turkish rule, an ASR quirk),
not *what* the code does.

## Reporting issues

Please include the exact input string, the output you got, the output you
expected and `damga.__version__`.  For ASR-related issues the raw
recognizer output is more useful than the audio.
