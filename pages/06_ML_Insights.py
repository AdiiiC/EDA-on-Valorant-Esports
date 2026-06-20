"""ML Insights — Clustering, win predictions, forecasting."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="ML Insights", page_icon="🤖", layout="wide")
st.title("🤖 ML-Powered Insights")

timespan = st.session_state.get("timespan", "60d")


@st.cache_data(ttl=1800)
def load_data(timespan: str):
    from data.db import Database
    db = Database()
    players = db.get_player_stats(timespan)
    matches = db.get_matches()
    db.close()
    return players, matches


players_df, matches_df = load_data(timespan)

if players_df.empty:
    st.warning("No player data available. Go to Player Stats page first.")
    st.stop()

# ─── Tab Layout ──────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎯 Player Clustering", "📈 Win Predictor", "🔮 Forecasting"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Player Clustering
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Player Playstyle Clustering")
    st.markdown("Using K-Means to group players into playstyle archetypes based on their performance metrics.")

    from src.models.clustering import (
        cluster_players_kmeans, get_pca_projection, get_cluster_profiles, find_optimal_k, prepare_features
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        n_clusters = st.slider("Number of Clusters", 2, 7, 4)
        use_auto_k = st.checkbox("Auto-detect K", value=False)

    if use_auto_k:
        _, scaled, _ = prepare_features(players_df)
        n_clusters = find_optimal_k(scaled)
        st.info(f"Optimal K detected: **{n_clusters}**")

    clustered_df = cluster_players_kmeans(players_df, n_clusters=n_clusters)

    # PCA Projection
    pca_result, explained_var = get_pca_projection(clustered_df)
    pca_result["cluster"] = clustered_df["cluster"].values
    pca_result["cluster_label"] = clustered_df["cluster_label"].values

    fig = px.scatter(
        pca_result, x="PC1", y="PC2",
        color="cluster_label", hover_name="player",
        title=f"Player Clusters (PCA — {sum(explained_var[:2])*100:.1f}% variance explained)",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Cluster Profiles
    st.markdown("#### Cluster Profiles (Mean Stats)")
    profiles = get_cluster_profiles(clustered_df)
    if not profiles.empty:
        st.dataframe(profiles, use_container_width=True)

    # Players per cluster
    st.markdown("#### Players per Cluster")
    selected_cluster = st.selectbox("Select Cluster", sorted(clustered_df["cluster_label"].unique()))
    cluster_players = clustered_df[clustered_df["cluster_label"] == selected_cluster][["player", "team", "acs", "kd", "adr", "rating"]]
    st.dataframe(cluster_players.sort_values("rating", ascending=False), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Win Predictor
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Match Win Probability Predictor")
    st.markdown("Uses team average stats to predict head-to-head outcomes.")

    from src.models.win_predictor import WinPredictor, get_head_to_head

    teams_available = sorted(players_df["team"].unique().tolist())

    if len(teams_available) < 2:
        st.warning("Need at least 2 teams with player data.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            team1 = st.selectbox("Team 1", teams_available, index=0)
        with col2:
            team2 = st.selectbox("Team 2", teams_available, index=min(1, len(teams_available) - 1))

        if team1 != team2:
            predictor = WinPredictor()

            # Train if we have match data
            if not matches_df.empty:
                predictor.train(matches_df, players_df)

            result = predictor.predict(team1, team2, players_df)

            # Display prediction
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                st.metric(team1, f"{result.team1_win_prob * 100:.1f}%")
            with col2:
                st.markdown("### vs")
            with col3:
                st.metric(team2, f"{result.team2_win_prob * 100:.1f}%")

            # Win probability bar
            fig = go.Figure(go.Bar(
                x=[result.team1_win_prob * 100, result.team2_win_prob * 100],
                y=[team1, team2],
                orientation="h",
                marker_color=["#ff4655", "#00d4ff"],
            ))
            fig.update_layout(
                title="Win Probability",
                xaxis_title="Probability %",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"**Confidence:** {result.confidence}")
            st.markdown("**Key Factors:**")
            for factor in result.key_factors:
                st.markdown(f"- {factor}")

            # Head to head
            if not matches_df.empty:
                h2h = get_head_to_head(matches_df, team1, team2)
                if h2h["matches"] > 0:
                    st.markdown(f"**H2H Record:** {team1} {h2h['team1_wins']} - {h2h['team2_wins']} {team2} ({h2h['matches']} matches)")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Forecasting
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Team Performance Forecasting")

    from src.models.forecasting import compute_elo_ratings, compute_rolling_performance, forecast_rating

    if matches_df.empty:
        st.warning("Need match data for forecasting. Go to Match Results page first.")
    else:
        # Compute Elo ratings
        elo_ratings = compute_elo_ratings(matches_df)
        elo_df = pd.DataFrame([
            {"team": team, "elo": round(elo, 1)}
            for team, elo in sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)
        ])

        st.markdown("#### Computed Elo Ratings (from match history)")
        fig = px.bar(
            elo_df.head(20), x="team", y="elo",
            color="elo", color_continuous_scale="RdYlGn",
            title="Elo Ratings — Top 20 Teams",
        )
        fig.add_hline(y=1500, line_dash="dash", line_color="gray", annotation_text="Baseline")
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Rolling performance for selected team
        st.markdown("#### Rolling Win Rate")
        team_for_forecast = st.selectbox("Select Team", elo_df["team"].tolist()[:20])

        rolling = compute_rolling_performance(matches_df, team_for_forecast, window=5)
        if not rolling.empty:
            fig2 = px.line(
                rolling, x="match_num", y="rolling_wr",
                title=f"Rolling Win Rate — {team_for_forecast} (5-match window)",
                labels={"match_num": "Match #", "rolling_wr": "Win Rate"},
            )
            fig2.add_hline(y=0.5, line_dash="dash", line_color="gray")
            fig2.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Forecast
            history = rolling["rolling_wr"].tolist()
            forecast = forecast_rating(history, periods=5)
            st.markdown(f"**Trend:** {forecast.trend.upper()}")
            st.markdown(f"**Forecast (next 5):** {forecast.forecasted_ratings}")
            st.markdown(f"**95% CI:** {forecast.confidence_interval}")
