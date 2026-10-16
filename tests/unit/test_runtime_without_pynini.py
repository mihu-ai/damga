"""A user who ran `pip install damga` has no pynini: every language must run on the compiled grammars alone, TN,
its readings and ITN.  Grammar modules import pynini, so nothing the run time loads may import them."""
import pathlib
import subprocess
import sys

import pytest

import damga
from damga import available_languages
from damga.core import engine as engine_mod

SCRIPT = r"""
import sys
sys.modules["pynini"] = None          # as if pynini were not installed
from damga import InverseNormalizer, TextNormalizer
lang = sys.argv[1]
tn = TextNormalizer(lang=lang, backend="native")
assert tn.normalize("In 2013 we paid 5 EUR, 1,5 and 21:30.")
variants = TextNormalizer(lang=lang, variants=True, backend="native")
readings = variants.normalize_variants("2013 2,5 1.5", n=5)
assert readings[0] == tn.normalize("2013 2,5 1.5"), readings
variants.normalize_matching("2013", "x")
InverseNormalizer(lang=lang, backend="native").normalize("one two three")
assert "pynini" not in [m for m in sys.modules if sys.modules[m] is not None and m.split(".")[0] == "pynini"]
print("ok")
"""


@pytest.mark.skipif(not engine_mod.native_available(), reason="native runtime not built")
@pytest.mark.parametrize("lang", available_languages())
def test_language_runs_without_pynini(lang):
    # Run next to the damga this test imported (the installed one, or the source tree), not whatever the working
    # directory holds: a source checkout there has no compiled grammars.
    home = pathlib.Path(damga.__file__).resolve().parents[1]
    out = subprocess.run([sys.executable, "-c", SCRIPT, lang], capture_output=True, text=True, timeout=300, cwd=home)
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr[-2000:]
