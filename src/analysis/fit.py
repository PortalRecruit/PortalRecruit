from __future__ import annotations

import os
import sqlite3
from typing import Dict

from src.film import analyze_tendencies, clean_clip_text

DB_PATH = os.path.join(os.getcwd(), "data/skout.db")

SYSTEM_PROFILES = {
    "5-Out Motion": {
        "Catch & Shoot": 0.4,
        "Cut": 0.3,
        "Passing": 0.3,
        "Post-Up": -0.5,
    },
    "Traditional": {
        "Post-Up": 0.5,
        "Passing": 0.2,
        "Catch & Shoot": 0.1,
        "Cut": 0.1,
    },
    "Triangle": {
        "Post-Up": 0.5,
        "Passing": 0.3,
        "Cut": 0.2,
    },
}


def _load_player_clips(player_id: str, limit: int = 80) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT description FROM plays WHERE player_id = ? ORDER BY utc DESC LIMIT ?",
        (player_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [clean_clip_text(r[0]) for r in rows if r and r[0]]


def _tendency_vector(player_id: str) -> Dict[str, float]:
    clips = _load_player_clips(player_id)
    tendencies = analyze_tendencies(clips)
    totals = {k: float(v) for k, v in tendencies.items()}

    extra = {"Post-Up": 0, "Cut": 0, "Passing": 0}
    for clip in clips:
        txt = clip.lower()
        if "post-up" in txt or "post up" in txt or "left shoulder" in txt or "right shoulder" in txt:
            extra["Post-Up"] += 1
        if "cut" in txt:
            extra["Cut"] += 1
        if "assist" in txt or "pass" in txt:
            extra["Passing"] += 1

    for k, v in extra.items():
        if v > 0:
            totals[k] = totals.get(k, 0) + v

    total_actions = sum(totals.values()) or 1
    return {k: (v / total_actions) for k, v in totals.items()}


def calculate_system_fit(player_id: str, system_profile: dict) -> float:
    vec = _tendency_vector(player_id)
    score = 50.0
    for trait, weight in system_profile.items():
        score += weight * (vec.get(trait, 0.0) * 100)
    return max(0.0, min(100.0, score))


def grade_fit(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"
