import os
import json
import time
import requests
from pathlib import Path

# --- CONFIGURATION ---
# 1. API KEY: Ensure this is set in your environment or pasted here safely
# WARNING: Do not commit your actual key to GitHub. Use env vars if possible.
API_KEY = os.getenv("SYNERGY_API_KEY", "YOUR_SYNERGY_API_KEY_HERE")

# 2. BASE URL: CORRECTED
# Your snippet had 'api-docs.sportradar.us' which is wrong.
# The logs confirm the live API is 'api.sportradar.com'.
BASE_URL = "https://api.sportradar.com/synergy/basketball"

# 3. SAFETY CONTROLS
# Increased to 2.0s to guarantee we stay under the "1 request per second" limit
# and account for network latency/jitter.
SAFE_DELAY_SECONDS = 2.0
MAX_RETRIES = 5

# 4. TARGETS
# Changed to lowercase 'ncaamb' to match the successful requests in your logs.
TARGET_LEAGUE_CODE = "ncaamb"
TARGET_SEASON_YEAR = 2024

# 5. STORAGE PATHS
# This builds the folder structure: /data/gold/season_2025/games/...
GOLD_ROOT = Path("data/gold/season_2025")
EVENTS_DIR = GOLD_ROOT / "games" / "events"

# Create directories automatically
os.makedirs(EVENTS_DIR, exist_ok=True)
os.makedirs(GOLD_ROOT / "metadata", exist_ok=True)


def fetch_with_backoff(url, params=None):
    """
    Robust fetcher that respects rate limits (429) and handles connection errors.
    """
    headers = {"x-api-key": API_KEY}
    for attempt in range(MAX_RETRIES):
        try:
            print(f"--> Fetching: {url}")
            response = requests.get(url, headers=headers, params=params)

            # SUCCESS
            if response.status_code == 200:
                time.sleep(SAFE_DELAY_SECONDS)  # The Safety Pause
                return response.json()

            # RATE LIMIT HIT
            elif response.status_code == 429:
                wait_time = (2 ** attempt) * 3  # Aggressive backoff: 3s, 6s, 12s...
                print(f"⚠️ Rate Limit (429). Cooling down for {wait_time}s...")
                time.sleep(wait_time)
                continue

            # OTHER ERRORS
            else:
                print(f"❌ Error {response.status_code}: {response.text[:200]}")
                # Don't retry on 404 (Not Found) or 401 (Unauthorized)
                if response.status_code in [401, 403, 404]:
                    return None
                time.sleep(1)

        except Exception as e:
            print(f"❌ Network Error: {e}")
            time.sleep(1)

    print("❌ Failed after max retries.")
    return None


def save_json(data, filepath):
    """Saves data to the Golden Database."""
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Saved: {filepath.name}")
    except Exception as e:
        print(f"❌ Failed to save {filepath}: {e}")


def build_golden_database():
    """
    Main Orchestrator:
    1. Fetch Schedule
    2. Iterate Games
    3. Save Play-by-Play (PBP)
    """
    if "YOUR_SYNERGY_API_KEY_HERE" in API_KEY:
        print("🛑 ERROR: Please set your API_KEY in the script line 10.")
        return

    # --- STEP 1: FETCH SCHEDULE ---
    # URL: https://api.sportradar.com/synergy/basketball/ncaamb/games
    games_url = f"{BASE_URL}/{TARGET_LEAGUE_CODE}/games"
    params = {"season_year": TARGET_SEASON_YEAR}

    print(f"🔍 Fetching Schedule for {TARGET_SEASON_YEAR}...")
    schedule_data = fetch_with_backoff(games_url, params)
    if not schedule_data:
        print("CRITICAL: Could not fetch schedule. Verify API Key and Season Year.")
        return

    # Save Master Schedule
    save_json(schedule_data, GOLD_ROOT / "metadata" / "schedule.json")

    # --- STEP 2: ITERATE GAMES ---
    # Parse the game list. Adjust key 'games' if API returns a different wrapper.
    games_list = schedule_data.get("games", [])
    if not games_list:
        print("⚠️ No games found. Response might be empty or key is wrong.")
        return

    print(f"🏀 Found {len(games_list)} games. Starting ingestion...")
    success_count = 0
    skip_count = 0

    for game in games_list:
        game_id = game.get("id")
        status = game.get("status")  # e.g., 'closed', 'complete'

        # FILTER: Only fetch finished games
        if status not in ["closed", "complete", "final"]:
            continue

        # IDEMPOTENCY: Check if file exists
        pbp_path = EVENTS_DIR / f"{game_id}_events.json"
        if pbp_path.exists():
            print(f"⏩ Skipping {game_id} (Already Downloaded)")
            skip_count += 1
            continue

        # --- STEP 3: FETCH EVENTS ---
        # URL: .../games/{id}/events
        events_url = f"{BASE_URL}/{TARGET_LEAGUE_CODE}/games/{game_id}/events"
        events_data = fetch_with_backoff(events_url)
        if events_data:
            save_json(events_data, pbp_path)
            success_count += 1

    print("🎉 Golden Database Build Complete.")
    print(f"📊 Stats: {success_count} downloaded, {skip_count} skipped.")


if __name__ == "__main__":
    print("🚀 Starting PortalRecruit Golden Database Ingestion...")
    build_golden_database()
