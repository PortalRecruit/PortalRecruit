import sqlite3
import re
import hashlib
from pathlib import Path

DB = Path("data/skout.db")


def make_id(name: str) -> str:
    return hashlib.md5(name.encode("utf-8")).hexdigest()[:12]


def extract_name(desc: str):
    if not desc:
        return None
    first = desc.split(">")[0].strip()  # e.g. "5 Yuri Covington"
    first = re.sub(r"^\d+\s+", "", first)  # strip jersey number
    return first.strip() if first else None


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT play_id, description FROM plays WHERE (player_name IS NULL OR player_name = '')")
    rows = cur.fetchall()
    print(f"Backfilling {len(rows)} plays...")

    updated = 0
    for play_id, desc in rows:
        name = extract_name(desc)
        if not name:
            continue
        pid = make_id(name)
        cur.execute(
            "UPDATE plays SET player_name = ?, player_id = ? WHERE play_id = ?",
            (name, pid, play_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"✅ Updated {updated} plays")


if __name__ == "__main__":
    main()
