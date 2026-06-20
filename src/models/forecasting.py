"""
Time-series Forecasting — predict team ranking trajectories.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from dataclasses import dataclass


@dataclass
class ForecastResult:
    team: str
    current_rating: float
    forecasted_ratings: list[float]
    trend: str  # "rising", "falling", "stable"
    confidence_interval: tuple[float, float]


def compute_elo_ratings(matches_df: pd.DataFrame, k_factor: float = 32) -> dict[str, float]:
    """
    Compute Elo ratings from match history.
    Returns dict of team -> elo rating.
    """
    ratings: dict[str, float] = {}
    DEFAULT_ELO = 1500.0

    for _, match in matches_df.iterrows():
        t1 = match["team1"]
        t2 = match["team2"]

        if t1 not in ratings:
            ratings[t1] = DEFAULT_ELO
        if t2 not in ratings:
            ratings[t2] = DEFAULT_ELO

        r1 = ratings[t1]
        r2 = ratings[t2]

        # Expected scores
        e1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
        e2 = 1 - e1

        # Actual scores
        s1 = match["score1"]
        s2 = match["score2"]
        if s1 > s2:
            actual1, actual2 = 1.0, 0.0
        elif s2 > s1:
            actual1, actual2 = 0.0, 1.0
        else:
            actual1, actual2 = 0.5, 0.5

        # Update
        ratings[t1] = r1 + k_factor * (actual1 - e1)
        ratings[t2] = r2 + k_factor * (actual2 - e2)

    return ratings


def compute_rolling_performance(matches_df: pd.DataFrame, team: str, window: int = 10) -> pd.DataFrame:
    """Compute rolling win rate for a team."""
    team_matches = matches_df[
        (matches_df["team1"] == team) | (matches_df["team2"] == team)
    ].copy()

    if team_matches.empty:
        return pd.DataFrame(columns=["match_num", "win", "rolling_wr"])

    team_matches["win"] = (
        ((team_matches["team1"] == team) & (team_matches["score1"] > team_matches["score2"])) |
        ((team_matches["team2"] == team) & (team_matches["score2"] > team_matches["score1"]))
    ).astype(int)

    team_matches["match_num"] = range(1, len(team_matches) + 1)
    team_matches["rolling_wr"] = team_matches["win"].rolling(window=window, min_periods=1).mean()

    return team_matches[["match_num", "win", "rolling_wr"]].reset_index(drop=True)


def forecast_rating(history: list[float], periods: int = 5) -> ForecastResult:
    """
    Simple linear trend forecast for a team's rating trajectory.
    Uses last N data points to project forward.
    """
    if len(history) < 3:
        current = history[-1] if history else 0
        return ForecastResult(
            team="",
            current_rating=current,
            forecasted_ratings=[current] * periods,
            trend="stable",
            confidence_interval=(current - 50, current + 50),
        )

    X = np.arange(len(history)).reshape(-1, 1)
    y = np.array(history)

    model = LinearRegression()
    model.fit(X, y)

    # Forecast
    future_X = np.arange(len(history), len(history) + periods).reshape(-1, 1)
    forecasted = model.predict(future_X).tolist()

    # Trend
    slope = model.coef_[0]
    if slope > 5:
        trend = "rising"
    elif slope < -5:
        trend = "falling"
    else:
        trend = "stable"

    # Simple CI based on residual std
    residuals = y - model.predict(X)
    std_err = np.std(residuals)
    ci = (forecasted[-1] - 1.96 * std_err, forecasted[-1] + 1.96 * std_err)

    return ForecastResult(
        team="",
        current_rating=history[-1],
        forecasted_ratings=[round(f, 1) for f in forecasted],
        trend=trend,
        confidence_interval=(round(ci[0], 1), round(ci[1], 1)),
    )


def detect_breakout_players(player_stats_df: pd.DataFrame, threshold_percentile: float = 90) -> pd.DataFrame:
    """
    Detect players whose stats are anomalously high compared to peers.
    These are 'breakout' performers.
    """
    if player_stats_df.empty:
        return pd.DataFrame()

    metrics = ["acs", "kd", "adr", "rating"]
    available_metrics = [m for m in metrics if m in player_stats_df.columns]

    if not available_metrics:
        return pd.DataFrame()

    result = player_stats_df.copy()
    result["breakout_score"] = 0.0

    for metric in available_metrics:
        threshold = np.percentile(result[metric].dropna(), threshold_percentile)
        result["breakout_score"] += (result[metric] >= threshold).astype(float)

    # Normalize
    result["breakout_score"] = result["breakout_score"] / len(available_metrics)
    breakouts = result[result["breakout_score"] >= 0.5].sort_values("breakout_score", ascending=False)

    return breakouts
