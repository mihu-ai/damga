from __future__ import annotations

from typing import Sequence

# Aliases accepted in ``categories=[...]``.
RENAMED = {"whitelist": "lexicon_entry", "electronic": "email_url"}


def resolve_categories(categories: Sequence[str] | None, all_categories: tuple[str, ...]) -> tuple[str, ...]:
    if categories is None:
        return all_categories
    return tuple(RENAMED.get(c, c) for c in categories)
