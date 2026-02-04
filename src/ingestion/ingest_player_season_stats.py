from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime

from src.ingestion.synergy_client import SynergyClient
from src.ingestion.db import db_path, connect_db, ensure_schema


PLAY_TYPES = [
    "Iso",
    "PostUp",
    "PandRBallHandler",
    "PandRRollMan",
    "Cut",
    "Transition",
    "SpotUp",
    "OffensiveRebound",
    "NoPlayType",
    "OffScreen",
    "HandOff",
]


def _coalesce_int(val):
    return int(val or 0)


def _coalesce_float(val):
    return float(val) if val is not None else None


def _aggregate_stats(target: dict, stats: dict):
    target["gp"] += _coalesce_int(stats.get("gp"))
    target["possessions"] += _coalesce_int(stats.get("possessions"))
    target["points"] += _coalesce_int(stats.get("points"))
    target["fg_made"] += _coalesce_int(stats.get("fgMade"))
    target["fg_miss"] += _coalesce_int(stats.get("fgMiss"))
    target["fg_attempt"] += _coalesce_int(stats.get("fgAttempt"))
    target["fg_percent_effective"] += _coalesce_float(stats.get("fgPercentEffective") or 0.0)
    target["shot2_made"] += _coalesce_int(stats.get("shot2Made"))
    target["shot2_miss"] += _coalesce_int(stats.get("shot2Miss"))
    target["shot2_attempt"] += _coalesce_int(stats.get("shot2Attempt"))
    target["shot3_made"] += _coalesce_int(stats.get("shot3Made"))
    target["shot3_miss"] += _coalesce_int(stats.get("shot3Miss"))
    target["shot3_attempt"] += _coalesce_int(stats.get("shot3Attempt"))
    target["ft_made"] += _coalesce_int(stats.get("ftMade"))
    target["ft_miss"] += _coalesce_int(stats.get("ftMiss"))
    target["ft_attempt"] += _coalesce_int(stats.get("ftAttempt"))
    target["plus_one"] += _coalesce_int(stats.get("plusOne"))
    target["shot_foul"] += _coalesce_int(stats.get("shotFoul"))
    target["score"] += _coalesce_int(stats.get("score"))
    target["turnover"] += _coalesce_int(stats.get("turnover"))


def _finalize(target: dict):
    fg_att = max(1, target["fg_attempt"])
    shot2_att = max(1, target["shot2_attempt"])
    shot3_att = max(1, target["shot3_attempt"])
    ft_att = max(1, target["ft_attempt"])

    target["fg_percent"] = round(target["fg_made"] / fg_att, 4)
    target["shot2_percent"] = round(target["shot2_made"] / shot2_att, 4)
    target["shot3_percent"] = round(target["shot3_made"] / shot3_att, 4)
    target["ft_percent"] = round(target["ft_made"] / ft_att, 4)

    # average eFG across play types (weighted by attempts)
    if target["fg_attempt"] > 0:
        target["fg_percent_effective"] = round(target["fg_percent_effective"] / len(PLAY_TYPES), 4)
    else:
        target["fg_percent_effective"] = None


def ingest_player_season_stats(league_code: str = "ncaamb", batch_limit: int | None = None) -> int:
    conn = connect_db()
    ensure_schema(conn)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT season_id FROM games WHERE season_id IS NOT NULL")
    seasons = [r[0] for r in cur.fetchall()]
    if not seasons:
        conn.close()
        raise RuntimeError("No season_id found in games table.")

    season_id = seasons[0]

    cur.execute("SELECT DISTINCT team_id FROM players WHERE team_id IS NOT NULL")
    team_ids = [r[0] for r in cur.fetchall()]
    if not team_ids:
        conn.close()
        raise RuntimeError("No team_id found in players table.")

    # Resume support: skip teams already processed for this season
    cur.execute(
        """
        SELECT DISTINCT team_id
        FROM player_season_stats
        WHERE season_id = ? AND team_id IS NOT NULL
        """,
        (season_id,),
    )
    done_team_ids = {r[0] for r in cur.fetchall()}
    pending_team_ids = [tid for tid in team_ids if tid not in done_team_ids]
    if batch_limit:
        pending_team_ids = pending_team_ids[: batch_limit]

    # Use current players list to filter
    cur.execute("SELECT DISTINCT player_id FROM players WHERE player_id IS NOT NULL")
    player_ids = {r[0] for r in cur.fetchall()}

    client = SynergyClient()

    agg = defaultdict(lambda: {
        "gp": 0,
        "possessions": 0,
        "points": 0,
        "fg_made": 0,
        "fg_miss": 0,
        "fg_attempt": 0,
        "fg_percent": None,
        "fg_percent_effective": 0.0,
        "shot2_made": 0,
        "shot2_miss": 0,
        "shot2_attempt": 0,
        "shot2_percent": None,
        "shot3_made": 0,
        "shot3_miss": 0,
        "shot3_attempt": 0,
        "shot3_percent": None,
        "ft_made": 0,
        "ft_miss": 0,
        "ft_attempt": 0,
        "ft_percent": None,
        "plus_one": 0,
        "shot_foul": 0,
        "score": 0,
        "turnover": 0,
        "team_id": None,
    })

    for team_id in pending_team_ids:
        for play_type in PLAY_TYPES:
            skip = 0
            while True:
                payload = client.get_player_playtype_stats(
                    league_code=league_code,
                    season_id=season_id,
                    play_type=play_type,
                    team_id=team_id,
                    skip=skip,
                    take=512,
                )
                data = None
                if isinstance(payload, dict):
                    data = payload.get("data") or payload.get("items")
                if not data:
                    break

                for item in data:
                    rec = item.get("data") if isinstance(item, dict) and "data" in item else item
                    if not isinstance(rec, dict):
                        continue
                    player = rec.get("player") or {}
                    pid = player.get("id")
                    if not pid or pid not in player_ids:
                        continue
                    stats = rec.get("stats") or {}
                    _aggregate_stats(agg[pid], stats)
                    agg[pid]["team_id"] = team_id

                if len(data) < 512:
                    break
                skip += 512

    updates = []
    now = datetime.utcnow().isoformat()
    for pid, s in agg.items():
        _finalize(s)
        updates.append(
            (
                pid,
                season_id,
                s.get("team_id"),
                s["gp"],
                s["possessions"],
                s["points"],
                s["fg_made"],
                s["fg_miss"],
                s["fg_attempt"],
                s["fg_percent"],
                s["fg_percent_effective"],
                s["shot2_made"],
                s["shot2_miss"],
                s["shot2_attempt"],
                s["shot2_percent"],
                s["shot3_made"],
                s["shot3_miss"],
                s["shot3_attempt"],
                s["shot3_percent"],
                s["ft_made"],
                s["ft_miss"],
                s["ft_attempt"],
                s["ft_percent"],
                s["plus_one"],
                s["shot_foul"],
                s["score"],
                s["turnover"],
                now,
            )
        )

    if updates:
        cur.executemany(
            """
            INSERT OR REPLACE INTO player_season_stats (
                player_id, season_id, team_id, gp, possessions, points,
                fg_made, fg_miss, fg_attempt, fg_percent, fg_percent_effective,
                shot2_made, shot2_miss, shot2_attempt, shot2_percent,
                shot3_made, shot3_miss, shot3_attempt, shot3_percent,
                ft_made, ft_miss, ft_attempt, ft_percent,
                plus_one, shot_foul, score, turnover, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            updates,
        )
        conn.commit()

    conn.close()
    return len(updates)


if __name__ == "__main__":
    count = ingest_player_season_stats()
    print(f"✅ player_season_stats updated for {count} players")
