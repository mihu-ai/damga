# Release checklist

Nothing below is automated on purpose; a human runs it and ticks the boxes.

- [ ] `pytest` green on Linux (CI) and on the maintainer's machine
- [ ] `ruff check .` and `mypy damga` clean (or documented exceptions)
- [ ] `python benchmarks/bench.py --out benchmarks/results/<machine>-<date>.md` committed
- [ ] `CHANGELOG.md` updated, version bumped in `pyproject.toml` **and** `damga/__init__.py`
- [ ] Golden files reviewed: every new line was checked by a Turkish speaker
- [ ] `python -m damga.build` (pynini) then `python -m build` → sdist + wheel; `twine check dist/*`
- [ ] Install the wheel in a fresh conda env (`conda create -n t -c conda-forge python=3.11 pynini && pip install dist/*.whl`) and run the README examples
- [ ] Dependency licences re-verified (pynini Apache-2.0, OpenFst Apache-2.0); no data table copied from a non-Apache source
- [ ] Push to `main`; CI (`ci.yml`) must be green on all wheel platforms (Linux x86_64/arm64, macOS, Windows)
- [ ] Tag `v<version>` and push the tag: the `publish` job (GitHub environment `pypi`, PyPI trusted publisher, no tokens) uploads wheels + sdist; GitHub release notes = changelog section
- [ ] Announce; update the Mihu STT model card link if the integration changed
