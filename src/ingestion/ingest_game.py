import sys
import os
import subprocess
import chromadb
import torch
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.ingestion.synergy_client import SynergyClient
from src.processing.vibe_check import get_image_embedding

# --- CONFIGURATION ---
LEAGUE = "ncaamb"
TARGET_TEAM = "Texas A&M" 
# Filter for high-value visual plays
TARGET_EVENTS = ["Dunk", "Steal", "Block", "3pt", "Technical Foul"] 

def get_frame_from_stream(video_url, offset_seconds, output_path):
    """Slices a single frame from the m3u8 stream using NVIDIA GPU hardware decoding if available."""
    try:
        cmd = [
            "ffmpeg", 
            "-ss", str(offset_seconds), 
            "-i", video_url,
            "-vframes", "1", 
            "-q:v", "2", 
            "-y", 
            output_path
        ]
        # Run silently
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        # print(f"FFmpeg Error: {e}") # Uncomment for deep debugging
        return False

def calculate_video_offset(period, clock, period_length=20):
    """Converts Game Clock (20:00 DOWN) to Video Timestamp (00:00 UP)."""
    try:
        parts = str(clock).split(':')
        mins = int(parts[0])
        secs = int(parts[1])
        # Elapsed time in current period
        elapsed = (period_length * 60) - (mins * 60 + secs)
        
        # Add offset for 2nd Half (Period 2)
        if period == 2: 
            # 20 mins for 1st half + 2 mins (120s) standard halftime buffer
            elapsed += (20 * 60) + 120 
        return elapsed
    except:
        return 0

def run_ingestion():
    # 0. Hardware Check
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"⚙️  Hardware Acceleration: {device.upper()} {'(NVIDIA Enabled)' if device == 'cuda' else ''}")

    client = SynergyClient()
    
    # Setup DB on your external drive path
    db_path = os.path.join(os.getcwd(), "data/vector_db")
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="skout_plays")

    # 1. Get Seasons
    print("🏀 Fetching Seasons...")
    seasons_resp = client.get_seasons(LEAGUE)
    if not seasons_resp or 'data' not in seasons_resp:
        print("❌ Critical: Could not fetch seasons.")
        return

    # UNWRAP LOGIC: SeasonPaginationResponse [cite: 1918] -> data list -> SeasonResponse [cite: 3447] -> data -> Season
    all_seasons = []
    for wrapper in seasons_resp['data']:
        if 'data' in wrapper:
            all_seasons.append(wrapper['data'])
            
    # Sort by name (Year) to get the newest
    all_seasons.sort(key=lambda x: x['name'], reverse=True)
    current_season = all_seasons[0]
    print(f"   ✅ Targeted Season: {current_season['name']} (ID: {current_season['id']})")

    # 2. Find Texas A&M
    print(f"🔎 Hunting for {TARGET_TEAM}...")
    aggies_id = None
    
    # We loop because pagination might be needed, but 'take=500' usually covers it
    teams_resp = client.get_teams(LEAGUE, current_season['id'])
    
    if teams_resp and 'data' in teams_resp:
        for team_wrapper in teams_resp['data']:
            # UNWRAP LOGIC: TeamResponse -> data -> Team [cite: 3592]
            team_data = team_wrapper.get('data')
            if team_data and TARGET_TEAM.lower() in team_data.get('name', '').lower():
                aggies_id = team_data['id']
                print(f"   👍 Found {team_data['name']} (ID: {aggies_id})")
                break
    
    if not aggies_id:
        print(f"   ⚠️ Could not find {TARGET_TEAM} in this season. Defaulting to generic games.")

    # 3. Fetch Games
    print("🏀 Fetching Games...")
    games_resp = client.get_games(LEAGUE, current_season['id'], team_id=aggies_id, limit=20)
    
    if not games_resp or 'data' not in games_resp:
        print("❌ Failed to fetch games.")
        return

    # UNWRAP LOGIC: GamePaginationResponse -> data list -> GameResponse -> data -> Game [cite: 2546]
    games = []
    for g_wrapper in games_resp['data']:
        if 'data' in g_wrapper:
            games.append(g_wrapper['data'])

    # Find a game with video
    target_game = None
    for g in games:
        # Check playlistUrl [cite: 2411]
        if g.get('playlistUrl'):
            target_game = g
            break
            
    if not target_game:
        print("❌ No games with video found. (Check if your API key includes video access)")
        return

    print(f"🚀 Processing: {target_game['awayTeam']['name']} @ {target_game['homeTeam']['name']}")
    
    # 4. Get Events
    events_resp = client.get_game_events(LEAGUE, target_game['id'])
    if not events_resp or 'data' not in events_resp:
        print("❌ No events found for this game.")
        return

    # UNWRAP LOGIC: EventPaginationResponse -> data list -> EventResponse -> data -> Event [cite: 2342]
    events = []
    for e_wrapper in events_resp['data']:
        if 'data' in e_wrapper:
            events.append(e_wrapper['data'])
    
    print(f"   Scanning {len(events)} events for highlights...")
    count = 0
    
    for event in events:
        desc = event.get('description', '')
        
        # Check against target events
        if any(x in desc for x in TARGET_EVENTS):
            # Unique ID based on game and clock
            play_id = f"{target_game['id']}_{str(event['clock']).replace(':', '')}_{count}"
            filename = f"data/video_clips/{play_id}.jpg"

            if os.path.exists(filename): 
                continue

            print(f"   🎥 Found: {desc} (Clock: {event['clock']})")
            
            # Timestamp Logic
            if ":" in str(event['clock']):
                offset = calculate_video_offset(event['period'], event['clock'])
                
                # Extract Frame
                success = get_frame_from_stream(target_game['playlistUrl'], offset, filename)
                
                if success:
                    # AI Embed
                    vector = get_image_embedding(filename)
                    
                    # Store
                    collection.add(
                        ids=[play_id],
                        embeddings=[vector],
                        metadatas=[{
                            "description": desc, 
                            "filepath": filename,
                            "game": f"{target_game['awayTeam']['abbr']} vs {target_game['homeTeam']['abbr']}",
                            "timestamp": str(event['clock'])
                        }]
                    )
                    print("      ✅ Indexed")
                    count += 1
                    if count >= 15: break # Cap at 15 for the test run

    print(f"\n🎉 Done! Indexed {count} plays.")

if __name__ == "__main__":
    run_ingestion()
