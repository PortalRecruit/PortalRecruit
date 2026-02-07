"""Autocomplete helpers for coach-speak queries."""
from __future__ import annotations

from functools import lru_cache

from src.search.coach_dictionary import PHRASES


@lru_cache(maxsize=1)
def all_phrases() -> tuple[str, ...]:
    phrases = []
    for items in PHRASES.values():
        phrases.extend(items)
    return tuple(sorted(set(phrases)))


def suggest(prefix: str, limit: int = 8) -> list[str]:
    p = (prefix or "").lower().strip()
    if not p or len(p) < 2:
        return []
    phrases = all_phrases()
    starts = [s for s in phrases if s.startswith(p)]
    contains = [s for s in phrases if p in s and not s.startswith(p)]
    return (starts + contains)[:limit]


def suggest_rich(prefix: str, limit: int = 25) -> list[str]:
    """Richer autocomplete: includes related phrases from matched buckets."""
    p = (prefix or "").lower().strip()
    if not p or len(p) < 2:
        return []

    try:
        from src.search.coach_dictionary import PHRASES
    except Exception:
        PHRASES = {}

    # direct matches
    direct = [s for s in all_phrases() if p in s]

    # related bucket phrases: any bucket containing a direct match
    related = []
    for bucket, phrases in PHRASES.items():
        if any(p in phrase for phrase in phrases) or any(d in phrase for d in direct for phrase in phrases):
            related.extend(phrases)

    def score(s: str) -> int:
        return 2 if s.startswith(p) else 1 if p in s else 0

    merged = list(dict.fromkeys(direct + related))
    merged.sort(key=lambda s: (-score(s), len(s), s))
    return merged[:limit]
