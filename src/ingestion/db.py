from __future__ import annotations

import os
import sqlite3


def project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def db_path() -> str:
    return os.path.join(project_root(), "data", "skout.db")


def connect_db() -> sqlite3.Connection:
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return sqlite3.connect(path)


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            season_id TEXT,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT,
            video_path TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS plays (
            play_id TEXT PRIMARY KEY,
            game_id TEXT,
            period INTEGER,
            clock_seconds INTEGER,
            clock_display TEXT,
            description TEXT,
            team_id TEXT,
            player_id TEXT,
            player_name TEXT,
            x_loc INTEGER,
            y_loc INTEGER,
            tags TEXT,
            FOREIGN KEY(game_id) REFERENCES games(game_id)
        )
        """
    )

    # Safe migrations for existing DBs missing new columns
    for col, ctype in [("player_id", "TEXT"), ("player_name", "TEXT")]:
        try:
            cur.execute(f"ALTER TABLE plays ADD COLUMN {col} {ctype}")
        except Exception:
            pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            team_id TEXT,
            first_name TEXT,
            last_name TEXT,
            full_name TEXT,
            position TEXT,
            height_in REAL,
            weight_lb REAL,
            class_year TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS player_traits (
            player_id TEXT PRIMARY KEY,
            player_name TEXT,
            dog_events INTEGER,
            total_events INTEGER,
            dog_index REAL,
            menace_index REAL,
            unselfish_index REAL,
            toughness_index REAL,
            rim_pressure_index REAL,
            shot_making_index REAL,
            size_index REAL
        )
        """
    )

    conn.commit()
