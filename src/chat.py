from __future__ import annotations

import chromadb
from src.search.semantic import semantic_search
from src.archetypes import assign_archetypes
from src.narrative import generate_physical_profile
from src.position_calibration import calculate_percentile
import sqlite3
import pandas as pd
import re
from typing import Literal

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


def detect_intent(query: str) -> tuple[Literal["stat", "semantic"], str | None]:
    q = (query or "").lower()
    stat_triggers = ["most", "highest", "best", "leader", "top"]
    metric_map = {
        "ppg": ["ppg", "points", "scoring"],
        "rpg": ["rpg", "rebounds", "rebounding"],
        "apg": ["apg", "assists", "playmaking"],
        "3pt": ["3pt", "3-point", "3 point", "three point", "threes", "3s"],
    }
    has_trigger = any(t in q for t in stat_triggers)
    metric = None
    for key, keywords in metric_map.items():
        if any(k in q for k in keywords):
            metric = key
            break
    if has_trigger and metric:
        return "stat", metric
    return "semantic", None


def _resolve_metric_column(df: pd.DataFrame, metric: str) -> str | None:
    candidates = {
        "ppg": ["ppg", "points_per_game", "points"],
        "rpg": ["rpg", "rebounds_per_game", "rebounds"],
        "apg": ["apg", "assists_per_game", "assists"],
        "3pt": ["3pt", "three_pt", "three_pt_pct", "3p", "3pt_pct"],
    }
    for col in candidates.get(metric, []):
        if col in df.columns:
            return col
        for c in df.columns:
            if c.lower() == col:
                return c
    return None


def _detect_position_filter(query: str) -> str | None:
    q = (query or "").lower()
    if "guard" in q or re.search(r"\bgs?\b", q):
        return "G"
    if "forward" in q or re.search(r"\bfs?\b", q):
        return "F"
    if "center" in q or re.search(r"\bcs?\b", q):
        return "C"
    if "wing" in q:
        return "W"
    return None


def get_stat_leaders(metric: str, count: int = 5, filter_pos: str | None = None) -> list[dict]:
    try:
        df = pd.read_csv("data/full_training_set.csv")
    except Exception:
        df = None
    if df is not None:
        metric_col = _resolve_metric_column(df, metric)
        pos_col = next((c for c in ["position", "pos", "true_position"] if c in df.columns), None)
        name_col = next((c for c in ["player_name", "name", "full_name"] if c in df.columns), None)
        if metric_col and name_col:
            if filter_pos and pos_col:
                df = df[df[pos_col].astype(str).str.upper().str.contains(filter_pos)]
            df = df.dropna(subset=[metric_col])
            df = df.sort_values(metric_col, ascending=False).head(count)
            leaders = []
            for _, row in df.iterrows():
                leaders.append({
                    "name": str(row.get(name_col, "Unknown")),
                    "value": row.get(metric_col),
                    "position": row.get(pos_col) if pos_col else None,
                })
            if leaders:
                return leaders

    metric_map = {"ppg": "ppg", "rpg": "rpg", "apg": "apg", "3pt": "three_pt_pct"}
    metric_col = metric_map.get(metric)
    if not metric_col:
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(player_season_stats)")
        columns = [row[1] for row in cur.fetchall()]
        if metric_col not in columns:
            conn.close()
            return []
        where_clauses = ["rn = 1"]
        params: list = []
        if filter_pos:
            where_clauses.append("position LIKE ?")
            params.append(f"%{filter_pos}%")
        where_sql = "WHERE " + " AND ".join(where_clauses)
        query = f"""
            SELECT full_name, position, metric_value FROM (
                SELECT p.full_name AS full_name,
                       p.position AS position,
                       s.{metric_col} AS metric_value,
                       ROW_NUMBER() OVER (PARTITION BY s.player_id ORDER BY s.season_id DESC) AS rn
                FROM player_season_stats s
                JOIN players p ON s.player_id = p.player_id
            ) sub
            {where_sql}
            ORDER BY metric_value DESC
            LIMIT ?
        """
        params.append(count)
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
    except Exception:
        return []
    leaders = []
    for name, pos, val in rows:
        leaders.append({"name": name, "value": val, "position": pos})
    return leaders


def ask_scout(user_question: str) -> str:
    query = (user_question or "").strip()
    if not query:
        return "Ask me about a player trait or archetype (e.g., 'best rebounder')."

    intent, metric = detect_intent(query)
    if intent == "stat" and metric:
        pos_filter = _detect_position_filter(query)
        leaders = get_stat_leaders(metric, count=5, filter_pos=pos_filter)
        print(f"Intent: STAT (Metric: {metric})")
        if not leaders:
            return f"Stat leaders not available for '{metric}'."
        metric_label = metric.upper()
        lines = [f"Here are the top 5 in {metric_label}:"]
        for idx, row in enumerate(leaders, start=1):
            val = row.get("value")
            try:
                val_str = f"{float(val):.1f}"
            except Exception:
                val_str = str(val)
            lines.append(f"{idx}. {row.get('name')} ({val_str})")
        return "\n".join(lines)

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
