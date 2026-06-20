"""
Valorant Esports Analytics Dashboard — Main Entry Point.
Run: streamlit run app.py
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(
    page_title="Valorant Esports Analytics",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Valorant-inspired dark theme accents */
    .stApp {
        background-color: #0f1923;
    }
    .main-header {
        background: linear-gradient(135deg, #ff4655 0%, #1f2326 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        margin: 0;
    }
    .main-header p {
        color: #ddd;
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    .metric-card {
        background: #1f2937;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #ff4655;
    }
    .stMetric label {
        color: #94a3b8 !important;
    }
    div[data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚡ Valorant Esports Analytics</h1>
    <p>Real-time competitive intelligence • Live data from VLR.gg & HenrikDev API • ML-powered insights</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Valorant_logo_-_pink_color_version.svg/320px-Valorant_logo_-_pink_color_version.svg.png", width=200)
    st.markdown("---")
    st.markdown("### 📊 Navigation")
    st.markdown("""
    Use the sidebar pages to explore:
    - **Team Rankings** — Live global rankings
    - **Player Stats** — Performance metrics & filtering
    - **Player Comparison** — Side-by-side radar charts
    - **Match Results** — Recent pro matches
    - **Agent & Map Meta** — Pick/win rates
    - **ML Insights** — Clustering, predictions, forecasts
    - **Network Analysis** — Transfer flows & team graphs
    - **Live Tracker** — Player lookup & MMR
    """)
    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    timespan = st.selectbox("Data Timespan", ["30d", "60d", "90d"], index=1)
    st.session_state["timespan"] = timespan

    region = st.selectbox("Region Filter", ["all", "na", "eu", "ap", "kr", "br", "latam"])
    st.session_state["region"] = region

    if st.button("🔄 Force Refresh Data"):
        st.session_state["force_refresh"] = True
        st.rerun()

# ─── Main Dashboard Overview ─────────────────────────────────────────────────
st.markdown("## 📈 Quick Overview")

# Try to load cached data for overview stats
try:
    from data.db import Database
    db = Database()

    col1, col2, col3, col4 = st.columns(4)

    teams_df = db.get_team_rankings(st.session_state.get("region", "all"))
    players_df = db.get_player_stats(st.session_state.get("timespan", "60d"))
    matches_df = db.get_matches()

    with col1:
        st.metric("Teams Tracked", len(teams_df) if not teams_df.empty else "—")
    with col2:
        st.metric("Players Tracked", len(players_df) if not players_df.empty else "—")
    with col3:
        st.metric("Recent Matches", len(matches_df) if not matches_df.empty else "—")
    with col4:
        st.metric("Data Source", "VLR.gg + API")

    db.close()

    if teams_df.empty and players_df.empty:
        st.info("👆 Navigate to any page to start fetching live data. Data will be cached automatically.")

except Exception:
    st.info("👆 Navigate to **Team Rankings** or **Player Stats** to begin fetching live data from VLR.gg")

# ─── Feature Highlights ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🚀 Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🌐 Live Data
    - Real-time scraping from VLR.gg
    - HenrikDev API for player MMR
    - Liquipedia for transfers
    - Auto-caching with TTL
    """)

with col2:
    st.markdown("""
    ### 🤖 ML Models
    - K-Means player clustering
    - Match win probability
    - Rating forecasting
    - Breakout detection
    """)

with col3:
    st.markdown("""
    ### 📊 Advanced Analytics
    - Network/graph analysis
    - Transfer Sankey diagrams
    - Percentile rankings
    - Interactive Plotly charts
    """)

st.markdown("---")
st.caption("Data sourced from VLR.gg, HenrikDev Valorant API, and Liquipedia. Updated in real-time.")
