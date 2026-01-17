import streamlit as st
import chromadb
import os
import sys
import torch
from transformers import CLIPProcessor, CLIPModel

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# --- CONFIG ---
st.set_page_config(page_title="SKOUT", layout="wide")
DB_PATH = os.path.join(os.getcwd(), "data/vector_db")

# --- CACHED RESOURCES (Crucial for Speed) ---
@st.cache_resource
def load_ai_model():
    """Loads the AI Model once and keeps it in memory."""
    print("🔄 Loading CLIP Model... (This happens only once)")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return model, processor

@st.cache_resource
def load_db():
    """Connects to the database once."""
    print(f"🔄 Connecting to Database at {DB_PATH}")
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_collection(name="skout_plays")

# --- UI LOGIC ---
st.title("🏀 SKOUT: Semantic Search")

# 1. Load Resources (with visual feedback)
with st.status("Initializing Engine...", expanded=True) as status:
    st.write("🧠 Loading AI Model...")
    model, processor = load_ai_model()
    st.write("📂 Connecting to Database...")
    collection = load_db()
    status.update(label="Engine Ready!", state="complete", expanded=False)

# 2. Search Bar
query = st.text_input("Search for a moment:", "A happy dog")

if st.button("Search") or query:
    st.divider()
    
    # Debug Container
    debug_box = st.empty()
    debug_box.info(f"Processing query: '{query}'...")

    try:
        # Step A: Convert Text to Math
        inputs = processor(text=[query], return_tensors="pt", padding=True)
        with torch.no_grad():
            text_features = model.get_text_features(**inputs)
        search_vec = text_features[0].tolist()
        debug_box.success("✅ AI Vector Generated")

        # Step B: Query Database
        results = collection.query(
            query_embeddings=[search_vec],
            n_results=3
        )
        debug_box.success("✅ Database Query Complete")

        # Step C: Display Results
        if results['ids'] and results['ids'][0]:
            st.success(f"Found {len(results['ids'][0])} matches:")
            cols = st.columns(3)
            for i, col in enumerate(cols):
                if i < len(results['ids'][0]):
                    # Get data
                    img_path = results['metadatas'][0][i]['filepath']
                    desc = results['metadatas'][0][i]['description']
                    score = results['distances'][0][i]
                    
                    # Display
                    with col:
                        # Check if file exists before trying to show it
                        if os.path.exists(img_path):
                            st.image(img_path)
                            st.subheader(desc)
                            st.caption(f"Distance Score: {score:.4f}")
                        else:
                            st.error(f"Image missing: {img_path}")
        else:
            st.warning("No matches found in the database.")
            
    except Exception as e:
        st.error(f"💥 Error: {e}")
        print(f"Error details: {e}")
