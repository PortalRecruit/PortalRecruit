import os
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "skout.db"
VECTOR_DB_PATH = REPO_ROOT / "data" / "vector_db"
CHROMA_SQLITE = VECTOR_DB_PATH / "chroma.sqlite3"

def print_header(title):
    print("\n" + "="*80)
    print(title)
    print("="*80)

def db_query(conn, q, params=()):
    cur = conn.cursor()
    cur.execute(q, params)
    return cur.fetchall()

def main():
    print_header("DB AUDIT: skout.db + Chroma")
    print(f"DB_PATH: {DB_PATH} ({'exists' if DB_PATH.exists() else 'MISSING'})")
    print(f"CHROMA_SQLITE: {CHROMA_SQLITE} ({'exists' if CHROMA_SQLITE.exists() else 'MISSING'})")

    if not DB_PATH.exists():
        print("❌ skout.db not found. Exiting.")
        return

    conn = sqlite3.connect(DB_PATH)

    # 1) Schema
    print_header("TABLE SCHEMAS")
    tables = db_query(conn, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for (tname,) in tables:
        print(f"\n-- {tname} --")
        cols = db_query(conn, f"PRAGMA table_info({tname})")
        for c in cols:
            # (cid, name, type, notnull, dflt_value, pk)
            print(f"  {c[1]:20s} {c[2]:10s} pk={c[5]}")

    # 2) Row counts
    print_header("ROW COUNTS")
    for (tname,) in tables:
        try:
            count = db_query(conn, f"SELECT COUNT(*) FROM {tname}")[0][0]
            print(f"{tname:20s} {count}")
        except Exception as e:
            print(f"{tname:20s} ERROR: {e}")

    # 3) Plays coverage
    print_header("PLAYS COVERAGE")
    try:
        total_plays = db_query(conn, "SELECT COUNT(*) FROM plays")[0][0]
        with_player = db_query(conn, "SELECT COUNT(*) FROM plays WHERE player_id IS NOT NULL")[0][0]
        print(f"Total plays: {total_plays}")
        print(f"Plays with player_id: {with_player} ({(with_player/total_plays*100 if total_plays else 0):.2f}%)")
    except Exception as e:
        print(f"Plays coverage ERROR: {e}")

    # 4) Sample rows
    print_header("SAMPLE PLAYS (5)")
    try:
        rows = db_query(conn, "SELECT play_id, player_name, description, clock_display FROM plays LIMIT 5")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Sample plays ERROR: {e}")

    print_header("SAMPLE GAMES (5)")
    try:
        rows = db_query(conn, "SELECT game_id, home_team, away_team, home_score, away_score FROM games LIMIT 5")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Sample games ERROR: {e}")

    # 5) Traits coverage (if table exists)
    print_header("PLAYER TRAITS")
    try:
        traits = db_query(conn, "SELECT COUNT(*) FROM player_traits")[0][0]
        print(f"player_traits rows: {traits}")
        rows = db_query(conn, "SELECT player_name, dog_index, dog_events, total_events FROM player_traits ORDER BY dog_index DESC LIMIT 5")
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Player traits ERROR: {e}")

    conn.close()

    # 6) Chroma presence
    print_header("CHROMA CHECK")
    if CHROMA_SQLITE.exists():
        print("✅ Chroma sqlite exists. Vector DB likely built.")
    else:
        print("❌ Chroma sqlite missing. Run generate_embeddings.py")

if __name__ == "__main__":
    main()
