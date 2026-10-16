"""Run the golden and unit tests against the installed damga (the wheel), not the source tree.

pytest puts the project root on sys.path, so running ``{project}/tests`` in place imports the uncompiled
``damga/`` next to it.  This copies the tests to a temporary directory and runs them there.

    python tests/run_installed.py
"""
import pathlib
import shutil
import sys
import tempfile

import pytest

if __name__ == "__main__":
    here = pathlib.Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as tmp:
        dest = pathlib.Path(tmp) / "tests"
        shutil.copytree(here, dest, ignore=shutil.ignore_patterns("__pycache__"))
        sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", "--rootdir", tmp,
                              str(dest / "golden"), str(dest / "unit")]))
