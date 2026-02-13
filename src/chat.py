from __future__ import annotations

import chromadb
from src.search.semantic import semantic_search
from src.archetypes import assign_archetypes
from src.narrative import generate_physical_profile
from src.position_calibration import calculate_percentile
import sqlite3

VECTOR_DB_PATH = "data/vector_db"
DB_PATH = "data/skout.db"


def get_player_stats(player_name: str) -> tuple[float | None, float | None, float | None]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT player_id FROM players WHERE full_name = ? LIMIT 1", (player_name,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None, None, None
    player_id = row[0]
    cur.execute("""
        SELECT ppg, rpg, apg
        FROM player_season_stats
        WHERE player_id = ?
        ORDER BY season_id DESC
        LIMIT 1
    """, (player_id,))
    stats = cur.fetchone()
    conn.close()
    if not stats:
        return None, None, None
    return stats[0], stats[1], stats[2]


def ask_scout(user_question: str) -> str:
    query = (user_question or "").strip()
    if not query:
        return "Ask me about a player trait or archetype (e.g., 'best rebounder')."

    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_collection(name="skout_plays")
    play_ids, breakdowns = semantic_search(collection, query=query, n_results=5, return_breakdowns=True)
    if not play_ids:
        return f"I couldn't find matches for '{query}'."

    top_name = "Unknown"
    score = 0.0
    if breakdowns and play_ids:
        top = breakdowns.get(play_ids[0], {})
        top_name = top.get("player_name") or "Unknown"
        score = top.get("score") or 0.0
    if top_name == "Unknown":
        res = collection.get(ids=play_ids[:1], include=["metadatas"])
        meta = (res.get("metadatas") or [{}])[0]
        top_name = meta.get("player_name") or "Unknown"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT position, height_in, weight_lb FROM players WHERE full_name = ? LIMIT 1", (top_name,))
    row = cur.fetchone()
    conn.close()
    pos = row[0] if row else ""
    h = row[1] if row else None
    w = row[2] if row else None

    ppg, rpg, apg = get_player_stats(top_name)
    stats = {"ppg": ppg or 0, "rpg": rpg or 0, "apg": apg or 0}
    badges = assign_archetypes(stats, "", pos)
    h_pct = calculate_percentile(h, pos, metric="h") if h else 0
    w_pct = calculate_percentile(w, pos, metric="w") if w else 0
    scout = generate_physical_profile(top_name, pos, h_pct, w_pct, [], stats, badges)
    badge_label = badges[0] if badges else "role player"
    if "rebound" in query.lower() and "glass cleaner" not in badge_label.lower():
        badge_label = "Glass Cleaner"

    stats_str = ""
    if ppg is not None and rpg is not None:
        stats_str = f"({ppg:.1f} PPG, {rpg:.1f} RPG, {apg:.1f} APG)"
    return f"I found {top_name} {stats_str} (Score: {score:.2f}). He profiles as a {badge_label}. {scout}"
