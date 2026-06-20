"""Player Stats — Performance metrics with filtering and sorting."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="Player Stats", page_icon="👤", layout="wide")
st.title("👤 Player Stats")

timespan = st.session_state.get("timespan", "60d")
region = st.session_state.get("region", "all")


@st.cache_data(ttl=1800, show_spinner="Fetching player stats from VLR.gg...")
def load_player_stats(timespan: str, region: str):
    from src.scrapers.vlr_scraper import VLRScraper
    from data.db import Database

    db = Database()
    if db.player_stats_stale(timespan) or st.session_state.get("force_refresh"):
        with VLRScraper() as scraper:
            players = scraper.get_player_stats(timespan=timespan, region=region)
        if players:
            db.save_player_stats(players, timespan)
        st.session_state.pop("force_refresh", None)

    df = db.get_player_stats(timespan)
    db.close()
    return df


df = load_player_stats(timespan, region)

if df.empty:
    st.warning("No player data available. Try refreshing or changing timespan.")
    st.stop()

# ─── Filters ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("### Filters")
min_rating = st.sidebar.slider("Min Rating", 0.8, 1.5, 1.0, 0.05)
sort_by = st.sidebar.selectbox("Sort By", ["rating", "acs", "kd", "adr", "kast", "kpr", "fkpr", "headshot_pct"])

teams_available = sorted(df["team"].unique().tolist())
selected_teams = st.sidebar.multiselect("Filter Teams", teams_available, default=[])

# Apply filters
filtered = df[df["rating"] >= min_rating]
if selected_teams:
    filtered = filtered[filtered["team"].isin(selected_teams)]
filtered = filtered.sort_values(sort_by, ascending=False).reset_index(drop=True)

# ─── Stats Table ─────────────────────────────────────────────────────────────
st.markdown(f"### Player Performance — Last `{timespan}` | Showing {len(filtered)} players")
st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    column_config={
        "player": st.column_config.TextColumn("Player"),
        "team": st.column_config.TextColumn("Team"),
        "agents": st.column_config.TextColumn("Agents"),
        "acs": st.column_config.NumberColumn("ACS", format="%.1f"),
        "kd": st.column_config.NumberColumn("K/D", format="%.2f"),
        "adr": st.column_config.NumberColumn("ADR", format="%.1f"),
        "kast": st.column_config.NumberColumn("KAST%", format="%.1f"),
        "kpr": st.column_config.NumberColumn("KPR", format="%.2f"),
        "apr": st.column_config.NumberColumn("APR", format="%.2f"),
        "fkpr": st.column_config.NumberColumn("FKPR", format="%.2f"),
        "fdpr": st.column_config.NumberColumn("FDPR", format="%.2f"),
        "headshot_pct": st.column_config.NumberColumn("HS%", format="%.1f"),
        "clutch_pct": st.column_config.NumberColumn("Clutch%", format="%.1f"),
        "rating": st.column_config.NumberColumn("Rating", format="%.2f"),
    },
)

# ─── Visualizations ──────────────────────────────────────────────────────────
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Top 15 by Rating")
    top15 = filtered.head(15)
    fig = px.bar(
        top15, x="rating", y="player", orientation="h",
        color="acs", color_continuous_scale="YlOrRd",
        title="Top Players by Rating (colored by ACS)",
    )
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("#### K/D vs ACS")
    fig2 = px.scatter(
        filtered, x="kd", y="acs", hover_name="player",
        color="rating", size="adr", color_continuous_scale="Viridis",
        title="K/D Ratio vs Average Combat Score",
    )
    fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

# ─── Distributions ───────────────────────────────────────────────────────────
st.markdown("#### Stat Distributions")
dist_metric = st.selectbox("Select Metric", ["acs", "kd", "adr", "kast", "headshot_pct", "rating"])
fig3 = px.histogram(
    filtered, x=dist_metric, nbins=30, marginal="box",
    title=f"Distribution of {dist_metric.upper()}",
    color_discrete_sequence=["#ff4655"],
)
fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig3, use_container_width=True)

# ─── Breakout Players ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🔥 Breakout Performers")
try:
    from src.models.forecasting import detect_breakout_players
    breakouts = detect_breakout_players(filtered)
    if not breakouts.empty:
        st.dataframe(
            breakouts[["player", "team", "acs", "kd", "adr", "rating", "breakout_score"]].head(10),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No breakout performers detected in current dataset.")
except Exception as e:
    st.caption(f"Breakout detection unavailable: {e}")
