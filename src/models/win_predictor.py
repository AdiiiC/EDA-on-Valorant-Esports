"""
Win Probability Predictor — logistic regression + gradient boosting for match outcomes.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass


@dataclass
class PredictionResult:
    team1: str
    team2: str
    team1_win_prob: float
    team2_win_prob: float
    confidence: str
    key_factors: list[str]


class WinPredictor:
    """Predict match outcomes from team/player stats."""

    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=100, max_depth=4, random_state=42, learning_rate=0.1
        )
        self.scaler = StandardScaler()
        self.feature_names: list[str] = []
        self.is_fitted = False

    def _build_features(self, team_stats: pd.DataFrame) -> pd.DataFrame:
        """Build team-level features from player stats."""
        features = team_stats.groupby("team").agg({
            "acs": "mean",
            "kd": "mean",
            "adr": "mean",
            "kast": "mean",
            "kpr": "mean",
            "apr": "mean",
            "fkpr": "mean",
            "fdpr": "mean",
            "headshot_pct": "mean",
            "clutch_pct": "mean",
            "rating": "mean",
        }).reset_index()

        features.columns = ["team"] + [f"avg_{c}" for c in features.columns[1:]]
        return features

    def _build_matchup_features(self, team1_stats: dict, team2_stats: dict) -> np.ndarray:
        """Create differential features for a matchup."""
        feature_keys = ["avg_acs", "avg_kd", "avg_adr", "avg_kast", "avg_kpr",
                        "avg_apr", "avg_fkpr", "avg_fdpr", "avg_rating"]
        diffs = []
        for key in feature_keys:
            diffs.append(team1_stats.get(key, 0) - team2_stats.get(key, 0))
        return np.array(diffs).reshape(1, -1)

    def train(self, matches_df: pd.DataFrame, player_stats_df: pd.DataFrame):
        """
        Train on historical match data.
        matches_df needs: team1, team2, score1, score2
        player_stats_df needs: player, team, + stat columns
        """
        if matches_df.empty or player_stats_df.empty:
            return

        team_features = self._build_features(player_stats_df)
        team_dict = team_features.set_index("team").to_dict("index")

        X_list = []
        y_list = []

        for _, match in matches_df.iterrows():
            t1 = match["team1"]
            t2 = match["team2"]

            if t1 not in team_dict or t2 not in team_dict:
                continue

            features = self._build_matchup_features(team_dict[t1], team_dict[t2])
            X_list.append(features.flatten())

            # 1 if team1 wins, 0 if team2 wins
            y_list.append(1 if match["score1"] > match["score2"] else 0)

        if len(X_list) < 10:
            return

        X = np.array(X_list)
        y = np.array(y_list)

        self.feature_names = ["diff_acs", "diff_kd", "diff_adr", "diff_kast", "diff_kpr",
                              "diff_apr", "diff_fkpr", "diff_fdpr", "diff_rating"]

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        self.model.fit(X_scaled, y)
        self.is_fitted = True

        # Cross-val score
        scores = cross_val_score(self.model, X_scaled, y, cv=min(5, len(y) // 2), scoring="accuracy")
        self.cv_accuracy = scores.mean()

    def predict(self, team1: str, team2: str, player_stats_df: pd.DataFrame) -> PredictionResult:
        """Predict win probability for a matchup."""
        team_features = self._build_features(player_stats_df)
        team_dict = team_features.set_index("team").to_dict("index")

        if team1 not in team_dict or team2 not in team_dict:
            return PredictionResult(
                team1=team1, team2=team2,
                team1_win_prob=0.5, team2_win_prob=0.5,
                confidence="Insufficient data",
                key_factors=["Missing team stats"],
            )

        features = self._build_matchup_features(team_dict[team1], team_dict[team2])

        if not self.is_fitted:
            # Heuristic fallback: use rating difference
            r1 = team_dict[team1].get("avg_rating", 1.0)
            r2 = team_dict[team2].get("avg_rating", 1.0)
            diff = r1 - r2
            prob1 = 1 / (1 + np.exp(-diff * 5))
            return PredictionResult(
                team1=team1, team2=team2,
                team1_win_prob=round(prob1, 3),
                team2_win_prob=round(1 - prob1, 3),
                confidence="Heuristic (no training data)",
                key_factors=[f"Rating diff: {diff:.3f}"],
            )

        features_scaled = self.scaler.transform(features)
        proba = self.model.predict_proba(features_scaled)[0]

        # Key factors from feature importances
        importances = self.model.feature_importances_
        top_idx = np.argsort(importances)[::-1][:3]
        key_factors = []
        for idx in top_idx:
            fname = self.feature_names[idx]
            val = features.flatten()[idx]
            direction = "favors " + team1 if val > 0 else "favors " + team2
            key_factors.append(f"{fname}: {val:.2f} ({direction})")

        confidence = "High" if abs(proba[1] - 0.5) > 0.2 else "Medium" if abs(proba[1] - 0.5) > 0.1 else "Low"

        return PredictionResult(
            team1=team1, team2=team2,
            team1_win_prob=round(proba[1], 3),
            team2_win_prob=round(proba[0], 3),
            confidence=confidence,
            key_factors=key_factors,
        )


def get_head_to_head(matches_df: pd.DataFrame, team1: str, team2: str) -> dict:
    """Get head-to-head record between two teams."""
    h2h = matches_df[
        ((matches_df["team1"] == team1) & (matches_df["team2"] == team2)) |
        ((matches_df["team1"] == team2) & (matches_df["team2"] == team1))
    ]

    if h2h.empty:
        return {"matches": 0, "team1_wins": 0, "team2_wins": 0}

    t1_wins = len(h2h[
        ((h2h["team1"] == team1) & (h2h["score1"] > h2h["score2"])) |
        ((h2h["team2"] == team1) & (h2h["score2"] > h2h["score1"]))
    ])

    return {
        "matches": len(h2h),
        "team1_wins": t1_wins,
        "team2_wins": len(h2h) - t1_wins,
    }
