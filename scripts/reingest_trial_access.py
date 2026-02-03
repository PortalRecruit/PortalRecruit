#!/usr/bin/env python3
"""Rebuild local DBs using only what the trial API key can access.

Flow:
1) API access check (seasons + teams)
2) Optional reset of local DB + vector store
3) Ingest all accessible teams for the selected season
4) Backfill player names, rebuild traits, regenerate embeddings
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

from src.ingestion.synergy_client import SynergyClient
from src.ingestion.pipeline import PipelinePlan, run_pipeline, _unwrap_list_payload
from src.ingestion.db import db_path


def pick_season_id(seasons: list[dict]) -> str | None:
    if not seasons:
        return None

    # Try common fields to pick the latest season
    def score(s: dict) -> int:
        for key in ("year", "seasonYear", "startYear", "endYear"):
            val = s.get(key)
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
        # fallback: extract digits from name or id
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
    parser.add_argument("--season", default="")
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

    season_id = args.season or pick_season_id(seasons)
    if not season_id:
        print("❌ Unable to determine season_id from API.")
        return 1

    teams_payload = client.get_teams(args.league, season_id)
    teams = [t for t in _unwrap_list_payload(teams_payload) if isinstance(t, dict)]
    team_ids = [t.get("id") for t in teams if t.get("id")]
    if not team_ids:
        print(f"❌ No teams accessible for season {season_id} (status={client.last_status_code}, err={client.last_error})")
        return 1

    # Quick games check to verify access
    _ = client.get_games(args.league, season_id, team_ids[0], limit=1)
    if client.last_status_code and client.last_status_code >= 400:
        print(f"❌ Games access failed (status={client.last_status_code}, err={client.last_error})")
        return 1

    print(f"✅ Access OK. Season: {season_id} | Teams: {len(team_ids)}")

    if args.reset:
        reset_local_dbs(root)

    # Ingest all accessible teams for the season
    plan = PipelinePlan(league_code=args.league, season_id=str(season_id), team_ids=[str(t) for t in team_ids])
    print("🚚 Running ingestion pipeline...")
    run_pipeline(plan, api_key=os.getenv("SYNERGY_API_KEY"))

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
