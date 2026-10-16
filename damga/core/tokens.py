from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NormalizationResult:

    text: str
    original: str
    record: str | None = None
    changed: bool = False
    notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.text

    @property
    def tagged(self) -> str | None:
        """Alias of ``record``."""
        return self.record
