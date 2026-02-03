#!/usr/bin/env python3
"""Incremental ingest using only API-accessible data.

Goals:
- Discover what the trial API key can access (seasons/teams/games)
- Only fetch data that is NOT already in the local DB
- Rebuild traits/embeddings after ingest (optional)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

from src.ingestion.db import connect_db, ensure_schema, db_path
from src.ingestion.pipeline import (
    _unwrap_list_payload,
    iter_games,
    upsert_games,
    upsert_players,
    upsert_plays,
)
from src.ingestion.synergy_client import SynergyClient


def pick_latest_season_id(seasons: list[dict]) -> str | None:
    if not seasons:
        return None

    def score(s: dict) -> int:
        for key in ("year", "seasonYear", "startYear", "endYear"):
            val = s.get(key)
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
        for key in ("name", "id", "seasonId"):
            val = s.get(key)
            if isinstance(val, str):
                m = re.findall(r"\d{4}", val)
                if m:
                    return int(m[-1])
        return 0

    seasons_sorted = sorted(seasons, key=score, reverse=True)
    for s in seasons_sorted:
        for key in ("id", "seasonId", "seasonID"):
            if s.get(key):
                return str(s.get(key))
    return None


def reset_local_dbs(root: Path) -> None:
    db = Path(db_path())
    if db.exists():
        db.unlink()
        print(f"🗑️  Deleted {db}")

    vector_db = root / "data" / "vector_db"
    if vector_db.exists():
        shutil.rmtree(vector_db)
        print(f"🗑️  Deleted {vector_db}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="ncaamb")
    parser.add_argument("--season", default="", help="Season ID to ingest (default: all accessible)")
    parser.add_argument("--reset", action="store_true", help="Delete local DB + vector store before ingest")
    parser.add_argument("--skip-embeddings", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    os.chdir(root)

    print("🔎 Checking API access...")
    client = SynergyClient()
    seasons_payload = client.get_seasons(args.league)
    seasons = [s for s in _unwrap_list_payload(seasons_payload) if isinstance(s, dict)]
    if not seasons:
        print(f"❌ No seasons available (status={client.last_status_code}, err={client.last_error})")
        return 1

    if args.season:
        season_ids = [str(args.season)]
    else:
        # Use all accessible seasons (trial scope)
        season_ids = []
        for s in seasons:
            for key in ("id", "seasonId", "seasonID"):
                if s.get(key):
                    season_ids.append(str(s.get(key)))
                    break
        if not season_ids:
            latest = pick_latest_season_id(seasons)
            if latest:
                season_ids = [latest]

    if not season_ids:
        print("❌ Unable to determine any season_id from API.")
        return 1

    if args.reset:
        reset_local_dbs(root)

    conn = connect_db()
    ensure_schema(conn)
    cur = conn.cursor()

    total_new_games = 0
    total_new_plays = 0

    for season_id in season_ids:
        teams_payload = client.get_teams(args.league, season_id)
        teams = [t for t in _unwrap_list_payload(teams_payload) if isinstance(t, dict)]
        team_ids = [t.get("id") for t in teams if t.get("id")]

        if not team_ids:
            print(f"⚠️  No teams accessible for season {season_id}")
            continue

        # Existing games for this season
        cur.execute("SELECT game_id FROM games WHERE season_id = ?", (season_id,))
        existing_game_ids = {r[0] for r in cur.fetchall()}

        print(f"✅ Season {season_id} | teams: {len(team_ids)} | existing games: {len(existing_game_ids)}")

        # Fetch games by team, but only keep those not in DB
        new_games: dict[str, dict] = {}
        for tid in team_ids:
            for g in iter_games(client, args.league, season_id, tid):
                gid = g.get("id")
                if not gid or gid in existing_game_ids or gid in new_games:
                    continue
                new_games[gid] = g

        if new_games:
            inserted = upsert_games(conn, season_id, list(new_games.values()))
            total_new_games += inserted
        else:
            print(f"ℹ️  No new games for season {season_id}")

        # Players: only fetch if team missing in DB
        for tid in team_ids:
            cur.execute("SELECT 1 FROM players WHERE team_id = ? LIMIT 1", (tid,))
            if cur.fetchone():
                continue
            payload = client.get_team_players(args.league, tid)
            players = [p for p in _unwrap_list_payload(payload) if isinstance(p, dict)]
            if players:
                upsert_players(conn, tid, players)

        # Events: only for newly added games
        if new_games:
            for idx, gid in enumerate(new_games.keys()):
                if idx % 10 == 0:
                    print(f"   events {idx}/{len(new_games)}")
                payload = client.get_game_events(args.league, gid)
                if not payload:
                    continue
                events = [e for e in _unwrap_list_payload(payload) if isinstance(e, dict)]
                total_new_plays += upsert_plays(conn, gid, events)

    conn.close()

    print(f"✅ New games: {total_new_games} | New plays: {total_new_plays}")

    # Backfill player names
    try:
        from scripts.backfill_player_names import main as backfill_names
        backfill_names()
    except Exception as e:
        print(f"⚠️ Backfill failed: {e}")

    # Rebuild traits (post-backfill)
    try:
        from src.processing.derive_player_traits import build_player_traits
        build_player_traits()
    except Exception as e:
        print(f"⚠️ Trait build failed: {e}")

    if not args.skip_embeddings:
        try:
            from src.processing.generate_embeddings import generate_embeddings
            generate_embeddings()
        except Exception as e:
            print(f"⚠️ Embeddings failed: {e}")

    print("✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
