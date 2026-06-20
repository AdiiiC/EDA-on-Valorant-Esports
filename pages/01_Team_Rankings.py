"""Team Rankings — Live global team rankings from VLR.gg."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Team Rankings", page_icon="🏆", layout="wide")
st.title("🏆 Team Rankings")

region = st.session_state.get("region", "all")

# ─── Fetch Data ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Fetching live team rankings...")
def load_team_rankings(region: str):
    from src.scrapers.vlr_scraper import VLRScraper
    from data.db import Database

    db = Database()
    if db.team_rankings_stale(region) or st.session_state.get("force_refresh"):
        with VLRScraper() as scraper:
            rankings = scraper.get_team_rankings(region)
        if rankings:
            db.save_team_rankings(rankings, region)
        st.session_state.pop("force_refresh", None)

    df = db.get_team_rankings(region)
    db.close()
    return df


df = load_team_rankings(region)

if df.empty:
    st.warning("No ranking data available. Try a different region or refresh.")
    st.stop()

# ─── Filters ─────────────────────────────────────────────────────────────────
st.sidebar.markdown("### Filters")
top_n = st.sidebar.slider("Show Top N Teams", 5, 50, 20)
df_display = df.head(top_n)

# ─── Rankings Table ──────────────────────────────────────────────────────────
st.markdown(f"### Top {top_n} Teams — Region: `{region.upper()}`")
st.dataframe(
    df_display[["rank", "team", "country", "rating", "earnings"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "rank": st.column_config.NumberColumn("Rank", width="small"),
        "team": st.column_config.TextColumn("Team", width="medium"),
        "country": st.column_config.TextColumn("Country"),
        "rating": st.column_config.NumberColumn("Rating", format="%.0f"),
        "earnings": st.column_config.TextColumn("Earnings"),
    },
)

# ─── Visualizations ──────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Rating Distribution")
    fig = px.bar(
        df_display, x="team", y="rating",
        color="rating", color_continuous_scale="Reds",
        title="Team Ratings",
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("#### Rating vs Rank")
    fig2 = px.scatter(
        df_display, x="rank", y="rating", size="rating",
        hover_name="team", color="rating",
        color_continuous_scale="RdYlGn",
        title="Rating Decay by Rank",
    )
    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── Country Distribution ────────────────────────────────────────────────────
if "country" in df.columns and df["country"].notna().any():
    st.markdown("#### Teams by Country/Region")
    country_counts = df["country"].value_counts().head(15)
    fig3 = px.pie(
        values=country_counts.values,
        names=country_counts.index,
        title="Geographic Distribution of Top Teams",
        color_discrete_sequence=px.colors.sequential.Reds,
    )
    fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig3, use_container_width=True)
