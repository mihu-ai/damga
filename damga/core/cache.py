from __future__ import annotations

import hashlib
import os
import pathlib
from typing import Any, Iterable

from .. import __version__


def default_cache_dir() -> pathlib.Path:
    env = os.environ.get("DAMGA_CACHE_DIR")
    if env:
        return pathlib.Path(env).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return pathlib.Path(base) / "damga"

def grammar_fingerprint(sources: Iterable[pathlib.Path], extra: str = "") -> str:
    """Hash of the package version, ``extra`` and every grammar source (directories are walked, files taken as is)."""
    h = hashlib.sha256()
    h.update(__version__.encode())
    h.update(extra.encode())
    for src in sources:
        src = pathlib.Path(src)
        files = [src] if src.is_file() else sorted(src.rglob("*"))
        for p in files:
            if p.is_file() and p.suffix in (".py", ".tsv", ".txt") and "__pycache__" not in p.parts:
                h.update(str(p.relative_to(src.parent if src.is_file() else src)).encode())
                h.update(p.read_bytes())
    return h.hexdigest()[:16]

def far_path(cache_dir: pathlib.Path, mode: str, fingerprint: str) -> pathlib.Path:
    return cache_dir / f"{mode}_{fingerprint}.far"

def save_far(path: pathlib.Path, fsts: dict[str, Any]) -> None:
    import pynini

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".far.tmp")
    with pynini.Far(str(tmp), mode="w", arc_type="standard", far_type="default") as far:
        for key in sorted(fsts):
            far[key] = fsts[key]
    os.replace(tmp, path)

def load_far(path: pathlib.Path, keys: Iterable[str]) -> dict[str, Any] | None:
    import pynini

    if not path.exists():
        return None
    out: dict[str, Any] = {}
    try:
        with pynini.Far(str(path), mode="r") as far:
            for key in keys:
                out[key] = far[key]
    except Exception:
        return None
    return out
