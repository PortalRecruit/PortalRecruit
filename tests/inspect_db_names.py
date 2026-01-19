import sqlite3
import os

DB_PATH = os.path.join(os.getcwd(), "data/skout.db")

def list_teams():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all unique home and away teams
    cursor.execute("SELECT DISTINCT home_team FROM games UNION SELECT DISTINCT away_team FROM games")
    teams = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"📋 Found {len(teams)} unique teams in the database:")
    print("-" * 40)
    for team in sorted(teams):
        print(f"'{team}'")

if __name__ == "__main__":
    list_teams()
