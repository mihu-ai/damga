import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent

@pytest.fixture(scope="session")
def itn():
    from damga import InverseNormalizer
    return InverseNormalizer(use_cache=False, diagnostics=True)

@pytest.fixture(scope="session")
def tn():
    from damga import TextNormalizer
    return TextNormalizer(use_cache=False, diagnostics=True)

def load_golden(name: str, with_xfail: bool = False):
    """Rows of a golden TSV.  A comment line starting with ``# xfail:`` marks the next row as expected to fail;
    with ``with_xfail=True`` such rows are returned as pytest params carrying ``pytest.mark.xfail(strict=True)``."""
    rows = []
    xfail_reason = None
    for line in (ROOT / "golden" / name).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            if line.startswith("# xfail:"):
                xfail_reason = line[len("# xfail:"):].strip()
            continue
        src, dst = line.split("\t")
        if xfail_reason is not None and with_xfail:
            rows.append(pytest.param(src, dst, marks=pytest.mark.xfail(reason=xfail_reason, strict=True)))
        elif xfail_reason is None:
            rows.append((src, dst))
        xfail_reason = None
    return rows
