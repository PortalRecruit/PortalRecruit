#!/usr/bin/env python3
"""Verify ACC team coverage for 2021-22 season in local DB."""
from __future__ import annotations

import sqlite3

ACC_2021_22 = {
    "BostonCollege",
    "Clemson",
    "Duke",
    "FloridaState",
    "GeorgiaTech",
    "Louisville",
    "MiamiFL",
    "NorthCarolina",
    "NorthCarolinaState",
    "NotreDame",
    "Pittsburgh",
    "Syracuse",
    "Virginia",
    "VirginiaTech",
    "WakeForest",
}

SEASON_ID = "6085b5d0e6c2413bc4ba9122"


def main() -> int:
    conn = sqlite3.connect("data/skout.db")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT home_team FROM games WHERE season_id = ?
        UNION
        SELECT DISTINCT away_team FROM games WHERE season_id = ?
        ORDER BY 1
        """,
        (SEASON_ID, SEASON_ID),
    )
    teams = {r[0] for r in cur.fetchall()}
    conn.close()

    missing = sorted(ACC_2021_22 - teams)
    extra = sorted(teams - ACC_2021_22)

    if missing:
        print("❌ Missing ACC teams:")
        for t in missing:
            print(f" - {t}")
        return 1

    print("✅ ACC 2021-22 coverage complete.")
    print(f"DB teams total in season: {len(teams)}")
    print(f"ACC teams present: {len(ACC_2021_22)}")

    # Show non-ACC teams (context)
    print("\nNon-ACC teams present (sample):")
    for t in extra[:25]:
        print(f" - {t}")
    if len(extra) > 25:
        print(f" ... +{len(extra)-25} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
