"""Reusable Plotly chart builders."""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np


DARK_TEMPLATE = "plotly_dark"
BG_TRANSPARENT = "rgba(0,0,0,0)"
VALORANT_RED = "#ff4655"
VALORANT_BLUE = "#00d4ff"
VALORANT_GOLD = "#ffd700"


def apply_dark_style(fig):
    """Apply consistent dark styling to any figure."""
    fig.update_layout(
        template=DARK_TEMPLATE,
        paper_bgcolor=BG_TRANSPARENT,
        plot_bgcolor=BG_TRANSPARENT,
        font=dict(color="#e2e8f0"),
    )
    return fig


def radar_chart(categories: list[str], values1: list[float], values2: list[float],
                name1: str, name2: str, title: str = "") -> go.Figure:
    """Create a comparison radar chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values1 + [values1[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=name1,
        line_color=VALORANT_RED,
        fillcolor="rgba(255, 70, 85, 0.2)",
    ))
    fig.add_trace(go.Scatterpolar(
        r=values2 + [values2[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name=name2,
        line_color=VALORANT_BLUE,
        fillcolor="rgba(0, 212, 255, 0.2)",
    ))
    fig.update_layout(
        polar=dict(bgcolor=BG_TRANSPARENT, radialaxis=dict(visible=True, range=[0, 1])),
        title=title,
    )
    return apply_dark_style(fig)


def horizontal_bar(df: pd.DataFrame, x: str, y: str, title: str,
                   color: str = None, color_scale: str = "Reds") -> go.Figure:
    """Horizontal bar chart."""
    fig = px.bar(df, x=x, y=y, orientation="h", color=color, color_continuous_scale=color_scale, title=title)
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return apply_dark_style(fig)


def scatter_with_size(df: pd.DataFrame, x: str, y: str, size: str,
                      hover_name: str, title: str, color: str = None) -> go.Figure:
    """Scatter plot with size encoding."""
    fig = px.scatter(df, x=x, y=y, size=size, hover_name=hover_name, color=color,
                     color_continuous_scale="Viridis", title=title)
    return apply_dark_style(fig)


def correlation_heatmap(corr_matrix: pd.DataFrame, title: str = "Correlation Matrix") -> go.Figure:
    """Correlation heatmap."""
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns.tolist(),
        y=corr_matrix.index.tolist(),
        colorscale="RdBu",
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate="%{text}",
    ))
    fig.update_layout(title=title, height=500)
    return apply_dark_style(fig)


def win_probability_gauge(team1: str, prob1: float, team2: str) -> go.Figure:
    """Win probability as a bullet/gauge chart."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=[prob1 * 100],
        y=[""],
        orientation="h",
        marker_color=VALORANT_RED,
        name=team1,
        text=f"{team1}: {prob1*100:.1f}%",
        textposition="inside",
    ))
    fig.add_trace(go.Bar(
        x=[(1 - prob1) * 100],
        y=[""],
        orientation="h",
        marker_color=VALORANT_BLUE,
        name=team2,
        text=f"{team2}: {(1-prob1)*100:.1f}%",
        textposition="inside",
    ))

    fig.update_layout(barmode="stack", showlegend=False, height=100, margin=dict(t=20, b=20))
    return apply_dark_style(fig)


def timeline_chart(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    """Line chart for time-series data."""
    fig = px.line(df, x=x, y=y, title=title, line_shape="spline")
    fig.update_traces(line_color=VALORANT_RED)
    fig.add_hline(y=df[y].mean(), line_dash="dash", line_color="gray", annotation_text="Average")
    return apply_dark_style(fig)
