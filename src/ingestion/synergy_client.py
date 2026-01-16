import requests
import os
import sys

# Ensure we can import from config by adding the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from config.settings import SYNERGY_API_KEY, BASE_URL

class SynergyClient:
    """
    Client for interacting with the Sportradar Synergy Basketball API v1.
    """
    def __init__(self):
        if not SYNERGY_API_KEY:
            raise ValueError("❌ ERROR: SYNERGY_API_KEY not found. Check your .env file.")
        
        self.base_url = BASE_URL
        self.headers = {
            "x-api-key": SYNERGY_API_KEY,
            "Content-Type": "application/json"
        }

    def _get(self, endpoint, params=None):
        """Helper method for GET requests with error handling."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"❌ HTTP Error: {err}")
            # Print the actual error message from Synergy if available
            print(f"Response: {response.text}") 
            return None

    def get_seasons(self, league_code="ncaamb"):
        """
        Fetches all seasons for a league to find the current 'seasonId'.
        Endpoint: GET /{league}/seasons
        """
        return self._get(f"/{league_code}/seasons")

    def get_games(self, league_code, season_id, limit=5):
        """
        Fetches a list of games for a specific season.
        Endpoint: GET /{league}/games
        """
        params = {
            "seasonId": season_id,
            "take": limit  # Limit results to keep it fast
        }
        return self._get(f"/{league_code}/games", params=params)

    def get_game_events(self, league_code, game_id):
        """
        Fetches play-by-play events (shots, rebounds, etc.) for a game.
        This is the CRITICAL endpoint for video syncing.
        Endpoint: GET /{league}/games/{gameId}/events
        """
        return self._get(f"/{league_code}/games/{game_id}/events")

# --- TEST BLOCK: Run this file directly to verify your key ---
if __name__ == "__main__":
    print("🏀 SKOUT: Testing Synergy Connection...")
    
    client = SynergyClient()
    league = "ncaamb" # NCAA Men's Basketball
    
    # 1. Get Seasons
    print(f"\n1. Fetching Seasons for {league}...")
    seasons_data = client.get_seasons(league)
    
    if seasons_data and 'data' in seasons_data:
        # Sort by year to get the most recent one
        # Note: Synergy season names are often "2024" or "2024-2025"
        all_seasons = seasons_data['data']
        latest_season = all_seasons[-1] # Grabbing the last one in the list (usually newest)
        season_id = latest_season['id']
        season_name = latest_season['name']
        
        print(f"✅ Success! Found Season: {season_name} (ID: {season_id})")
        
        # 2. Get Games from this Season
        print(f"\n2. Fetching recent games from {season_name}...")
        games_data = client.get_games(league, season_id, limit=3)
        
        if games_data and 'data' in games_data:
            games = games_data['data']
            print(f"✅ Found {len(games)} games.")
            
            # 3. Inspect the first game for Video URLs
            if games:
                first_game = games[0]
                game_id = first_game['id']
                matchup = f"{first_game['awayTeam']['name']} @ {first_game['homeTeam']['name']}"
                
                print(f"\n3. Inspecting Game: {matchup}")
                print(f"   Game ID: {game_id}")
                
                # Check for the video playlist URL (The "Keys to the Ferrari")
                video_url = first_game.get('playlistUrl', 'NOT FOUND')
                print(f"   🎥 Video Playlist URL: {video_url}")
                
                if video_url == 'NOT FOUND' or video_url is None:
                    print("   ⚠️ WARNING: No video URL found. Check if your API tier includes video.")
                else:
                    print("   🚀 SUCCESS: We have a video stream to slice!")

                # 4. Fetch Events (The "Map")
                print(f"\n4. Fetching Events for Game {game_id}...")
                events_data = client.get_game_events(league, game_id)
                if events_data and 'data' in events_data:
                    events = events_data['data']
                    print(f"✅ Retrieved {len(events)} events.")
                    
                    # Show a sample event with clock info
                    if len(events) > 0:
                        sample = events[0]
                        print(f"   Sample Event: {sample.get('description', 'Unknown Play')}")
                        print(f"   Clock: {sample.get('clock')} (Used to sync video)")
        else:
            print("❌ No games found for this season.")
    else:
        print("❌ Failed to fetch seasons. Check API Key or League Code.")
