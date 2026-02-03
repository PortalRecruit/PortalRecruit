import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.getcwd(), "data/skout.db")

def calculate_dog_index():
    print("🐶 Calculating 'Dog Index' (Hustle Stats)...")
    conn = sqlite3.connect(DB_PATH)
    
    # We look for keywords in the description or tags
    # "Dog" events: Offensive Rebounds, Steals, Blocks, Charges (if we can find them)
    # We also look for "loose ball" if it appears in text
    
    query = """
    SELECT 
        player_id, 
        player_name,
        COUNT(CASE WHEN description LIKE '%Offensive Rebound%' THEN 1 END) as o_rebs,
        COUNT(CASE WHEN description LIKE '%Steal%' THEN 1 END) as steals,
        COUNT(CASE WHEN description LIKE '%Block%' THEN 1 END) as blocks,
        COUNT(CASE WHEN description LIKE '%Charge%' THEN 1 END) as charges,
        COUNT(*) as total_events
    FROM plays
    WHERE player_id IS NOT NULL
    GROUP BY player_id
    HAVING total_events > 10
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Simple Formula: (O_Reb * 1.5) + (Steal * 2) + (Block * 1.5) + (Charge * 3)
    # Normalized by total events (proxy for usage/minutes for now)
    
    df['dog_score'] = (
        (df['o_rebs'] * 1.5) + 
        (df['steals'] * 2.0) + 
        (df['blocks'] * 1.5) + 
        (df['charges'] * 3.0)
    ) / df['total_events']
    
    # Scale to 0-100
    max_score = df['dog_score'].max()
    df['dog_index'] = (df['dog_score'] / max_score) * 100
    
    print(df.sort_values('dog_index', ascending=False).head(10))
    return df

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        calculate_dog_index()
    else:
        print("❌ Database not found.")
