from __future__ import annotations

import pathlib

from .unicode import tr_lower


def load_tsv(path: pathlib.Path, lower_first: bool = True) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        a, b = parts[0].strip(), parts[1].strip()
        rows.append((tr_lower(a) if lower_first else a, b))
    return rows
