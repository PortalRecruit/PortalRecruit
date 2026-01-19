import streamlit as st
import sqlite3
import chromadb
import os
import sys
import re
import base64
from datetime import datetime

# --- PATH CONFIGURATION ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '../../'))
sys.path.append(PROJECT_ROOT) 

DB_PATH = os.path.join(PROJECT_ROOT, "data/skout.db")
VECTOR_DB_PATH = os.path.join(PROJECT_ROOT, "data/vector_db")
LOGO_PATH = os.path.join(PROJECT_ROOT, "www", "SKOUT_LOGO.png")
BG_IMAGE_PATH = os.path.join(PROJECT_ROOT, "www", "SKOUT_BUCKETS.jpg")

# --- LOAD CONFIG ---
try:
    from config.ncaa_di_mens_basketball import NCAA_DI_MENS_BASKETBALL
    from config.ncaa_dii_mens_basketball import NCAA_DII_MENS_BASKETBALL
    from config.ncaa_diii_mens_basketball import NCAA_DIII_MENS_BASKETBALL
    LEAGUE_STRUCTURE = {
        "NCAA D1": NCAA_DI_MENS_BASKETBALL,
        "NCAA D2": NCAA_DII_MENS_BASKETBALL,
        "NCAA D3": NCAA_DIII_MENS_BASKETBALL
    }
except ImportError:
    LEAGUE_STRUCTURE = {}

# --- PAGE SETUP ---
st.set_page_config(
    page_title="SKOUT | Recruitment Engine", 
    layout="wide", 
    page_icon="🏀",
    initial_sidebar_state="expanded" 
)

# --- CUSTOM CSS (DARK MODE & BRANDING) ---
def get_base64_image(image_path):
    if not os.path.exists(image_path): return ""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def inject_custom_css():
    # Load background image if available
    bg_encoded = get_base64_image(BG_IMAGE_PATH)
    bg_style = ""
    if bg_encoded:
        bg_style = f"""
        .stApp {{
            background-image: linear-gradient(rgba(2, 6, 23, 0.95), rgba(2, 6, 23, 0.9)), url("data:image/jpg;base64,{bg_encoded}");
            background-size: cover;
            background-attachment: fixed;
        }}
        """
    else:
        bg_style = """
        .stApp {
            background-color: #020617; /* Slate 950 */
        }
        """

    st.markdown(f"""
    <style>
        /* BASE THEME */
        {bg_style}
        
        h1, h2, h3, h4, h5, h6, p, div, span, label, li {{
            color: #f8fafc !important; /* Slate 50 */
            font-family: 'Inter', sans-serif;
        }}
        
        /* SIDEBAR STYLING */
        section[data-testid="stSidebar"] {{
            background-color: rgba(15, 23, 42, 0.8); /* Slate 900 */
            border-right: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        /* INPUT FIELDS */
        .stTextInput > div > div > input {{
            background-color: rgba(30, 41, 59, 0.6);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }}
        .stSelectbox > div > div > div {{
            background-color: rgba(30, 41, 59, 0.6);
            color: white;
        }}
        .stMultiSelect > div > div > div {{
            background-color: rgba(30, 41, 59, 0.6);
            color: white;
        }}
        
        /* CARDS / EXPANDERS */
        .streamlit-expanderHeader {{
            background-color: rgba(30, 41, 59, 0.4) !important;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            color: white !important;
        }}
        .streamlit-expanderContent {{
            background-color: rgba(15, 23, 42, 0.4) !important;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-top: none;
        }}
        
        /* BUTTONS */
        button {{
            border-radius: 8px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- BACKEND FUNCTIONS ---
@st.cache_resource
def get_chroma_client():
    if not os.path.exists(VECTOR_DB_PATH): return None
    return chromadb.PersistentClient(path=VECTOR_DB_PATH)

def get_database_connection():
    return sqlite3.connect(DB_PATH)

def get_unique_tags():
    if not os.path.exists(DB_PATH): return []
    conn = get_database_connection()
    try:
        rows = conn.execute("SELECT tags FROM plays WHERE tags != ''").fetchall()
        unique_tags = set()
        for r in rows:
            tags = [t.strip() for t in r[0].split(",")]
            unique_tags.update(tags)
        return sorted(list(unique_tags))
    except: return []
    finally: conn.close()

def normalize_name(name):
    if not name: return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def search_plays(query, selected_tags, selected_teams, year_range, n_results=50):
    client = get_chroma_client()
    if not client: return []
    try: collection = client.get_collection(name="skout_plays")
    except: return []

    search_text = query if query else " ".join(selected_tags)
    if not search_text: return []

    results = collection.query(query_texts=[search_text], n_results=n_results)
    parsed = []
    conn = get_database_connection()
    cursor = conn.cursor()

    if not results['ids']: return []
    
    norm_selected_teams = {normalize_name(t) for t in selected_teams}

    for i, play_id in enumerate(results['ids'][0]):
        meta = results['metadatas'][0][i]
        cursor.execute("SELECT home_team, away_team, video_path, date FROM games WHERE game_id = ?", (meta['game_id'],))
        game = cursor.fetchone()
        if not game: continue
        
        home, away, vid_path, date_str = game
        
        # FILTERS
        if norm_selected_teams:
            if normalize_name(home) not in norm_selected_teams and normalize_name(away) not in norm_selected_teams:
                continue

        game_year = int(date_str[:4]) if date_str else 0
        if game_year < year_range[0] or game_year > year_range[1]: continue

        if selected_tags:
            play_tags = meta['tags'].split(", ") if meta['tags'] else []
            if not all(tag in play_tags for tag in selected_tags): continue

        # Offset Logic
        period_len = 1200 
        cursor.execute("SELECT period, clock_seconds FROM plays WHERE play_id = ?", (play_id,))
        p_row = cursor.fetchone()
        offset = 0
        if p_row:
            period, clock_sec = p_row
            if period == 1: offset = max(0, period_len - clock_sec)
            elif period == 2: offset = max(0, 1200 + (period_len - clock_sec))

        parsed.append({
            "id": play_id,
            "matchup": f"{home} vs {away}",
            "desc": meta['original_desc'],
            "tags": meta['tags'],
            "clock": meta['clock'],
            "video": vid_path,
            "offset": offset,
            "score": results['distances'][0][i],
            "date": date_str
        })
    conn.close()
    return parsed

# --- SIDEBAR CONTENT ---
if os.path.exists(LOGO_PATH):
    st.sidebar.image(LOGO_PATH, use_container_width=True)
else:
    st.sidebar.title("SKOUT 🏀")

st.sidebar.markdown("### 🔎 Filters")
sel_div = st.sidebar.selectbox("Division", ["All"] + list(LEAGUE_STRUCTURE.keys()), index=1)

available_conferences = []
# --- FIX: Variable name corrected below ---
if sel_div != "All":
    available_conferences = list(LEAGUE_STRUCTURE[sel_div].keys())
    
sel_conf = st.sidebar.selectbox("Conference", ["All"] + sorted(available_conferences), index=1)

available_teams = []
if sel_conf != "All" and sel_div != "All":
    available_teams = LEAGUE_STRUCTURE[sel_div][sel_conf]
elif sel_div != "All":
    for conf_teams in LEAGUE_STRUCTURE[sel_div].values():
        available_teams.extend(conf_teams)

sel_teams = st.sidebar.multiselect("Team", sorted(available_teams), placeholder="Select Teams...")
sel_years = st.sidebar.slider("Season", 2020, datetime.now().year, (2020, datetime.now().year))

# --- MAIN CONTENT ---
st.title("SKOUT | Recruitment Engine")

# CHECK DB STATUS
db_exists = os.path.exists(DB_PATH)
if db_exists:
    conn = sqlite3.connect(DB_PATH)
    try:
        game_count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    except:
        game_count = 0
    conn.close()
else:
    game_count = 0

# --- GREETING / INSTRUCTIONS ---
show_instructions = True
is_expanded = (game_count == 0)

if show_instructions:
    with st.expander("ℹ️  How to use SKOUT (Instructions)", expanded=is_expanded):
        st.markdown("""
        ### 👋 Welcome, Coach.
        
        **1. Populate Your Engine:**
        * Navigate to **Admin Settings** in the left sidebar.
        * Enter your **Synergy API Key**.
        * Click **Sync Schedule** -> **Sync Plays** -> **Build AI Index**.
        
        **2. Search the Database:**
        * Use the **Semantic Search** bar below to describe what you are looking for (e.g., *"Late clock PnR defenses"*).
        * Use the **Filters** on the left to narrow by Conference or Team.
        * Use the **Tag Filter** to find specific events (Turnovers, Dunks, etc.).
        """)
        
        if game_count == 0:
            st.warning("⚠️ Database is currently empty. Please follow step 1 above.")

# SEARCH INTERFACE
col1, col2 = st.columns([3, 1])
with col1:
    search_query = st.text_input("Search Playbook", placeholder="e.g. 'Freshman turnovers', 'Pick and roll lob'")
with col2:
    real_tags = get_unique_tags()
    selected_tags_filter = st.multiselect("Tags", real_tags, placeholder="Add tags...")

# RESULTS AREA
if search_query or selected_tags_filter:
    st.divider()
    with st.spinner("Analyzing tape..."):
        results = search_plays(search_query, selected_tags_filter, sel_teams, sel_years)
    
    if not results:
        st.warning("No plays found matching criteria.")
    else:
        st.success(f"Found {len(results)} plays.")
        for idx, play in enumerate(results):
            with st.container():
                label = f"{idx+1}. {play['matchup']} ({play['date']}) | ⏰ {play['clock']}"
                with st.expander(label, expanded=(idx == 0)):
                    c1, c2 = st.columns([1.2, 2])
                    with c1:
                        st.markdown(f"**{play['desc']}**")
                        # Chips
                        if play['tags']:
                            tags = play['tags'].split(", ")
                            chips = ""
                            for t in tags:
                                color = "blue"
                                if "turnover" in t: color = "red"
                                if "made" in t or "score" in t: color = "green"
                                chips += f":{color}[`{t}`] "
                            st.markdown(chips)
                    with c2:
                        if play['video']:
                            st.video(play['video'], start_time=int(play['offset']))
                        else:
                            st.info("Video unavailable.")
