from __future__ import annotations

import pathlib
import re
from typing import Iterable, Sequence

from ...core.categories import resolve_categories
from ...core.engine import Engine
from ...core.readings import Readings
from ...core.tokens import NormalizationResult
from ...core.variants import resolve_variants
from ..lexicon import CASING, FEM

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
LEXICON = ROOT / "lexicon.py"
NUMBERS = ROOT / "numbers.py"

# Feminine nouns: a number ending in 1 before one of them takes "une" (21 voix → vingt et une voix).
FEMININE = (
    "heure heures fois personne personnes voix année années semaine semaines minute minutes seconde secondes tonne "
    "tonnes page pages femme femmes fille filles entreprise entreprises région régions nation nations victime victimes "
    "langue langues proposition propositions mesure mesures journée journées place places voiture voitures famille "
    "familles école écoles ville villes maison maisons mission missions question questions raison raisons étape "
    "étapes priorité priorités condition conditions recommandation recommandations règle règles directive directives "
    "résolution résolutions décision décisions organisation organisations institution institutions délégation "
    "délégations session sessions séance séances réunion réunions conférence conférences élection élections réforme "
    "réformes action actions initiative initiatives livre livres victoire victoires voie voies chance chances fin "
    "zone zones agence agences communauté communautés ligne lignes"
).split()
_FEM = re.compile(r"(?<![\d,.\w])(\d*1)(?= (?:" + "|".join(FEMININE) + r")\b)")
_ISO_DATE = re.compile(r"\b((?:1[5-9]|20)\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")


def prepare(text: str) -> str:
    text = _ISO_DATE.sub(r"\3/\2/\1", text)
    return _FEM.sub(lambda m: m.group(1) if m.group(1).endswith("11") else FEM + m.group(1), text)


def _reader(cats, custom_vocab, variants=False):
    from .readers.sentence import SentenceReader
    return SentenceReader(cats, variants=variants, custom_vocab=custom_vocab).fst


def _writer(cats):
    from .writers.sentence import SentenceWriter
    return SentenceWriter(cats).fst


class TextNormalizer(Readings):
    """French text normalization (written → spoken): ``1,50 €`` → *un euro cinquante*, ``21 voix`` → *vingt et une
    voix*.

    ``variants=True`` adds ``normalize_variants`` / ``normalize_matching`` (``damga.core.readings``) for the
    other readings of a form (``92`` → *nonante-deux*); ``normalize()`` is the same in both modes."""

    def __init__(
        self,
        categories: Sequence[str] | None = None,
        custom_vocab: dict[str, str] | None = None,
        cache_dir: str | pathlib.Path | None = None,
        use_cache: bool = True,
        diagnostics: bool = False,
        lowercase: bool = False,
        backend: str = "auto",
        variants: bool = False,
        deterministic: bool | None = None,
    ):
        from .categories import ALL_CATEGORIES

        self.variants = resolve_variants(variants, deterministic)
        self.lang = "fr"
        cats = resolve_categories(categories, ALL_CATEGORIES)
        self.categories = cats
        self.custom_vocab = dict(custom_vocab or {})
        self.engine = Engine(
            mode="tn",
            build_reader=lambda: _reader(cats, self.custom_vocab),
            build_writer=lambda: _writer(cats),
            source_dirs=[HERE, ROOT.parent / "core", LEXICON, NUMBERS],
            config_key=f"lang=fr|cats={','.join(sorted(cats))}",
            cache_dir=pathlib.Path(cache_dir) if cache_dir else None,
            use_cache=use_cache,
            lowercase=lowercase,
            diagnostics=diagnostics,
            pre_hook=prepare,
            compiled_dir=HERE / "compiled",
            default_config=(cats == ALL_CATEGORIES),
            backend=backend,
            custom_vocab=self.custom_vocab,
            casing=CASING,
            build_variants=lambda: _reader(cats, self.custom_vocab, variants=True),
        )

    def normalize(self, text: str) -> str:
        return self.engine.normalize(text).text

    def normalize_with_details(self, text: str) -> NormalizationResult:
        return self.engine.normalize(text)

    def normalize_batch(self, texts: Iterable[str]) -> list[str]:
        return [self.normalize(t) for t in texts]
