"""Live Tracker — Player lookup, MMR tracking via HenrikDev API."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Live Tracker", page_icon="📡", layout="wide")
st.title("📡 Live Player & Leaderboard Tracker")

# ─── Player Lookup ───────────────────────────────────────────────────────────
st.markdown("## 🔍 Player Lookup")
st.markdown("Look up any Valorant player's MMR, rank, and recent match history via HenrikDev API.")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    player_name = st.text_input("Riot ID (name)", placeholder="TenZ")
with col2:
    player_tag = st.text_input("Tag", placeholder="0505")
with col3:
    player_region = st.selectbox("Region", ["na", "eu", "ap", "kr", "br", "latam"])

if st.button("🔎 Look Up Player") and player_name and player_tag:
    from src.api_clients.henrik_api import HenrikAPIClient

    with st.spinner("Fetching player data..."):
        try:
            client = HenrikAPIClient()

            # Account info
            account = client.get_account(player_name, player_tag)
            st.markdown(f"### {account.name}#{account.tag}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Region", account.region.upper())
            with col2:
                st.metric("Level", account.account_level)
            with col3:
                if account.card_url:
                    st.image(account.card_url, width=200)

            # MMR
            st.markdown("---")
            st.markdown("#### Ranked Info")
            mmr = client.get_mmr(player_name, player_tag, player_region)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Current Rank", mmr.current_tier)
            with col2:
                st.metric("RR", mmr.current_rr)
            with col3:
                st.metric("Peak Rank", mmr.peak_tier)
            with col4:
                st.metric("Peak Season", mmr.peak_season)

            if mmr.wins + mmr.losses > 0:
                wr = mmr.wins / (mmr.wins + mmr.losses) * 100
                st.metric("Season Win Rate", f"{wr:.1f}% ({mmr.wins}W - {mmr.losses}L)")

            # Match History
            st.markdown("---")
            st.markdown("#### Recent Matches")
            matches = client.get_match_history(player_name, player_tag, player_region, size=5)

            if matches:
                for match in matches:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.write(f"🗺️ **{match.map}**")
                    with col2:
                        st.write(f"🔵 {match.team_blue_score} - {match.team_red_score} 🔴")
                    with col3:
                        st.write(f"⏱️ {match.duration // 60}min")
                    with col4:
                        st.write(f"🎮 {match.mode}")

                    # Player's stats in this match
                    player_match_stats = [p for p in match.players if p["name"].lower() == player_name.lower()]
                    if player_match_stats:
                        ps = player_match_stats[0]
                        st.caption(f"  → {ps['agent']} | {ps['kills']}/{ps['deaths']}/{ps['assists']} | Score: {ps['score']}")
                    st.markdown("---")
            else:
                st.info("No recent match history found.")

            client.close()

        except Exception as e:
            st.error(f"Error fetching player data: {str(e)}")
            st.caption("Make sure you have a valid HENRIK_API_KEY in your .env file, and the player name/tag are correct.")

# ─── Leaderboard ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🏅 Regional Leaderboard")

lb_region = st.selectbox("Leaderboard Region", ["na", "eu", "ap", "kr", "br"], key="lb_region")


@st.cache_data(ttl=3600, show_spinner="Fetching leaderboard...")
def load_leaderboard(region: str):
    from src.api_clients.henrik_api import HenrikAPIClient
    from data.db import Database

    db = Database()
    lb_df = db.get_leaderboard(region)

    if lb_df.empty or st.session_state.get("force_refresh"):
        try:
            client = HenrikAPIClient()
            entries = client.get_leaderboard(region)
            if entries:
                db.save_leaderboard(entries, region)
            lb_df = db.get_leaderboard(region)
            client.close()
        except Exception:
            pass
        st.session_state.pop("force_refresh", None)

    db.close()
    return lb_df


lb_df = load_leaderboard(lb_region)

if not lb_df.empty:
    st.dataframe(
        lb_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "rank": st.column_config.NumberColumn("#", width="small"),
            "name": st.column_config.TextColumn("Name"),
            "tag": st.column_config.TextColumn("Tag"),
            "tier": st.column_config.TextColumn("Tier"),
            "rr": st.column_config.NumberColumn("RR"),
            "wins": st.column_config.NumberColumn("Wins"),
            "games_played": st.column_config.NumberColumn("Games"),
        },
    )

    # Leaderboard viz
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            lb_df.head(20), x="name", y="rr",
            color="wins", color_continuous_scale="Viridis",
            title="Top 20 — RR Distribution",
        )
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "games_played" in lb_df.columns and lb_df["games_played"].sum() > 0:
            lb_df["win_rate"] = (lb_df["wins"] / lb_df["games_played"].replace(0, 1) * 100).round(1)
            fig2 = px.scatter(
                lb_df.head(50), x="rr", y="win_rate",
                hover_name="name", size="games_played",
                title="RR vs Win Rate",
                color="wins", color_continuous_scale="YlOrRd",
            )
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No leaderboard data. Ensure HENRIK_API_KEY is set in .env file.")
