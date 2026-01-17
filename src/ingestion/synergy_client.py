import requests
import os
import sys
import time

# Ensure we can import from config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.settings import SYNERGY_API_KEY, BASE_URL

class SynergyClient:
    def __init__(self):
        if not SYNERGY_API_KEY:
            raise ValueError("❌ ERROR: SYNERGY_API_KEY not found in .env")
        
        self.base_url = BASE_URL
        self.headers = {
            "x-api-key": SYNERGY_API_KEY,
            "Content-Type": "application/json"
        }

    def _get(self, endpoint, params=None, retries=4):
        """
        Executes a GET request with strict 429 Rate Limit handling.
        """
        url = f"{self.base_url}{endpoint}"
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, params=params)
                
                # 1. Handle Rate Limiting (429)
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 2.5 # Backoff: 2.5s, 5s, 7.5s...
                    print(f"      ⚠️ Rate limit hit (429). Pausing for {wait_time}s...")
                    time.sleep(wait_time)
                    continue # Retry
                
                # 2. Handle Server Errors (5xx)
                if response.status_code >= 500:
                    print(f"      ⚠️ Server Error ({response.status_code}). Retrying...")
                    time.sleep(2)
                    continue

                response.raise_for_status()
                return response.json()
            
            except Exception as e:
                if attempt == retries - 1:
                    print(f"❌ API Failed on {endpoint}: {e}")
                    return None
        return None

    def get_seasons(self, league_code="ncaamb"):
        # Spec: GET /{league}/seasons
        return self._get(f"/{league_code}/seasons")

    def get_teams(self, league_code, season_id):
        # Spec: GET /{league}/teams
        # We limit 'take' to 500 to avoid timeouts/heavy rate limits
        params = {"seasonId": season_id, "take": 500} 
        return self._get(f"/{league_code}/teams", params=params)

    def get_games(self, league_code, season_id, team_id=None, limit=20):
        # Spec: GET /{league}/games
        params = {
            "seasonId": season_id,
            "take": limit
        }
        if team_id:
            params["teamId"] = team_id # Spec
            
        return self._get(f"/{league_code}/games", params=params)

    def get_game_events(self, league_code, game_id):
        # Spec: GET /{league}/games/{gameId}/events
        return self._get(f"/{league_code}/games/{game_id}/events")
