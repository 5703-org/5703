"""Minimal feature flag evaluation (Spec A14, K10).

Flags come from typed config today; the Flag modelled in the DB arrives with
the admin UI in a later iteration. Unknown flags are always OFF (safe default).
"""

from __future__ import annotations

from app.core.config import Settings


class FeatureFlags:
    def __init__(self, flags: dict[str, bool]):
        self._flags = flags

    def enabled(self, name: str) -> bool:
        return self._flags.get(name, False)

    def as_dict(self) -> dict[str, bool]:
        return dict(self._flags)


def build_flags(settings: Settings) -> FeatureFlags:
    return FeatureFlags(settings.flags)
