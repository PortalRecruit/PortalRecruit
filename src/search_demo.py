import os
import sqlite3

import chromadb
from sentence_transformers import SentenceTransformer

from src.processing.play_tagger import tag_play

VECTOR_DB_PATH = os.path.join(os.getcwd(), "data/vector_db")
DB_PATH = os.path.join(os.getcwd(), "data/skout.db")

CLIENT = chromadb.PersistentClient(path=VECTOR_DB_PATH)
COLLECTION = CLIENT.get_collection(name="skout_plays")
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def _enrich_query(query: str) -> str:
    tags = tag_play(query)
    if not tags:
        return query
    return f"{query} [Tags: {', '.join(tags)}]"


def search_plays(query, n_results=5):
    # 1. Search the Vector DB
    query_text = _enrich_query(query)
    query_embedding = MODEL.encode([query_text], normalize_embeddings=True).tolist()
    results = COLLECTION.query(query_embeddings=query_embedding, n_results=n_results)
    
    # 2. Correlate with SQL DB to get Video Path
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"\n🔍 Search Results for: '{query}'")
    print("-" * 50)
    
    if not results["ids"][0]:
        print("No results found.")
        return

    for i, play_id in enumerate(results["ids"][0]):
        desc = results['metadatas'][0][i]['original_desc']
        tags = results['metadatas'][0][i]['tags']
        clock = results['metadatas'][0][i]['clock']
        game_id = results['metadatas'][0][i]['game_id']
        
        # Get Video Path
        cursor.execute("SELECT video_path, home_team, away_team FROM games WHERE game_id = ?", (game_id,))
        game_row = cursor.fetchone()
        
        if game_row:
            v_path = os.path.basename(game_row[0]) if game_row[0] else "No Video"
            matchup = f"{game_row[1]} vs {game_row[2]}"
        else:
            v_path = "Unknown"
            matchup = "Unknown"

        print(f"[{i+1}] {matchup} @ {clock}")
        print(f"    Play: {desc}")
        print(f"    Tags: [{tags}]")
        print(f"    File: {v_path}")
        print("")

if __name__ == "__main__":
    while True:
        q = input("Enter search query (or 'q' to quit): ")
        if q.lower() == "q":
            break
        search_plays(q)
