import os
import sys
import requests
import sqlite3
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv("/media/jch903/fidelio/SKOUT/.env")

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# CONFIGURATION
SEASON_ID = "6085b5d0e6c2413bc4ba9122" # 2021-2022 Season
API_KEY = os.getenv("SYNERGY_API_KEY") 
DB_PATH = os.path.join(os.getcwd(), "data/skout.db")

def setup_db():
    """Ensures the games table exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    conn.commit()
    return conn

def fetch_season_games():
    """Fetches all games for the 2021-22 Season."""
    if not API_KEY:
        print("❌ Error: SYNERGY_API_KEY not found. Check your .env path.")
        return []

    url = "https://api.sportradar.com/synergy/basketball/ncaamb/games"
    
    headers = {
        "x-api-key": API_KEY
    }
    
    params = {
        "seasonId": SEASON_ID,
        "take": 1000 
    }
    
    print(f"📡 Fetching schedule for Season ID: {SEASON_ID}...")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ API Error: {e}")
        return []

    data = response.json()
    games = []
    
    # --- FIX: Iterate through the outer list, then UNWRAP the inner 'data' object ---
    for item in data.get('data', []):
        game = item.get('data', {}) # <--- This is the key fix (unwrapping)
        
        # Check for valid statuses (GameOver, Final, Closed)
        status = game.get('status')
        if status in ['GameOver', 'Final', 'Closed']: 
            try:
                # We use .get() safely for teams
                home_team = game.get('homeTeam', {}).get('name', 'Unknown')
                away_team = game.get('awayTeam', {}).get('name', 'Unknown')

                games.append((
                    game.get('id'),
                    SEASON_ID,
                    game.get('date'), 
                    home_team,
                    away_team, 
                    game.get('homeScore', 0),
                    game.get('awayScore', 0),
                    status,
                    None
                ))
            except Exception as e:
                print(f"⚠️ Skipping malformed game record: {e}")
                continue
    
    print(f"✅ Found {len(games)} valid games.")
    return games

def save_schedule(games):
    conn = setup_db()
    cursor = conn.cursor()
    
    count = 0
    for game in games:
        # Use INSERT OR REPLACE to update stats if we re-run it
        cursor.execute('''
            INSERT OR REPLACE INTO games 
            (game_id, season_id, date, home_team, away_team, home_score, away_score, status, video_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT video_path FROM games WHERE game_id = ?), ?))
        ''', game[:8] + (game[0], None)) # This complex logic preserves existing video_path links if they exist
        count += 1
        
    conn.commit()
    conn.close()
    print(f"💾 Successfully cached {count} games into skout.db")

if __name__ == "__main__":
    games_list = fetch_season_games()
    if games_list:
        save_schedule(games_list)
