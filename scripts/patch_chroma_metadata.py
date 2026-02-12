import os
import sqlite3

import chromadb

DB_PATH = os.path.join(os.getcwd(), "data/skout.db")
VECTOR_DB_PATH = os.path.join(os.getcwd(), "data/vector_db")


def main():
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_collection(name="skout_plays")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT player_id, position, height_in, weight_lb FROM players")
    rows = cur.fetchall()

    player_meta = {str(r[0]): (r[1], r[2], r[3]) for r in rows if r[0]}

    patched = 0
    offset = 0
    batch = 5000

    while True:
        res = collection.get(limit=batch, offset=offset, include=["metadatas"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        if not ids:
            break

        new_metas = []
        batch_changed = 0
        for pid, meta in zip(ids, metas):
            meta = meta or {}
            player_id = str(meta.get("player_id") or "")
            player_name = str(meta.get("player_name") or "")
            changed = False
            pos = h = w = None
            if player_id in player_meta:
                pos, h, w = player_meta[player_id]
            elif player_name:
                cur.execute('SELECT position, height_in, weight_lb FROM players WHERE full_name = ? LIMIT 1', (player_name,))
                row = cur.fetchone()
                if row:
                    pos, h, w = row
            if pos is not None:
                if meta.get("position") != pos:
                    meta["position"] = pos
                    changed = True
            if h is not None:
                if meta.get("height_in") != int(h):
                    meta["height_in"] = int(h)
                    changed = True
                if meta.get("height") != int(h):
                    meta["height"] = int(h)
                    changed = True
            if w is not None:
                if meta.get("weight_lb") != int(w):
                    meta["weight_lb"] = int(w)
                    changed = True
                if meta.get("weight") != int(w):
                    meta["weight"] = int(w)
                    changed = True
            if changed:
                batch_changed += 1
            new_metas.append(meta)

        if batch_changed:
            collection.update(ids=ids, metadatas=new_metas)
            patched += batch_changed

        offset += batch

    print(f"Patched {patched} records with Position data.")
    conn.close()


if __name__ == "__main__":
    main()
