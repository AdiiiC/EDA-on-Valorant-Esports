"""Player Comparison — Side-by-side radar charts and percentile analysis."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Player Comparison", page_icon="⚔️", layout="wide")
st.title("⚔️ Player Comparison")

timespan = st.session_state.get("timespan", "60d")


@st.cache_data(ttl=1800)
def load_players(timespan: str):
    from data.db import Database
    db = Database()
    df = db.get_player_stats(timespan)
    db.close()
    return df


df = load_players(timespan)

if df.empty:
    st.warning("No player data. Go to Player Stats page first to fetch data.")
    st.stop()

# ─── Player Selection ────────────────────────────────────────────────────────
players_list = sorted(df["player"].unique().tolist())

col1, col2 = st.columns(2)
with col1:
    player1 = st.selectbox("Player 1", players_list, index=0)
with col2:
    default_idx = min(1, len(players_list) - 1)
    player2 = st.selectbox("Player 2", players_list, index=default_idx)

if player1 == player2:
    st.warning("Select two different players to compare.")
    st.stop()

# ─── Get Player Data ─────────────────────────────────────────────────────────
p1 = df[df["player"] == player1].iloc[0]
p2 = df[df["player"] == player2].iloc[0]

metrics = ["acs", "kd", "adr", "kast", "kpr", "apr", "fkpr", "headshot_pct", "clutch_pct", "rating"]
metric_labels = ["ACS", "K/D", "ADR", "KAST%", "KPR", "APR", "FKPR", "HS%", "Clutch%", "Rating"]

# ─── Radar Chart ─────────────────────────────────────────────────────────────
st.markdown("### Radar Comparison")


def normalize_for_radar(values, metric_list, dataframe):
    """Normalize values to 0-1 range for radar chart."""
    normalized = []
    for val, metric in zip(values, metric_list):
        col_min = dataframe[metric].min()
        col_max = dataframe[metric].max()
        if col_max - col_min == 0:
            normalized.append(0.5)
        else:
            normalized.append((val - col_min) / (col_max - col_min))
    return normalized


p1_values = [p1[m] for m in metrics]
p2_values = [p2[m] for m in metrics]

p1_norm = normalize_for_radar(p1_values, metrics, df)
p2_norm = normalize_for_radar(p2_values, metrics, df)

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=p1_norm + [p1_norm[0]],
    theta=metric_labels + [metric_labels[0]],
    fill="toself",
    name=player1,
    line_color="#ff4655",
    fillcolor="rgba(255, 70, 85, 0.2)",
))
fig.add_trace(go.Scatterpolar(
    r=p2_norm + [p2_norm[0]],
    theta=metric_labels + [metric_labels[0]],
    fill="toself",
    name=player2,
    line_color="#00d4ff",
    fillcolor="rgba(0, 212, 255, 0.2)",
))
fig.update_layout(
    polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(visible=True, range=[0, 1], showticklabels=False),
    ),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    showlegend=True,
    title=f"{player1} vs {player2}",
)
st.plotly_chart(fig, use_container_width=True)

# ─── Detailed Comparison Table ───────────────────────────────────────────────
st.markdown("### Detailed Stats Comparison")

from src.analysis.stats import compare_players
comparison = compare_players(df, player1, player2)

if not comparison.empty:
    st.dataframe(comparison, use_container_width=True, hide_index=True)
else:
    # Fallback manual comparison
    comp_data = []
    for m, label in zip(metrics, metric_labels):
        from scipy.stats import percentileofscore
        p1_pct = percentileofscore(df[m].dropna(), p1[m])
        p2_pct = percentileofscore(df[m].dropna(), p2[m])
        comp_data.append({
            "Metric": label,
            player1: round(p1[m], 2),
            f"{player1} %ile": round(p1_pct, 1),
            player2: round(p2[m], 2),
            f"{player2} %ile": round(p2_pct, 1),
            "Advantage": player1 if p1[m] > p2[m] else player2,
        })
    st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

# ─── Percentile Bar Chart ────────────────────────────────────────────────────
st.markdown("### Percentile Rankings")
from scipy.stats import percentileofscore

pct_data = []
for m, label in zip(metrics, metric_labels):
    pct_data.append({"Metric": label, "Player": player1, "Percentile": percentileofscore(df[m].dropna(), p1[m])})
    pct_data.append({"Metric": label, "Player": player2, "Percentile": percentileofscore(df[m].dropna(), p2[m])})

pct_df = pd.DataFrame(pct_data)
fig2 = go.Figure()
for player, color in [(player1, "#ff4655"), (player2, "#00d4ff")]:
    pdata = pct_df[pct_df["Player"] == player]
    fig2.add_trace(go.Bar(
        x=pdata["Metric"], y=pdata["Percentile"],
        name=player, marker_color=color, opacity=0.8,
    ))
fig2.update_layout(
    barmode="group", template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    title="Percentile Rankings Comparison",
    yaxis_title="Percentile",
)
st.plotly_chart(fig2, use_container_width=True)
