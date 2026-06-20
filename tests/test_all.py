"""Tests for VLR scraper."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock


class TestVLRScraper:
    """Unit tests for VLR scraper (mocked HTTP)."""

    def test_team_ranking_dataclass(self):
        from src.scrapers.vlr_scraper import TeamRanking
        ranking = TeamRanking(rank=1, team="Sentinels", region="na", country="US", rating=1800.0, earnings="$500,000")
        assert ranking.rank == 1
        assert ranking.team == "Sentinels"

    def test_player_stats_dataclass(self):
        from src.scrapers.vlr_scraper import PlayerStats
        player = PlayerStats(player="TenZ", team="Sentinels", acs=270.0, kd=1.35, rating=1.25)
        assert player.player == "TenZ"
        assert player.acs == 270.0

    def test_match_result_dataclass(self):
        from src.scrapers.vlr_scraper import MatchResult
        match = MatchResult(event="VCT", date="2026-06-15", team1="SEN", team2="NRG", score1=2, score2=1)
        assert match.score1 > match.score2

    @patch("src.scrapers.vlr_scraper.httpx.Client")
    def test_scraper_throttle(self, mock_client):
        from src.scrapers.vlr_scraper import VLRScraper
        scraper = VLRScraper()
        # Verify client is initialized
        assert scraper.client is not None
        scraper.close()


class TestHenrikAPI:
    """Unit tests for HenrikDev API client."""

    def test_account_info_dataclass(self):
        from src.api_clients.henrik_api import AccountInfo
        account = AccountInfo(puuid="abc", name="TenZ", tag="0505", region="na", account_level=200)
        assert account.name == "TenZ"

    def test_mmr_dataclass(self):
        from src.api_clients.henrik_api import MMRData
        mmr = MMRData(name="TenZ", tag="0505", current_tier="Radiant", current_rr=450, peak_tier="Radiant", peak_season="e8a3")
        assert mmr.current_tier == "Radiant"

    def test_leaderboard_entry(self):
        from src.api_clients.henrik_api import LeaderboardEntry
        entry = LeaderboardEntry(rank=1, name="Player1", tag="NA1", tier="Radiant", rr=800, wins=50, games_played=60)
        assert entry.rank == 1


class TestDatabase:
    """Tests for DuckDB storage layer."""

    def test_database_init(self, tmp_path):
        from data.db import Database
        db = Database(db_path=tmp_path / "test.duckdb")
        # Tables should be created
        result = db.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
        table_names = [r[0] for r in result]
        assert "team_rankings" in table_names
        assert "player_stats" in table_names
        assert "match_results" in table_names
        db.close()

    def test_team_rankings_roundtrip(self, tmp_path):
        from data.db import Database
        from src.scrapers.vlr_scraper import TeamRanking

        db = Database(db_path=tmp_path / "test.duckdb")
        rankings = [
            TeamRanking(rank=1, team="Team1", region="all", country="US", rating=1800, earnings="$100k"),
            TeamRanking(rank=2, team="Team2", region="all", country="EU", rating=1700, earnings="$80k"),
        ]
        db.save_team_rankings(rankings, "all")
        df = db.get_team_rankings("all")
        assert len(df) == 2
        assert df.iloc[0]["team"] == "Team1"
        db.close()


class TestModels:
    """Tests for ML models."""

    def test_clustering(self):
        import pandas as pd
        from src.models.clustering import cluster_players_kmeans

        df = pd.DataFrame({
            "player": [f"P{i}" for i in range(20)],
            "team": ["Team1"] * 10 + ["Team2"] * 10,
            "acs": [250 + i * 5 for i in range(20)],
            "kd": [1.0 + i * 0.05 for i in range(20)],
            "adr": [140 + i * 3 for i in range(20)],
            "kast": [70 + i for i in range(20)],
            "kpr": [0.7 + i * 0.02 for i in range(20)],
            "apr": [0.3 + i * 0.01 for i in range(20)],
            "fkpr": [0.1 + i * 0.01 for i in range(20)],
            "fdpr": [0.1 + i * 0.005 for i in range(20)],
            "headshot_pct": [20 + i for i in range(20)],
            "clutch_pct": [10 + i * 0.5 for i in range(20)],
            "rating": [1.0 + i * 0.03 for i in range(20)],
        })

        result = cluster_players_kmeans(df, n_clusters=3)
        assert "cluster" in result.columns
        assert result["cluster"].nunique() == 3

    def test_win_predictor_heuristic(self):
        import pandas as pd
        from src.models.win_predictor import WinPredictor

        predictor = WinPredictor()
        player_stats = pd.DataFrame({
            "player": ["P1", "P2", "P3", "P4"],
            "team": ["TeamA", "TeamA", "TeamB", "TeamB"],
            "acs": [280, 260, 220, 210],
            "kd": [1.4, 1.3, 1.0, 0.9],
            "adr": [160, 150, 130, 120],
            "kast": [75, 73, 68, 65],
            "kpr": [0.9, 0.85, 0.7, 0.65],
            "apr": [0.4, 0.35, 0.3, 0.25],
            "fkpr": [0.15, 0.12, 0.08, 0.06],
            "fdpr": [0.1, 0.11, 0.12, 0.13],
            "headshot_pct": [28, 25, 22, 20],
            "clutch_pct": [15, 12, 10, 8],
            "rating": [1.3, 1.2, 1.0, 0.9],
        })

        result = predictor.predict("TeamA", "TeamB", player_stats)
        # TeamA should be favored
        assert result.team1_win_prob > 0.5

    def test_forecasting(self):
        from src.models.forecasting import forecast_rating
        history = [1500, 1520, 1540, 1530, 1560, 1580, 1600]
        result = forecast_rating(history, periods=3)
        assert result.trend == "rising"
        assert len(result.forecasted_ratings) == 3


class TestNetworkAnalysis:
    """Tests for network analysis."""

    def test_transfer_flow_data(self):
        import pandas as pd
        from src.analysis.network import get_transfer_flow_data

        transfers = pd.DataFrame({
            "date": ["2026-01-01"] * 4,
            "player": ["P1", "P2", "P3", "P4"],
            "old_team": ["A", "A", "B", "C"],
            "new_team": ["B", "C", "A", "A"],
            "role": ["player"] * 4,
        })

        flows = get_transfer_flow_data(transfers)
        assert not flows.empty
        assert "source" in flows.columns

    def test_coplay_network(self):
        import pandas as pd
        from src.analysis.network import build_coplay_network

        df = pd.DataFrame({
            "player": ["P1", "P2", "P3"],
            "team": ["Team1", "Team1", "Team2"],
        })

        G = build_coplay_network(df)
        assert len(G.nodes) == 3
        assert G.has_edge("P1", "P2")
        assert not G.has_edge("P1", "P3")
