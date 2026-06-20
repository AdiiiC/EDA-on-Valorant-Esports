"""Match Results — Recent pro matches from VLR.gg."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Match Results", page_icon="🎮", layout="wide")
st.title("🎮 Recent Match Results")


@st.cache_data(ttl=300, show_spinner="Fetching recent matches...")
def load_matches():
    from src.scrapers.vlr_scraper import VLRScraper
    from data.db import Database

    db = Database()
    if db.matches_stale() or st.session_state.get("force_refresh"):
        with VLRScraper() as scraper:
            matches = scraper.get_recent_matches(page=1)
            matches += scraper.get_recent_matches(page=2)
        if matches:
            db.save_matches(matches)
        st.session_state.pop("force_refresh", None)

    df = db.get_matches()
    db.close()
    return df


df = load_matches()

if df.empty:
    st.warning("No match data available. Try refreshing.")
    st.stop()

# ─── Filters ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("### Filters")
events = sorted(df["event"].unique().tolist())
selected_event = st.sidebar.selectbox("Filter by Event", ["All"] + events)

teams_in_matches = sorted(set(df["team1"].tolist() + df["team2"].tolist()))
selected_team = st.sidebar.selectbox("Filter by Team", ["All"] + teams_in_matches)

filtered = df.copy()
if selected_event != "All":
    filtered = filtered[filtered["event"] == selected_event]
if selected_team != "All":
    filtered = filtered[(filtered["team1"] == selected_team) | (filtered["team2"] == selected_team)]

# ─── Match Cards ─────────────────────────────────────────────────────────────
st.markdown(f"### Showing {len(filtered)} matches")

for _, match in filtered.head(30).iterrows():
    score1 = match["score1"]
    score2 = match["score2"]
    winner_indicator = "🟢" if score1 > score2 else "🔴"
    loser_indicator = "🔴" if score1 > score2 else "🟢"

    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])
    with col1:
        st.markdown(f"**{winner_indicator} {match['team1']}**")
    with col2:
        st.markdown(f"**{score1}**")
    with col3:
        st.markdown("vs")
    with col4:
        st.markdown(f"**{score2}**")
    with col5:
        st.markdown(f"**{loser_indicator} {match['team2']}**")

    st.caption(f"📅 {match['date']} • 🏆 {match['event']}")
    st.markdown("---")

# ─── Win Rate Analysis ────────────────────────────────────────────────────────
st.markdown("### 📊 Team Win Rates (from recent matches)")

# Compute win rates
team_records: dict[str, dict] = {}
for _, match in df.iterrows():
    t1, t2, s1, s2 = match["team1"], match["team2"], match["score1"], match["score2"]
    for team in [t1, t2]:
        if team not in team_records:
            team_records[team] = {"wins": 0, "losses": 0, "maps_won": 0, "maps_lost": 0}

    if s1 > s2:
        team_records[t1]["wins"] += 1
        team_records[t2]["losses"] += 1
    elif s2 > s1:
        team_records[t2]["wins"] += 1
        team_records[t1]["losses"] += 1

    team_records[t1]["maps_won"] += s1
    team_records[t1]["maps_lost"] += s2
    team_records[t2]["maps_won"] += s2
    team_records[t2]["maps_lost"] += s1

wr_data = []
for team, record in team_records.items():
    total = record["wins"] + record["losses"]
    if total >= 3:  # minimum matches
        wr_data.append({
            "team": team,
            "wins": record["wins"],
            "losses": record["losses"],
            "win_rate": record["wins"] / total * 100,
            "matches": total,
            "map_diff": record["maps_won"] - record["maps_lost"],
        })

wr_df = pd.DataFrame(wr_data).sort_values("win_rate", ascending=False).head(20)

if not wr_df.empty:
    fig = px.bar(
        wr_df, x="team", y="win_rate", color="map_diff",
        color_continuous_scale="RdYlGn",
        title="Win Rate by Team (min 3 matches)",
        labels={"win_rate": "Win Rate %", "map_diff": "Map Differential"},
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)

# ─── Score Distribution ──────────────────────────────────────────────────────
st.markdown("### Match Score Distribution")
scores = []
for _, match in df.iterrows():
    scores.append(f"{match['score1']}-{match['score2']}")
    scores.append(f"{match['score2']}-{match['score1']}")

score_counts = pd.Series(scores).value_counts().head(10)
fig2 = px.bar(
    x=score_counts.index, y=score_counts.values,
    title="Most Common Scorelines",
    labels={"x": "Score", "y": "Frequency"},
    color_discrete_sequence=["#ff4655"],
)
fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig2, use_container_width=True)
