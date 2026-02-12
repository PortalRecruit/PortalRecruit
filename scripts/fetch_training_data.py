import csv
import os
import sqlite3

import chromadb

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

VECTOR_DB_PATH = os.path.join(os.getcwd(), "data/vector_db")
DB_PATH = os.path.join(os.getcwd(), "data/skout.db")
OUTPUT_PATH = os.path.join(os.getcwd(), "data/full_training_set.csv")


def _iter_collection(collection, batch_size: int = 5000):
    offset = 0
    while True:
        res = collection.get(limit=batch_size, offset=offset, include=["metadatas", "documents"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        docs = res.get("documents") or []
        if not ids:
            break
        for meta, doc in zip(metas, docs):
            yield meta or {}, (doc or "")
        offset += batch_size


def main():
    client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
    collection = client.get_collection(name="skout_plays")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT player_id, full_name, position, height_in, weight_lb FROM players")
    rows = cur.fetchall()
    player_meta = {str(r[0]): (r[1], r[2], r[3], r[4]) for r in rows if r[0]}

    total = None
    try:
        total = collection.count()
    except Exception:
        total = None

    records = _iter_collection(collection)
    if tqdm and total:
        records = tqdm(records, total=total, desc="Harvesting plays")
    elif tqdm:
        records = tqdm(records, desc="Harvesting plays")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["player_name", "true_position", "height_in", "weight_lb", "text"])
        for meta, doc in records:
            player_id = str(meta.get("player_id") or "")
            player_name = meta.get("player_name") or meta.get("player") or ""
            position = meta.get("position") or ""
            height = meta.get("height_in") or meta.get("height")
            weight = meta.get("weight_lb") or meta.get("weight")

            if player_id and player_id in player_meta:
                name, pos, h, w = player_meta[player_id]
                player_name = player_name or name
                position = position or pos
                height = height or h
                weight = weight or w
            elif player_name:
                cur.execute(
                    "SELECT position, height_in, weight_lb FROM players WHERE full_name = ? LIMIT 1",
                    (player_name,),
                )
                row = cur.fetchone()
                if row:
                    position = position or row[0]
                    height = height or row[1]
                    weight = weight or row[2]

            text = meta.get("original_desc") or doc or ""
            writer.writerow([player_name, position, height, weight, text])

    conn.close()


if __name__ == "__main__":
    main()
