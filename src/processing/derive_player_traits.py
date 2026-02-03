import os
import sqlite3

DB_PATH = os.path.join(os.getcwd(), "data/skout.db")

# Simple keyword-based proxies until we have richer event typing
DOG_KEYWORDS = [
    "offensive rebound", "off. rebound", "oreb",
    "steal", "block", "charge", "loose ball", "dive"
]


def _count_keywords(desc: str, keywords: list[str]) -> int:
    if not desc:
        return 0
    d = desc.lower()
    return sum(1 for k in keywords if k in d)


def build_player_traits():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create table to store traits (idempotent)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS player_traits (
            player_id TEXT PRIMARY KEY,
            player_name TEXT,
            dog_events INTEGER,
            total_events INTEGER,
            dog_index REAL
        )
        """
    )

    # Pull plays with player_id
    cur.execute(
        """
        SELECT player_id, player_name, description
        FROM plays
        WHERE player_id IS NOT NULL
        """
    )
    rows = cur.fetchall()

    # Aggregate counts in Python (simple + fast enough for now)
    agg = {}
    for player_id, player_name, desc in rows:
        if player_id not in agg:
            agg[player_id] = {
                "player_name": player_name,
                "dog_events": 0,
                "total_events": 0,
            }
        agg[player_id]["total_events"] += 1
        agg[player_id]["dog_events"] += _count_keywords(desc, DOG_KEYWORDS)

    # Compute dog_index and persist
    # dog_index = dog_events / total_events (scaled 0-100)
    for pid, data in agg.items():
        total = max(1, data["total_events"])
        dog_score = data["dog_events"] / total
        dog_index = round(dog_score * 100, 3)

        cur.execute(
            """
            INSERT OR REPLACE INTO player_traits
            (player_id, player_name, dog_events, total_events, dog_index)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pid, data["player_name"], data["dog_events"], data["total_events"], dog_index),
        )

    conn.commit()
    conn.close()
    print(f"✅ player_traits updated for {len(agg)} players")


if __name__ == "__main__":
    build_player_traits()
