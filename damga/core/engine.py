from __future__ import annotations

import importlib
import json
import os
import pathlib
import re
import time
import warnings
from typing import Any, Callable

from .cache import default_cache_dir, far_path, grammar_fingerprint, load_far, save_far
from .tokens import NormalizationResult
from .unicode import TURKISH, Casing, preprocess, reattach_quotes, restore_case

pynini: Any = None
_fstrt: Any = None
try:
    pynini = importlib.import_module("pynini")
except ImportError:
    pynini = None
try:
    _fstrt = importlib.import_module("damga._fstrt")
except ImportError:
    _fstrt = None

_NO_STATE = getattr(pynini, "NO_STATE_ID", -1)

# A sentence that ends in a word with a point (an abbreviation such as "руб." or a plain full stop), not "23.11.".
_ENDS_WITH_ABBREVIATION = re.compile(r"[^\W\d_]\.$")
_SPACE_BEFORE_PUNCT = re.compile(r" +([.,;:!?)\]…])")
_SPACE_AFTER_OPEN = re.compile(r"([(\[]) +")

BACKENDS = ("auto", "native", "pynini")


def native_available() -> bool:
    return _fstrt is not None


def pynini_available() -> bool:
    return pynini is not None


def _compiled_ok(compiled_dir: pathlib.Path | None) -> bool:
    return compiled_dir is not None and all((compiled_dir / f).is_file() for f in ("read.fst", "write.fst", "meta.json"))


class Engine:
    def __init__(
        self,
        mode: str,
        build_reader: Callable[[], Any],
        build_writer: Callable[[], Any],
        source_dirs: list[pathlib.Path],
        config_key: str = "",
        cache_dir: pathlib.Path | None = None,
        use_cache: bool = True,
        lowercase: bool = True,
        preserve_case: bool = True,
        diagnostics: bool = False,
        pre_hook: Callable[[str], str] | None = None,
        compiled_dir: pathlib.Path | None = None,
        default_config: bool = True,
        backend: str = "auto",
        custom_vocab: dict[str, str] | None = None,
        casing: Casing = TURKISH,
        build_variants: Callable[[], Any] | None = None,
    ):
        if backend == "auto":
            backend = os.environ.get("DAMGA_BACKEND", "auto")
        if backend not in BACKENDS:
            raise ValueError(f"backend must be one of {BACKENDS}, got {backend!r}")
        self.mode = mode
        self.casing = casing
        self.pre_hook = pre_hook
        self.lowercase = lowercase
        self.preserve_case = preserve_case
        self.diagnostics = diagnostics
        self.compile_seconds = 0.0
        self.loaded_from_cache = False
        self.far_file: pathlib.Path | None = None
        # variants mode: a reader grammar that also holds the other readings, built or loaded on first use.
        self._build_variants = build_variants
        self._variants: Any = None
        self._use_cache = use_cache
        self.compiled_dir = compiled_dir
        self.fingerprint = grammar_fingerprint(source_dirs, extra=f"{mode}|{config_key}")
        self._vocab = self._vocab_table(custom_vocab, casing)
        self.backend = self._choose(backend, compiled_dir, default_config)
        if self.backend == "native":
            assert compiled_dir is not None
            t0 = time.perf_counter()
            self._nc = _fstrt.Grammar(str(compiled_dir / "read.fst"))
            self._nv = _fstrt.Grammar(str(compiled_dir / "write.fst"))
            self.compile_seconds = 0.0
            self.load_seconds = time.perf_counter() - t0
            return
        cache_dir = cache_dir or default_cache_dir()
        vocab_key = f"{self.fingerprint}|pynini={getattr(pynini, '__version__', '')}|vocab={sorted((custom_vocab or {}).items())}"
        path = far_path(cache_dir, mode, grammar_fingerprint([], extra=vocab_key))
        fsts = load_far(path, ["read", "write"]) if use_cache else None
        t0 = time.perf_counter()
        if fsts is None:
            fsts = {"read": build_reader(), "write": build_writer()}
            self.compile_seconds = time.perf_counter() - t0
            if use_cache:
                try:
                    save_far(path, fsts)
                except OSError:
                    pass
        else:
            self.loaded_from_cache = True
        self.reader_fst = fsts["read"]
        self.writer_fst = fsts["write"]
        self.far_file = path
        self._far_key = vocab_key
        self._cache_dir = cache_dir

    def _choose(self, backend: str, compiled_dir: pathlib.Path | None, default_config: bool) -> str:
        compiled = compiled_dir is not None and _compiled_ok(compiled_dir) and _fstrt is not None
        fresh = False
        if compiled and compiled_dir is not None:
            try:
                meta = json.loads((compiled_dir / "meta.json").read_text(encoding="utf-8"))
                fresh = meta.get("fingerprint") == self.fingerprint
            except (OSError, ValueError):
                fresh = False
        if backend == "pynini":
            if pynini is None:
                raise ImportError("backend='pynini' but pynini is not installed: pip install 'damga[build]'")
            return "pynini"
        if backend == "native":
            if _fstrt is None:
                raise ImportError("backend='native' but the damga._fstrt extension is not available (source install without a compiler?)")
            if not compiled:
                raise FileNotFoundError(f"no compiled grammars under {compiled_dir}; run: python -m damga.build")
            if not default_config:
                raise ValueError("the native backend runs the default grammar configuration only; "
                                 "use backend='pynini' (pip install 'damga[build]') for custom categories")
            return "native"
        if compiled and default_config and (pynini is None or fresh):
            return "native"
        if pynini is not None:
            return "pynini"
        if compiled and default_config:
            warnings.warn("compiled grammars are older than the grammar sources and pynini is not installed; "
                          "using the compiled grammars (run python -m damga.build to refresh)", stacklevel=3)
            return "native"
        if compiled:
            raise ValueError("custom grammar configuration needs pynini: pip install 'damga[build]'")
        raise ImportError("neither compiled grammars nor pynini are available; pip install damga from a wheel, "
                          "or pip install 'damga[build]' and run python -m damga.build")

    @staticmethod
    def _vocab_table(custom_vocab: dict[str, str] | None, casing: Casing) -> list[tuple[re.Pattern[str], str]]:
        table = []
        for spoken, written in sorted((custom_vocab or {}).items(), key=lambda kv: -len(kv[0])):
            pat = re.compile(r"(?<![\w'])" + re.escape(casing.lower(spoken.strip())) + r"(?![\w'])", re.IGNORECASE)
            table.append((pat, written))
        return table

    def read(self, text: str) -> str | None:
        if self.backend == "native":
            out = self._nc.rewrite(text.encode("utf-8"))
            return None if out is None else out.decode("utf-8")
        lattice = pynini.escape(text) @ self.reader_fst
        if lattice.start() == _NO_STATE:
            return None
        return pynini.shortestpath(lattice, nshortest=1, unique=True).string()

    @property
    def has_variants(self) -> bool:
        return self._build_variants is not None

    def _variants_grammar(self) -> Any:
        if self._variants is None:
            if self.backend == "native":
                assert self.compiled_dir is not None
                path = self.compiled_dir / "variants.fst"
                if not path.is_file():
                    raise FileNotFoundError(f"no compiled variants grammar under {self.compiled_dir}; run: python -m damga.build")
                self._variants = _fstrt.Grammar(str(path))
            else:
                assert self._build_variants is not None
                far = far_path(self._cache_dir, f"{self.mode}-variants", grammar_fingerprint([], extra=self._far_key))
                fsts = load_far(far, ["variants"]) if self._use_cache else None
                if fsts is None:
                    fsts = {"variants": self._build_variants()}
                    if self._use_cache:
                        try:
                            save_far(far, fsts)
                        except OSError:
                            pass
                self._variants = fsts["variants"]
        return self._variants

    def read_nbest(self, text: str, n: int) -> list[tuple[str, float]]:
        """The ``n`` best distinct records of ``text`` by the variants grammar with their costs, best first."""
        grammar = self._variants_grammar()
        if self.backend == "native":
            return [(o.decode("utf-8"), cost) for o, cost in grammar.rewrite_nbest(text.encode("utf-8"), n)]
        lattice = pynini.escape(text) @ grammar
        if lattice.start() == _NO_STATE:
            return []
        lattice = pynini.project(lattice, "output").rmepsilon()
        best = pynini.shortestpath(lattice, nshortest=n, unique=True)
        paths = best.paths()
        scored = []
        while not paths.done():
            scored.append((float(paths.weight()), paths.ostring()))
            paths.next()
        scored.sort(key=lambda t: t[0])
        return [(o, w) for w, o in scored]

    def readings(self, text: str, n: int, max_extra: float = 20.0) -> list[str]:
        """Up to ``n`` distinct readings of ``text`` from the variants grammar, best first, finished like
        ``normalize`` output; readings costing more than ``max_extra`` over the best one are dropped."""
        out = self._readings(text, n, max_extra, hook=True)
        if not out and self.pre_hook is not None:
            out = self._readings(text, n, max_extra, hook=False)
        return out

    def _readings(self, text: str, n: int, max_extra: float, hook: bool) -> list[str]:
        base = preprocess(text, lowercase=self.lowercase, casing=self.casing)
        clean = self.prepare(text) if hook else base
        if not clean:
            return [""]
        marks = {c for c in set(clean) - set(base) if not c.isascii() and (not c.isalpha() or c in "ºª")}
        out: list[str] = []
        nbest = self.read_nbest(clean, n)
        for record, cost in nbest:
            if cost > nbest[0][1] + max_extra:
                break
            spoken = self.write_record(record)
            if spoken is None:
                continue
            spoken = self.finish(text, clean, spoken)
            if spoken not in out and not any(c in spoken for c in marks):
                out.append(spoken)
        return out

    def write_record(self, record: str) -> str | None:
        if self.backend == "native":
            out = self._nv.rewrite(record.encode("utf-8"))
            return None if out is None else out.decode("utf-8")
        lattice = pynini.escape(record) @ self.writer_fst
        if lattice.start() == _NO_STATE:
            return None
        return pynini.shortestpath(lattice, nshortest=1, unique=True).string()

    def postprocess(self, text: str) -> str:
        text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
        text = _SPACE_AFTER_OPEN.sub(r"\1", text)
        return re.sub(r" {2,}", " ", text).strip()

    def apply_vocab(self, text: str) -> str:
        for pat, written in self._vocab:
            text = pat.sub(written, text)
        return text

    def normalize(self, text: str) -> NormalizationResult:
        res = self._normalize(text, hook=True)
        if self.pre_hook is None:
            return res
        # When the pre-hook's marks (``º``, ``−``) block a path or survive into the output, read without them.
        base = preprocess(text, lowercase=self.lowercase, casing=self.casing)
        # Letters a pre-hook adds (e.g. a restored accent) are text, not marks.
        marks = {c for c in set(self.pre_hook(base)) - set(base)
                 if not c.isascii() and (not c.isalpha() or c in "ºª")}
        if res.notes or any(c in res.text for c in marks):
            plain = self._normalize(text, hook=False)
            if not plain.notes or res.notes:
                return plain
        return res

    def _normalize(self, text: str, hook: bool) -> NormalizationResult:
        original = text
        clean = self.prepare(text) if hook else preprocess(text, lowercase=self.lowercase, casing=self.casing)
        if not clean:
            return NormalizationResult(text="", original=original, record="", changed=False)
        record = self.read(clean)
        if record is None:
            return NormalizationResult(text=clean, original=original, notes=["read: no path"])
        out = self.write_record(record)
        if out is None:
            return NormalizationResult(text=clean, original=original, record=record, notes=["write: no path"])
        out = self.finish(text, clean, out)
        return NormalizationResult(
            text=out, original=original, record=record if self.diagnostics else None, changed=(out != clean)
        )

    def prepare(self, text: str) -> str:
        """The input as the reader sees it (Unicode cleanup, optional lower-casing, the language's pre-hook)."""
        clean = preprocess(text, lowercase=self.lowercase, casing=self.casing)
        if self.pre_hook is not None:
            clean = self.pre_hook(clean)
        return clean

    def finish(self, text: str, clean: str, out: str) -> str:
        """Everything after the writer: spacing around punctuation, casing, quotes, custom vocabulary."""
        out = self.postprocess(out)
        # One point serves both an abbreviation and the end of the sentence: "25 руб." keeps its full stop when the
        # word is spelled out, "und so weiter." does not get a second one after "usw.".
        if _ENDS_WITH_ABBREVIATION.search(text.rstrip()):
            if out and out[-1] not in ".!?…":
                out += "."
            elif out.endswith("..") and not out.endswith("..."):
                out = out[:-1]
        if self.lowercase and self.preserve_case:
            lowered = clean if self.pre_hook is None else preprocess(text, lowercase=True, casing=self.casing)
            out = restore_case(preprocess(text, lowercase=False), lowered, out)
        if '"' in out:
            out = reattach_quotes(clean, out)
        if self.backend == "native" and self._vocab:
            out = self.apply_vocab(out)
        return out
