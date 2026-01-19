import streamlit as st
import sqlite3
import chromadb
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# --- CONFIGURATION ---
DB_PATH = os.path.join(os.getcwd(), "data/skout.db")
VECTOR_DB_PATH = os.path.join(os.getcwd(), "data/vector_db")

# --- SETUP BACKEND ---
@st.cache_resource
def get_chroma_client():
    return chromadb.PersistentClient(path=VECTOR_DB_PATH)

def calculate_video_offset(period, clock_seconds):
    """
    Attempts to convert 'Game Clock Remaining' to 'Video Time Elapsed'.
    NOTE: This assumes a FULL game video. For condensed games, this will be approximate.
    """
    # NCAA Men's: 2 Halves of 20 minutes (1200 seconds)
    period_length = 1200
    
    if period == 1:
        # If 15:00 remaining, elapsed is 5:00 (300s)
        return max(0, period_length - clock_seconds)
    elif period == 2:
        # Full first half (1200) + elapsed in second half
        return max(0, 1200 + (period_length - clock_seconds))
    else:
        return 0

def search_plays(query, n_results=50): # <--- INCREASED DEFAULT TO 50
    client = get_chroma_client()
    collection = client.get_collection(name="skout_plays")
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    parsed_results = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if not results['ids']:
        return []

    for i, play_id in enumerate(results['ids'][0]):
        meta = results['metadatas'][0][i]
        game_id = meta['game_id']
        
        # Fetch Game Details
        cursor.execute("SELECT home_team, away_team, video_path FROM games WHERE game_id = ?", (game_id,))
        game_row = cursor.fetchone()
        
        if game_row:
            home, away, v_path = game_row
            matchup = f"{home} vs {away}"
        else:
            matchup = "Unknown Game"
            v_path = None

        # Calculate Jump Timestamp
        # We need the period to calculate offset, retrieving it from DB since it wasn't in metadata
        cursor.execute("SELECT period, clock_seconds FROM plays WHERE play_id = ?", (play_id,))
        play_row = cursor.fetchone()
        start_offset = 0
        if play_row:
            period, clk_sec = play_row
            start_offset = calculate_video_offset(period, clk_sec)

        parsed_results.append({
            "play_id": play_id,
            "matchup": matchup,
            "clock_display": meta['clock'], # e.g. "14:23"
            "description": meta['original_desc'],
            "tags": meta['tags'],
            "video_path": v_path,
            "start_offset": start_offset,
            "score": results['distances'][0][i] if 'distances' in results else 0
        })
    
    conn.close()
    return parsed_results

# --- UI LAYOUT ---
st.set_page_config(page_title="SKOUT Intelligence", layout="wide", page_icon="🏀")

st.sidebar.title("SKOUT 🏀")
st.sidebar.markdown("### Search Settings")
# SLIDER: Let the user control how many results they want
result_limit = st.sidebar.slider("Max Results", 10, 100, 20)
filter_team = st.sidebar.text_input("Filter by Team")

st.title("Semantic Game Search")
st.markdown("Search for concepts like _'Late clock PnR'_, _'Forced turnovers'_, or _'Corner 3s'_.")

query = st.text_input("", placeholder="Ask SKOUT...", key="search_box")

if query:
    st.divider()
    with st.spinner(f"Scanning library for '{query}'..."):
        # Pass the slider value to the search function
        results = search_plays(query, n_results=result_limit)
    
    if not results:
        st.warning("No plays found.")
    else:
        # Filter results if team is specified
        filtered_results = [r for r in results if not filter_team or filter_team.lower() in r['matchup'].lower()]
        
        st.success(f"Found {len(filtered_results)} plays.")
        
        for idx, play in enumerate(filtered_results):
            # Card Header
            label = f"{idx+1}. {play['matchup']} | ⏰ {play['clock_display']} (Game Clock)"
            
            with st.expander(label, expanded=(idx == 0)):
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.markdown(f"**Play:** {play['description']}")
                    st.info(f"**Game Clock:** {play['clock_display']}")
                    
                    if play['tags']:
                        tags = play['tags'].split(", ")
                        chips = " ".join([f"`{t}`" for t in tags])
                        st.markdown(f"**Tags:** {chips}")
                    
                    st.caption(f"Relevance: {play['score']:.4f}")

                with col2:
                    if play['video_path'] and os.path.exists(play['video_path']):
                        # We pass start_time to the video player
                        # NOTE: For condensed games, this is an ESTIMATE.
                        st.video(play['video_path'], start_time=int(play['start_offset']))
                        st.caption(f"Attempting jump to {int(play['start_offset'])}s (Timeline may vary for condensed games)")
                    else:
                        st.error("🚫 Video file missing.")
