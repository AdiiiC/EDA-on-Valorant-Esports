"""Agent & Map Meta — Pick rates, win rates, map statistics."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Agent & Map Meta", page_icon="🕵️", layout="wide")
st.title("🕵️ Agent & Map Meta")

timespan = st.session_state.get("timespan", "60d")


@st.cache_data(ttl=3600, show_spinner="Fetching agent stats...")
def load_agent_stats(timespan: str):
    from src.scrapers.vlr_scraper import VLRScraper
    from data.db import Database

    db = Database()
    agent_df = db.get_agent_stats(timespan)
    if agent_df.empty or st.session_state.get("force_refresh"):
        with VLRScraper() as scraper:
            agents = scraper.get_agent_stats(timespan=timespan)
        if agents:
            db.save_agent_stats(agents, timespan)
        agent_df = db.get_agent_stats(timespan)
        st.session_state.pop("force_refresh", None)
    db.close()
    return agent_df


@st.cache_data(ttl=3600, show_spinner="Fetching map stats...")
def load_map_stats(timespan: str):
    from src.scrapers.vlr_scraper import VLRScraper
    from data.db import Database

    db = Database()
    map_df = db.get_map_stats(timespan)
    if map_df.empty or st.session_state.get("force_refresh"):
        with VLRScraper() as scraper:
            maps = scraper.get_map_stats(timespan=timespan)
        if maps:
            db.save_map_stats(maps, timespan)
        map_df = db.get_map_stats(timespan)
    db.close()
    return map_df


# ─── Agent Section ───────────────────────────────────────────────────────────
st.markdown("## 🎭 Agent Meta")
agent_df = load_agent_stats(timespan)

if not agent_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            agent_df.sort_values("pick_rate", ascending=False),
            x="agent", y="pick_rate",
            color="win_rate", color_continuous_scale="RdYlGn",
            title="Agent Pick Rates (colored by Win Rate)",
            labels={"pick_rate": "Pick Rate %", "win_rate": "Win Rate %"},
        )
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.scatter(
            agent_df, x="pick_rate", y="win_rate",
            size="avg_acs", hover_name="agent",
            color="avg_acs", color_continuous_scale="Viridis",
            title="Pick Rate vs Win Rate (size = avg ACS)",
            labels={"pick_rate": "Pick Rate %", "win_rate": "Win Rate %"},
        )
        fig2.add_hline(y=50, line_dash="dash", line_color="gray")
        fig2.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Agent tier list
    st.markdown("#### Agent Tier List")
    agent_df_sorted = agent_df.sort_values("win_rate", ascending=False).copy()
    agent_df_sorted["tier"] = pd.cut(
        agent_df_sorted["win_rate"],
        bins=[0, 45, 48, 51, 54, 100],
        labels=["D", "C", "B", "A", "S"],
    )
    st.dataframe(
        agent_df_sorted[["agent", "pick_rate", "win_rate", "avg_acs", "tier"]],
        use_container_width=True, hide_index=True,
    )
else:
    st.info("No agent data available. Data will be fetched on next refresh.")

# ─── Map Section ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🗺️ Map Meta")
map_df = load_map_stats(timespan)

if not map_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        fig3 = px.bar(
            map_df.sort_values("times_played", ascending=False),
            x="map", y="times_played",
            title="Map Play Frequency",
            color_discrete_sequence=["#ff4655"],
        )
        fig3.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        # ATK vs DEF win rate
        map_balance = map_df.melt(
            id_vars=["map"], value_vars=["atk_win_rate", "def_win_rate"],
            var_name="side", value_name="win_rate",
        )
        map_balance["side"] = map_balance["side"].map({"atk_win_rate": "Attack", "def_win_rate": "Defense"})

        fig4 = px.bar(
            map_balance, x="map", y="win_rate", color="side",
            barmode="group", title="Attack vs Defense Win Rate by Map",
            color_discrete_map={"Attack": "#ff4655", "Defense": "#00d4ff"},
        )
        fig4.add_hline(y=50, line_dash="dash", line_color="gray")
        fig4.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.dataframe(map_df, use_container_width=True, hide_index=True)
else:
    st.info("No map data available. Data will be fetched on next refresh.")
