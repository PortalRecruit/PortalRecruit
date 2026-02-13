from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List

DB_PATH = os.path.join(os.getcwd(), "data/skout.db")
TEAM_PATH = os.path.join(os.getcwd(), "data/my_team.json")


def _load_team() -> list[dict]:
    if not os.path.exists(TEAM_PATH):
        return []
    try:
        with open(TEAM_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_team(team: list[dict]) -> None:
    os.makedirs(os.path.dirname(TEAM_PATH), exist_ok=True)
    with open(TEAM_PATH, "w", encoding="utf-8") as f:
        json.dump(team, f, indent=2)


def _get_profile_by_name(name: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT player_id, full_name, position, team_id, height_in, weight_lb, class_year FROM players WHERE LOWER(full_name) = LOWER(?) LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    player_id = row[0]
    profile = {
        "player_id": row[0],
        "name": row[1],
        "position": row[2],
        "team": row[3],
        "height_in": row[4],
        "weight_lb": row[5],
        "class_year": row[6],
    }
    cur.execute(
        """
        SELECT ppg, rpg, apg, shot3_percent
        FROM player_season_stats
        WHERE player_id = ?
        ORDER BY season_id DESC
        LIMIT 1
        """,
        (player_id,),
    )
    stats = cur.fetchone()
    conn.close()
    if stats:
        profile.update({
            "ppg": stats[0],
            "rpg": stats[1],
            "apg": stats[2],
            "three_pt_pct": stats[3],
        })
    return profile


def add_to_team(player: dict | str) -> bool:
    team = _load_team()
    if isinstance(player, str):
        profile = _get_profile_by_name(player)
        if not profile:
            return False
        player = profile
    player_id = player.get("player_id") or player.get("name")
    if any((p.get("player_id") or p.get("name")) == player_id for p in team):
        return False
    team.append(player)
    _save_team(team)
    return True


def remove_from_team(player_id: str) -> bool:
    team = _load_team()
    filtered = [p for p in team if (p.get("player_id") or p.get("name")) != player_id]
    if len(filtered) == len(team):
        return False
    _save_team(filtered)
    return True


def get_team() -> list[dict]:
    return _load_team()


def set_team(team: list[dict]) -> None:
    _save_team(team)


def _avg(values: list[float]) -> float | None:
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals:
        return None
    return sum(vals) / len(vals)


def get_team_averages() -> dict:
    team = _load_team()
    return {
        "count": len(team),
        "height_in": _avg([p.get("height_in") for p in team]),
        "weight_lb": _avg([p.get("weight_lb") for p in team]),
        "ppg": _avg([p.get("ppg") for p in team]),
        "rpg": _avg([p.get("rpg") for p in team]),
        "apg": _avg([p.get("apg") for p in team]),
        "three_pt_pct": _avg([p.get("three_pt_pct") for p in team]),
        "avg_age": None,
    }


def calculate_impact(target_player_stats: dict, current_team_averages: dict) -> dict:
    count = current_team_averages.get("count") or 0
    if count <= 0:
        return {}

    def _new_avg(metric: str) -> float | None:
        current_avg = current_team_averages.get(metric)
        target_val = target_player_stats.get(metric)
        if current_avg is None or target_val is None:
            return None
        return (current_avg * count + target_val) / (count + 1)

    impact = {}
    for metric in ["height_in", "weight_lb", "ppg", "rpg", "apg", "three_pt_pct"]:
        new_avg = _new_avg(metric)
        current_avg = current_team_averages.get(metric)
        if new_avg is None or current_avg is None:
            continue
        impact[f"{metric}_diff"] = new_avg - current_avg
        impact[f"{metric}_new"] = new_avg
    return impact


def audit_roster_balance(my_team_list: list[dict]) -> list[str]:
    alerts: list[str] = []
    counts = {"G": 0, "F": 0, "C": 0}
    for p in my_team_list:
        pos = str(p.get("position") or "").upper()
        if "G" in pos:
            counts["G"] += 1
        if "F" in pos:
            counts["F"] += 1
        if "C" in pos:
            counts["C"] += 1
    if counts["G"] > 5:
        alerts.append("⚠️ Too many Guards on roster.")
    if counts["C"] == 0:
        alerts.append("🚨 Needs Size: No Centers on roster.")
    return alerts
