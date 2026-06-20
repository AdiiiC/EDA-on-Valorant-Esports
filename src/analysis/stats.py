"""
Statistical Analysis — correlations, distributions, percentile rankings.
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


def compute_percentile_ranks(df: pd.DataFrame, metrics: list[str] = None) -> pd.DataFrame:
    """Compute percentile ranks for each player across all metrics."""
    if metrics is None:
        metrics = ["acs", "kd", "adr", "kast", "kpr", "apr", "fkpr", "headshot_pct", "clutch_pct", "rating"]

    available = [m for m in metrics if m in df.columns]
    result = df[["player", "team"]].copy()

    for metric in available:
        result[f"{metric}_percentile"] = df[metric].rank(pct=True).round(3) * 100

    # Overall percentile (mean of all percentile ranks)
    pct_cols = [c for c in result.columns if c.endswith("_percentile")]
    result["overall_percentile"] = result[pct_cols].mean(axis=1).round(1)

    return result.sort_values("overall_percentile", ascending=False).reset_index(drop=True)


def compute_correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Compute correlation matrix for numeric stat columns."""
    numeric_cols = ["acs", "kd", "adr", "kast", "kpr", "apr", "fkpr", "fdpr", "headshot_pct", "clutch_pct", "rating"]
    available = [c for c in numeric_cols if c in df.columns]
    return df[available].corr().round(3)


def compute_stat_distributions(df: pd.DataFrame) -> dict:
    """Compute distribution stats (mean, std, skew, kurtosis) for each metric."""
    metrics = ["acs", "kd", "adr", "kast", "kpr", "apr", "fkpr", "fdpr", "headshot_pct", "rating"]
    available = [m for m in metrics if m in df.columns]

    distributions = {}
    for metric in available:
        values = df[metric].dropna()
        distributions[metric] = {
            "mean": round(values.mean(), 2),
            "std": round(values.std(), 2),
            "median": round(values.median(), 2),
            "skew": round(values.skew(), 3),
            "kurtosis": round(values.kurtosis(), 3),
            "q25": round(values.quantile(0.25), 2),
            "q75": round(values.quantile(0.75), 2),
            "min": round(values.min(), 2),
            "max": round(values.max(), 2),
        }
    return distributions


def compare_players(df: pd.DataFrame, player1: str, player2: str) -> pd.DataFrame:
    """Side-by-side comparison of two players with percentile context."""
    p1_data = df[df["player"] == player1]
    p2_data = df[df["player"] == player2]

    if p1_data.empty or p2_data.empty:
        return pd.DataFrame()

    metrics = ["acs", "kd", "adr", "kast", "kpr", "apr", "fkpr", "fdpr", "headshot_pct", "clutch_pct", "rating"]
    available = [m for m in metrics if m in df.columns]

    comparison = []
    for metric in available:
        p1_val = p1_data[metric].values[0]
        p2_val = p2_data[metric].values[0]
        league_avg = df[metric].mean()
        p1_pct = scipy_stats.percentileofscore(df[metric].dropna(), p1_val)
        p2_pct = scipy_stats.percentileofscore(df[metric].dropna(), p2_val)

        comparison.append({
            "metric": metric,
            player1: round(p1_val, 2),
            f"{player1}_percentile": round(p1_pct, 1),
            player2: round(p2_val, 2),
            f"{player2}_percentile": round(p2_pct, 1),
            "league_avg": round(league_avg, 2),
            "advantage": player1 if p1_val > p2_val else player2,
        })

    return pd.DataFrame(comparison)


def region_performance_summary(team_rankings_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize performance by region."""
    if "region" not in team_rankings_df.columns:
        return pd.DataFrame()

    summary = team_rankings_df.groupby("region").agg(
        num_teams=("team", "count"),
        avg_rating=("rating", "mean"),
        top_team=("team", "first"),
        best_rank=("rank", "min"),
    ).round(2).sort_values("avg_rating", ascending=False)

    return summary.reset_index()


def compute_consistency_score(player_stats_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a 'consistency score' — players with low variance relative to mean
    are more consistent performers.
    """
    metrics = ["acs", "kd", "adr", "rating"]
    available = [m for m in metrics if m in player_stats_df.columns]

    if not available:
        return player_stats_df

    result = player_stats_df[["player", "team"]].copy()

    # Use coefficient of variation (lower = more consistent)
    # Since we have snapshot data, use distance from median as proxy
    for metric in available:
        median_val = player_stats_df[metric].median()
        result[f"{metric}_consistency"] = 1 - abs(player_stats_df[metric] - median_val) / (player_stats_df[metric].std() + 1e-8)

    consistency_cols = [c for c in result.columns if c.endswith("_consistency")]
    result["overall_consistency"] = result[consistency_cols].mean(axis=1).round(3)

    return result.sort_values("overall_consistency", ascending=False).reset_index(drop=True)
