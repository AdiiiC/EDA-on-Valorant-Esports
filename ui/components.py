"""Reusable Streamlit UI components."""

import streamlit as st
import pandas as pd


def metric_row(metrics: list[tuple[str, str | int | float]]):
    """Display a row of metrics."""
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)


def player_card(player_data: dict):
    """Display a player info card."""
    st.markdown(f"""
    <div style="background: #1f2937; padding: 1rem; border-radius: 10px; border-left: 4px solid #ff4655;">
        <h3 style="margin: 0; color: white;">{player_data.get('player', 'Unknown')}</h3>
        <p style="color: #94a3b8; margin: 0.25rem 0;">{player_data.get('team', '')}</p>
        <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
            <span style="color: #ff4655;">ACS: {player_data.get('acs', 0):.1f}</span>
            <span style="color: #00d4ff;">K/D: {player_data.get('kd', 0):.2f}</span>
            <span style="color: #ffd700;">Rating: {player_data.get('rating', 0):.2f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def match_card(team1: str, score1: int, team2: str, score2: int, event: str, date: str):
    """Display a match result card."""
    winner = team1 if score1 > score2 else team2
    t1_style = "color: #22c55e; font-weight: bold;" if score1 > score2 else "color: #ef4444;"
    t2_style = "color: #22c55e; font-weight: bold;" if score2 > score1 else "color: #ef4444;"

    st.markdown(f"""
    <div style="background: #1f2937; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="{t1_style}">{team1}</span>
            <span style="color: white; font-size: 1.2rem;">{score1} - {score2}</span>
            <span style="{t2_style}">{team2}</span>
        </div>
        <div style="color: #64748b; font-size: 0.8rem; margin-top: 0.5rem;">
            {event} • {date}
        </div>
    </div>
    """, unsafe_allow_html=True)


def data_freshness_indicator(last_fetched: float | None):
    """Show how fresh the data is."""
    import time
    if last_fetched is None:
        st.caption("⚪ No data loaded")
        return

    age = time.time() - last_fetched
    if age < 300:
        st.caption("🟢 Data is fresh (< 5 min)")
    elif age < 3600:
        st.caption(f"🟡 Data is {int(age // 60)} min old")
    else:
        st.caption(f"🔴 Data is {int(age // 3600)} hours old — consider refreshing")


def error_boundary(func):
    """Decorator to catch and display errors gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.caption("Try refreshing the page or check your configuration.")
    return wrapper
