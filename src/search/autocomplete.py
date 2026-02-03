"""Autocomplete helpers for coach-speak queries."""
from __future__ import annotations

from src.search.coach_dictionary import PHRASES


def all_phrases() -> list[str]:
    phrases = []
    for items in PHRASES.values():
        phrases.extend(items)
    # de-dupe + sort
    return sorted(set(phrases))


def suggest(prefix: str, limit: int = 8) -> list[str]:
    p = (prefix or "").lower().strip()
    if not p or len(p) < 2:
        return []
    out = [s for s in all_phrases() if p in s]
    return out[:limit]
