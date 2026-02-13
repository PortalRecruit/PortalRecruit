from __future__ import annotations

from typing import Dict


POWER_6 = {
    "acc",
    "big 12",
    "big12",
    "big ten",
    "big10",
    "sec",
    "pac-12",
    "pac 12",
    "pac12",
    "big east",
}


def estimate_nil_value_amount(player_row: Dict) -> float:
    ppg = float(player_row.get("ppg") or 0)
    rpg = float(player_row.get("rpg") or 0)
    apg = float(player_row.get("apg") or 0)
    base = 10000 + (1500 * ppg) + (1000 * rpg) + (2000 * apg)

    conference = str(player_row.get("conference") or "").lower().strip()
    power6 = any(key in conference for key in POWER_6)
    if power6:
        base *= 1.5

    games_started = player_row.get("games_started") or player_row.get("gs") or 0
    try:
        gs_val = float(games_started)
    except Exception:
        gs_val = 0
    if gs_val > 20:
        base *= 1.2

    return base


def estimate_nil_value(player_row: Dict) -> str:
    base = estimate_nil_value_amount(player_row)
    low = base * 0.92
    high = base * 1.05

    def _fmt(val: float) -> str:
        if val >= 1_000_000:
            return f"${val/1_000_000:.2f}M"
        return f"${val/1000:.0f}k"

    return f"{_fmt(low)} - {_fmt(high)}"
