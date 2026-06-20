"""Network Analysis — Transfer flows, co-play networks, team graphs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Network Analysis", page_icon="🕸️", layout="wide")
st.title("🕸️ Network Analysis")

timespan = st.session_state.get("timespan", "60d")


@st.cache_data(ttl=3600, show_spinner="Fetching transfer data...")
def load_transfers():
    from src.scrapers.liquipedia import LiquipediaScraper
    from data.db import Database

    db = Database()
    transfers_df = db.get_transfers()
    if transfers_df.empty or st.session_state.get("force_refresh"):
        try:
            with LiquipediaScraper() as scraper:
                transfers = scraper.get_recent_transfers(limit=80)
            if transfers:
                db.save_transfers(transfers)
            transfers_df = db.get_transfers()
        except Exception:
            pass
        st.session_state.pop("force_refresh", None)
    db.close()
    return transfers_df


@st.cache_data(ttl=1800)
def load_player_data(timespan: str):
    from data.db import Database
    db = Database()
    df = db.get_player_stats(timespan)
    db.close()
    return df


transfers_df = load_transfers()
players_df = load_player_data(timespan)

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔄 Transfer Network", "🤝 Co-Play Network", "⭐ Super Team Builder"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Transfer Network
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Transfer Flow Network")

    if transfers_df.empty:
        st.warning("No transfer data available. Liquipedia scraping may have been rate-limited. Try again later.")
    else:
        from src.analysis.network import (
            build_transfer_network, get_network_metrics,
            get_transfer_flow_data, get_team_centrality_rankings,
        )

        # Transfer table
        st.markdown("#### Recent Transfers")
        st.dataframe(transfers_df.head(30), use_container_width=True, hide_index=True)

        # Sankey diagram
        st.markdown("#### Transfer Flow (Sankey Diagram)")
        flow_data = get_transfer_flow_data(transfers_df)

        if not flow_data.empty:
            flow_top = flow_data.head(20)

            # Build label list
            all_teams = list(set(flow_top["source"].tolist() + flow_top["target"].tolist()))
            label_map = {team: idx for idx, team in enumerate(all_teams)}

            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15, thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_teams,
                    color="#ff4655",
                ),
                link=dict(
                    source=[label_map[s] for s in flow_top["source"]],
                    target=[label_map[t] for t in flow_top["target"]],
                    value=flow_top["value"].tolist(),
                    color="rgba(255, 70, 85, 0.3)",
                ),
            )])
            fig.update_layout(
                title="Player Transfer Flows Between Teams",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Team centrality
        st.markdown("#### Team Market Activity (Centrality)")
        centrality = get_team_centrality_rankings(transfers_df)
        if not centrality.empty:
            fig2 = px.scatter(
                centrality.head(20), x="in_degree", y="out_degree",
                size="betweenness", hover_name="team",
                color="net_flow", color_continuous_scale="RdYlGn",
                title="Transfer Market Activity (in vs out transfers)",
                labels={"in_degree": "Players Acquired", "out_degree": "Players Lost", "net_flow": "Net Flow"},
            )
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(centrality.head(15), use_container_width=True, hide_index=True)

        # Network metrics
        G = build_transfer_network(transfers_df)
        metrics = get_network_metrics(G)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Teams in Network", metrics.nodes)
        with col2:
            st.metric("Transfer Connections", metrics.edges)
        with col3:
            st.metric("Network Density", f"{metrics.density:.4f}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Co-Play Network
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Co-Play Network")
    st.markdown("Players connected by being on the same team — reveals team chemistry clusters.")

    if players_df.empty:
        st.warning("Need player data. Go to Player Stats page first.")
    else:
        from src.analysis.network import build_coplay_network, get_network_metrics

        G_coplay = build_coplay_network(players_df)
        metrics = get_network_metrics(G_coplay)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Players", metrics.nodes)
        with col2:
            st.metric("Connections", metrics.edges)
        with col3:
            st.metric("Density", f"{metrics.density:.4f}")
        with col4:
            st.metric("Communities", metrics.communities)

        # Most connected players
        if metrics.most_connected:
            st.markdown("#### Most Connected Players")
            connected_df = pd.DataFrame(metrics.most_connected, columns=["Player", "Connections"])
            fig3 = px.bar(
                connected_df, x="Player", y="Connections",
                title="Most Connected Players (by teammate count)",
                color_discrete_sequence=["#00d4ff"],
            )
            fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Super Team Builder
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ⭐ Super Team Builder")
    st.markdown("AI-identified top candidates for each role based on statistical profiles.")

    if players_df.empty:
        st.warning("Need player data. Go to Player Stats page first.")
    else:
        from src.analysis.network import find_super_team_candidates

        top_n = st.slider("Candidates per Role", 3, 10, 5)
        candidates = find_super_team_candidates(players_df, top_n=top_n)

        if not candidates.empty:
            for role in candidates["role"].unique():
                st.markdown(f"#### {role}")
                role_df = candidates[candidates["role"] == role][["player", "team", "role_score"]]
                st.dataframe(role_df, use_container_width=True, hide_index=True)
        else:
            st.info("Insufficient data for super team analysis.")
