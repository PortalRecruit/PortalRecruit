import base64
import os
from pathlib import Path
import streamlit as st

WAR_ROOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Roboto+Mono:wght@500;700&display=swap');
:root{
 --bg-primary:#0e1117;
 --bg-elev-1:#111827;
 --bg-elev-2:#0b1220;
 --glass:rgba(17,25,40,0.56);
 --glass-strong:rgba(17,25,40,0.74);
 --border-subtle:rgba(255,255,255,0.14);
 --border-strong:rgba(255,255,255,0.24);
 --text-primary:#f3f6ff;
 --text-secondary:#a9b4cc;
 --text-muted:#7f8ba3;
 --tier-s:#f6c453;
 --tier-a:#31d0ff;
 --tier-b:#48d597;
 --tier-c:#8b9bb4;
 --accent:#ff7a18;
 --accent-2:#ffb347;
 --shadow-soft:0 8px 28px rgba(0,0,0,0.38);
 --radius-lg:14px;
 --radius-xl:18px;
}
html, body, [class*="css"]{
 font-family:"Inter", system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
 color:var(--text-primary);
}
/* Transparent Streamlit Containers (Let Video Show) */
[data-testid="stAppViewContainer"]{
 background: transparent !important;
}
[data-testid="stHeader"]{
 background: rgba(0,0,0,0) !important;
}
[data-testid="stToolbar"]{
 right: 1rem;
}
/* Fixed Wallpaper Layer */
.pr-video-bg-wrap{
 position: fixed;
 inset: 0;
 overflow: hidden;
 z-index: -20;
 background: radial-gradient(1200px 420px at 15% -10%, rgba(49,208,255,0.10), transparent 55%),
             radial-gradient(1200px 500px at 85% -20%, rgba(246,196,83,0.10), transparent 50%),
             linear-gradient(180deg, #0d111a 0%, #0e1117 50%, #0b1018 100%);
}
.pr-video-bg{
 position:absolute;
 width:100%;
 height:100%;
 object-fit:cover;
 opacity:0.28;
 filter: saturate(1.15) contrast(1.08) brightness(0.72);
 transform: scale(1.02);
 pointer-events:none;
}
/* Glass & Texture Overlays */
.pr-glass-overlay{
 position:absolute;
 inset:0;
 background: linear-gradient(180deg, rgba(6,10,16,0.50), rgba(9,12,20,0.62)),
             radial-gradient(900px 400px at 10% 10%, rgba(49,208,255,0.06), transparent 60%),
             radial-gradient(900px 420px at 90% 0%, rgba(246,196,83,0.05), transparent 62%);
 backdrop-filter: blur(3px);
 -webkit-backdrop-filter: blur(3px);
 pointer-events:none;
}
.pr-grain{
 position:absolute;
 inset:0;
 background-image: radial-gradient(rgba(255,255,255,0.025) 0.7px, transparent 0.7px);
 background-size: 3px 3px;
 opacity:.25;
 pointer-events:none;
}
/* Sidebar Styling */
[data-testid="stSidebar"]{
 background: linear-gradient(180deg, rgba(11,18,32,0.92), rgba(7,11,18,0.92)) !important;
 border-right: 1px solid rgba(255,255,255,0.08);
}
/* Button Styling (Standard Streamlit) */
.stButton > button, button[kind="primary"], button[kind="secondary"]{
 border-radius: 11px !important;
 border:1px solid rgba(255,255,255,0.16) !important;
 background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02)), rgba(20,28,44,0.82) !important;
 color:#f3f6ff !important;
 font-weight:600 !important;
 box-shadow: 0 3px 14px rgba(0,0,0,.26);
 transition: all .18s ease;
}
.stButton > button:hover{
 transform: translateY(-1px);
 border-color:rgba(255,122,24,0.45) !important;
 box-shadow: 0 8px 20px rgba(0,0,0,.32), 0 0 18px rgba(255,122,24,.20);
}
/* Custom Components (Cards, Tiers, Pills) */
.pr-card{
 background: rgba(17,25,40,0.58);
 border:1px solid rgba(255,255,255,0.14);
 border-radius:18px;
 backdrop-filter: blur(14px);
 -webkit-backdrop-filter: blur(14px);
 box-shadow: 0 8px 28px rgba(0,0,0,0.35);
 padding:.85rem .95rem;
 margin-bottom:.75rem;
}
.pr-card:hover{ border-color:rgba(255,255,255,0.24); }
.pr-name{ color:#f3f6ff; font-weight:800; font-size:.98rem; line-height:1.15;}
.pr-meta{ color:#a9b4cc; font-size:.81rem;}
.pr-stats{
 display:grid;
 grid-template-columns: repeat(3,minmax(0,1fr));
 gap:.4rem;
 margin-top:.55rem;
}
.pr-stat{
 background: rgba(255,255,255,0.035);
 border:1px solid rgba(255,255,255,0.1);
 border-radius:10px;
 padding:.35rem .45rem;
}
.pr-stat-k{ color:#7f8ba3; font-size:.68rem;}
.pr-stat-v{ font-family: 'Roboto Mono', monospace; color:#f3f6ff; font-size:.86rem; font-weight:700; }
.pr-tier{ border-radius:12px; border:1px solid rgba(255,255,255,0.15); padding:.56rem .74rem; margin-bottom:.6rem; font-weight:800; letter-spacing:.35px; }
.pr-tier--s{ color:#ffe29a; background:linear-gradient(90deg, rgba(246,196,83,.20), rgba(246,196,83,.05)); box-shadow:0 0 18px rgba(246,196,83,.22);} 
.pr-tier--a{ color:#9be9ff; background:linear-gradient(90deg, rgba(49,208,255,.20), rgba(49,208,255,.05)); box-shadow:0 0 18px rgba(49,208,255,.20);} 
.pr-tier--b{ color:#aef5d5; background:linear-gradient(90deg, rgba(72,213,151,.20), rgba(72,213,151,.05)); }
.pr-tier--c{ color:#c6d1e5; background:linear-gradient(90deg, rgba(139,155,180,.18), rgba(139,155,180,.05)); }
.pr-pill{display:inline-flex;align-items:center;padding:.18rem .52rem;border-radius:999px;font-size:.70rem;font-weight:700;border:1px solid transparent;margin:.12rem .2rem 0 0;}
.pr-pill--sniper{ color:#98f5c2; background:rgba(12,76,48,0.65); border-color:rgba(116,255,178,0.40); }
.pr-pill--enforcer{ color:#ffc4c4; background:rgba(93,31,31,0.58); border-color:rgba(255,132,132,0.38); }
.pr-pill--rim{ color:#b7d8ff; background:rgba(29,58,104,0.55); border-color:rgba(113,171,255,0.35); }
.pr-pill--pg{ color:#d9c8ff; background:rgba(53,35,94,0.56); border-color:rgba(187,146,255,0.35); }
</style>
"""

FALLBACK_BG_HTML = """
<div class="pr-video-bg-wrap">
  <div class="pr-glass-overlay"></div>
  <div class="pr-grain"></div>
</div>
"""


def inject_warroom_theme():
    st.markdown(WAR_ROOM_CSS, unsafe_allow_html=True)
    video_path = Path("www/PORTALRECRUIT_ANIMATED_LOGO.mp4")
    if video_path.exists():
        b64 = base64.b64encode(video_path.read_bytes()).decode("utf-8")
        html = f"""
        <div class="pr-video-bg-wrap">
          <video class="pr-video-bg" autoplay loop muted playsinline>
            <source src="data:video/mp4;base64,{b64}" type="video/mp4" />
          </video>
          <div class="pr-glass-overlay"></div>
          <div class="pr-grain"></div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(FALLBACK_BG_HTML, unsafe_allow_html=True)
