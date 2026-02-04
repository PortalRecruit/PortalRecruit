import sys
from pathlib import Path

import streamlit as st

from src.dashboard.theme import inject_background
# --- 1. SETUP PATHS ---
# Ensure repo root is on sys.path so imports work
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# --- 2. PAGE CONFIGURATION ---
WORDMARK_DARK_URL = "https://skoutsearch.github.io/PortalRecruit/PORTALRECRUIT_WORDMARK_DARK.jpg"

st.set_page_config(
    page_title="PortalRecruit | Search",
    layout="wide",
    page_icon="🏀",
    initial_sidebar_state="expanded", # Changed to expanded for navigation
)
inject_background()

# --- 3. HELPER FUNCTIONS ---
def check_ingestion_status():
    """
    Checks if the database exists. 
    ADJUST THE PATH below to match where your ingestion script saves the database 
    (e.g., 'chroma_db' or 'data/vectors').
    """
    db_path = REPO_ROOT / "chroma_db" # <--- VERIFY THIS PATH
    return db_path.exists()

def render_header():
    st.markdown(
        f"""
        <div class="pr-hero">
          <img src="{WORDMARK_DARK_URL}" style="max-width:560px; width:min(560px, 92vw); height:auto; object-fit:contain;" />
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- 4. MAIN APP LOGIC ---

# Initialize Session State for Navigation
if "app_mode" not in st.session_state:
    # Default to Search if data exists, otherwise send to Admin/Setup
    if check_ingestion_status():
        st.session_state.app_mode = "Search"
    else:
        st.session_state.app_mode = "Admin"

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation")
    mode = st.radio(
        "Choose Mode:", 
        ["Search", "Admin"], 
        index=0 if st.session_state.app_mode == "Search" else 1
    )
    st.session_state.app_mode = mode
    st.divider()
    st.info(f"Current Status: {st.session_state.app_mode}")

# --- 5. RENDER CONTENT BASED ON MODE ---

if st.session_state.app_mode == "Admin":
    # ---------------- ADMIN / INGESTION VIEW ----------------
    render_header()
    st.caption("⚙️ Ingestion Pipeline & Settings")
    
    # Execute the existing admin_content.py
    admin_path = Path(__file__).with_name("admin_content.py")
    if admin_path.exists():
        code = admin_path.read_text(encoding="utf-8")
        exec(compile(code, str(admin_path), "exec"), globals(), globals())
    else:
        st.error(f"Could not find {admin_path}")

elif st.session_state.app_mode == "Search":
    # ---------------- SEARCH VIEW ----------------
    render_header()
    
    # This is where your Search UI lives. 
    # Ideally, put this in a separate file like `src/dashboard/search_ui.py` and import it.
    # For now, I'll place the logic block here.
    
    st.markdown("### 🔍 Semantic Player Search")
    
    query = st.chat_input("Describe the player you are looking for (e.g., 'A high-motor rim protector who can switch on guards')...")
    
    if query:
        st.write(f"Searching for: **{query}**")
        
        # --- CONNECT TO YOUR SEARCH ENGINE HERE ---
        # Example:
        # from src.engine import search
        # results = search.query(query)
        # st.dataframe(results)
        
        st.success("Search logic goes here! (Connect your backend in Home.py lines 85+)")
