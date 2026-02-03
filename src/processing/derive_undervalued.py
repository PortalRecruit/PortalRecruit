from __future__ import annotations

import sqlite3
from collections import defaultdict

from src.processing.play_tagger import tag_play
from src.ingestion.db import db_path


def build_undervalued_metrics() -> None:
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()

    cur.execute(
        """
        SELECT player_id, description, duration
        FROM plays
        WHERE player_id IS NOT NULL
        """
    )
    rows = cur.fetchall()

    if not rows:
        conn.close()
        return

    stats = defaultdict(lambda: {
        "total": 0,
        "made": 0,
        "assist": 0,
        "turnover": 0,
        "duration_sum": 0.0,
    })

    for player_id, desc, duration in rows:
        tags = tag_play(desc or "")
        made_or_score = "made" in tags or "score" in tags
        turnover = "turnover" in tags
        assist = "assist" in tags

        s = stats[player_id]
        s["total"] += 1
        if made_or_score:
            s["made"] += 1
        if assist:
            s["assist"] += 1
        if turnover:
            s["turnover"] += 1
        if duration:
            s["duration_sum"] += float(duration)

    updates = []
    for pid, s in stats.items():
        total = max(1, s["total"])
        make_rate = s["made"] / total
        assist_rate = s["assist"] / total
        turnover_rate = s["turnover"] / total
        avg_duration = s["duration_sum"] / total if total else 0

        low_touch = 1.0 / max(1.0, avg_duration)
        high_yield = make_rate + assist_rate
        low_usage_turnover_rate = turnover_rate

        undervalued = (
            2.2 * high_yield
            + 1.5 * low_touch
            - 1.8 * low_usage_turnover_rate
        )

        updates.append(
            (
                undervalued,
                low_touch,
                high_yield,
                low_usage_turnover_rate,
                pid,
            )
        )

    cur.executemany(
        """
        UPDATE player_traits
        SET undervalued_index = ?,
            low_touch_score = ?,
            high_yield_score = ?,
            low_usage_turnover_rate = ?
        WHERE player_id = ?
        """,
        updates,
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    build_undervalued_metrics()
