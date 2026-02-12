from __future__ import annotations

from typing import Dict, Any


def generate_physical_profile(
    player_name: str,
    position: str,
    height_pct: int,
    weight_pct: int,
    biometric_tags: list[str] | None,
    stats_dict: Dict[str, Any] | None,
) -> str:
    tags = biometric_tags or []
    tag_str = " / ".join(tags[:2]) if tags else "physical"
    pos_label = position or "Player"

    ppg = (stats_dict or {}).get("ppg")
    rpg = (stats_dict or {}).get("rpg")
    apg = (stats_dict or {}).get("apg")

    def _fmt(stat, label):
        try:
            return f"{float(stat):.1f} {label}"
        except Exception:
            return None

    ppg_s = _fmt(ppg, "PPG")
    rpg_s = _fmt(rpg, "RPG")
    apg_s = _fmt(apg, "APG")

    if ppg_s or rpg_s or apg_s:
        stat_phrase = ", ".join([s for s in [ppg_s, rpg_s, apg_s] if s])
        return f"A {height_pct}th %ile height {pos_label} with {tag_str} traits producing {stat_phrase}."

    return f"A {height_pct}th %ile height {pos_label} with {tag_str} traits."
