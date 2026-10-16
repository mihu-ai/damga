from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import pathlib
import sys
import time

from . import __version__
from .api import LANGUAGES


def compile_language(lang: str, modes: tuple[str, ...] = ("itn", "tn"), verbose: bool = True) -> list[pathlib.Path]:
    import pynini

    written: list[pathlib.Path] = []
    for mode in modes:
        module = importlib.import_module(f"{LANGUAGES[lang]}.{mode}.normalizer")
        cls = module.InverseNormalizer if mode == "itn" else module.TextNormalizer
        t0 = time.perf_counter()
        norm = cls(use_cache=False, backend="pynini")
        engine = norm.engine
        out_dir = pathlib.Path(str(module.__file__)).resolve().parent / "compiled"
        out_dir.mkdir(exist_ok=True)
        engine.reader_fst.write(str(out_dir / "read.fst"))
        engine.writer_fst.write(str(out_dir / "write.fst"))
        meta = {
            "lang": lang,
            "mode": mode,
            "damga": __version__,
            "fingerprint": engine.fingerprint,
            "pynini": getattr(pynini, "__version__", ""),
            "read_states": engine.reader_fst.num_states(),
            "write_states": engine.writer_fst.num_states(),
        }
        files = [out_dir / "read.fst", out_dir / "write.fst"]
        variants_file = out_dir / "variants.fst"
        if getattr(engine, "has_variants", False):
            # variants mode: the grammar that also holds the other readings
            grammar = engine._variants_grammar()
            grammar.write(str(variants_file))
            meta["variants_states"] = grammar.num_states()
            files.append(variants_file)
        elif variants_file.exists():
            variants_file.unlink()
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        files.append(out_dir / "meta.json")
        written += files
        if verbose:
            mb = sum(p.stat().st_size for p in files) / 1e6
            print(f"{lang}/{mode}: {out_dir} ({mb:.1f} MB, {time.perf_counter() - t0:.1f} s)")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m damga.build", description="Compile grammars to the native runtime format (needs pynini).")
    ap.add_argument("--lang", action="append", help="language code (default: all registered)")
    ap.add_argument("--mode", action="append", choices=["itn", "tn"], help="itn and/or tn (default: both)")
    args = ap.parse_args(argv)
    langs = args.lang or sorted(LANGUAGES)
    modes = tuple(args.mode or ("itn", "tn"))
    if importlib.util.find_spec("pynini") is None:
        print("pynini is required to compile grammars: pip install 'damga[build]' (conda-forge on macOS)", file=sys.stderr)
        return 2
    for lang in langs:
        compile_language(lang, modes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
