"""
DuckDB storage layer — persistent cache for scraped data with TTL support.
"""

import time
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
from config.settings import DB_PATH, CACHE_TTL_RANKINGS, CACHE_TTL_MATCHES, CACHE_TTL_STATS


class Database:
    """DuckDB-backed storage with TTL caching."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # Retry connection to handle transient lock conflicts (e.g. Streamlit multi-page)
        for attempt in range(5):
            try:
                self.conn = duckdb.connect(self.db_path)
                break
            except duckdb.IOException:
                if attempt == 4:
                    raise
                time.sleep(0.5 * (attempt + 1))
        self._init_tables()

    def _init_tables(self):
        """Create tables if they don't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS team_rankings (
                rank INTEGER,
                team VARCHAR,
                region VARCHAR,
                country VARCHAR,
                rating DOUBLE,
                earnings VARCHAR,
                logo_url VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS player_stats (
                player VARCHAR,
                team VARCHAR,
                agents VARCHAR,
                acs DOUBLE,
                kd DOUBLE,
                adr DOUBLE,
                kast DOUBLE,
                kpr DOUBLE,
                apr DOUBLE,
                fkpr DOUBLE,
                fdpr DOUBLE,
                headshot_pct DOUBLE,
                clutch_pct DOUBLE,
                rating DOUBLE,
                timespan VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS match_results (
                event VARCHAR,
                date VARCHAR,
                team1 VARCHAR,
                team2 VARCHAR,
                score1 INTEGER,
                score2 INTEGER,
                maps VARCHAR,
                match_url VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                name VARCHAR,
                dates VARCHAR,
                status VARCHAR,
                prize_pool VARCHAR,
                region VARCHAR,
                event_url VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                date VARCHAR,
                player VARCHAR,
                old_team VARCHAR,
                new_team VARCHAR,
                role VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_stats (
                agent VARCHAR,
                pick_rate DOUBLE,
                win_rate DOUBLE,
                avg_acs DOUBLE,
                timespan VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS map_stats (
                map VARCHAR,
                times_played INTEGER,
                atk_win_rate DOUBLE,
                def_win_rate DOUBLE,
                timespan VARCHAR,
                fetched_at DOUBLE
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                rank INTEGER,
                name VARCHAR,
                tag VARCHAR,
                tier VARCHAR,
                rr INTEGER,
                wins INTEGER,
                games_played INTEGER,
                region VARCHAR,
                fetched_at DOUBLE
            )
        """)

    # ─── Generic helpers ─────────────────────────────────────────────────
    def _is_stale(self, table: str, ttl: float, **filters) -> bool:
        """Check if cached data is stale."""
        where = " AND ".join(f"{k} = '{v}'" for k, v in filters.items()) if filters else "1=1"
        result = self.conn.execute(
            f"SELECT MAX(fetched_at) FROM {table} WHERE {where}"
        ).fetchone()
        if result[0] is None:
            return True
        return (time.time() - result[0]) > ttl

    def _clear_table(self, table: str, **filters):
        where = " AND ".join(f"{k} = '{v}'" for k, v in filters.items()) if filters else "1=1"
        self.conn.execute(f"DELETE FROM {table} WHERE {where}")

    # ─── Team Rankings ───────────────────────────────────────────────────
    def save_team_rankings(self, rankings: list, region: str = "all"):
        if region == "all":
            self._clear_table("team_rankings")
        else:
            self._clear_table("team_rankings", region=region)
        now = time.time()
        for r in rankings:
            self.conn.execute(
                "INSERT INTO team_rankings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [r.rank, r.team, r.region, r.country, r.rating, r.earnings, r.logo_url, now],
            )

    def get_team_rankings(self, region: str = "all") -> pd.DataFrame:
        if region == "all":
            return self.conn.execute(
                "SELECT rank, team, region, country, rating, earnings, logo_url FROM team_rankings ORDER BY rating DESC"
            ).fetchdf()
        return self.conn.execute(
            "SELECT rank, team, region, country, rating, earnings, logo_url FROM team_rankings WHERE region = ? ORDER BY rank",
            [region],
        ).fetchdf()

    def team_rankings_stale(self, region: str = "all") -> bool:
        if region == "all":
            return self._is_stale("team_rankings", CACHE_TTL_RANKINGS)
        return self._is_stale("team_rankings", CACHE_TTL_RANKINGS, region=region)

    # ─── Player Stats ────────────────────────────────────────────────────
    def save_player_stats(self, players: list, timespan: str = "60d"):
        self._clear_table("player_stats", timespan=timespan)
        now = time.time()
        for p in players:
            self.conn.execute(
                "INSERT INTO player_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [p.player, p.team, ",".join(p.agents), p.acs, p.kd, p.adr, p.kast,
                 p.kpr, p.apr, p.fkpr, p.fdpr, p.headshot_pct, p.clutch_pct, p.rating, timespan, now],
            )

    def get_player_stats(self, timespan: str = "60d") -> pd.DataFrame:
        return self.conn.execute(
            "SELECT player, team, agents, acs, kd, adr, kast, kpr, apr, fkpr, fdpr, headshot_pct, clutch_pct, rating FROM player_stats WHERE timespan = ? ORDER BY rating DESC",
            [timespan],
        ).fetchdf()

    def player_stats_stale(self, timespan: str = "60d") -> bool:
        return self._is_stale("player_stats", CACHE_TTL_STATS, timespan=timespan)

    # ─── Matches ─────────────────────────────────────────────────────────
    def save_matches(self, matches: list):
        self._clear_table("match_results")
        now = time.time()
        for m in matches:
            self.conn.execute(
                "INSERT INTO match_results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [m.event, m.date, m.team1, m.team2, m.score1, m.score2,
                 ",".join(m.maps), m.match_url, now],
            )

    def get_matches(self) -> pd.DataFrame:
        return self.conn.execute(
            "SELECT event, date, team1, team2, score1, score2, maps, match_url FROM match_results ORDER BY ROWID DESC"
        ).fetchdf()

    def matches_stale(self) -> bool:
        return self._is_stale("match_results", CACHE_TTL_MATCHES)

    # ─── Events ──────────────────────────────────────────────────────────
    def save_events(self, events: list):
        self._clear_table("events")
        now = time.time()
        for e in events:
            self.conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                [e.name, e.dates, e.status, e.prize_pool, e.region, e.event_url, now],
            )

    def get_events(self) -> pd.DataFrame:
        return self.conn.execute("SELECT * FROM events").fetchdf()

    # ─── Transfers ───────────────────────────────────────────────────────
    def save_transfers(self, transfers: list):
        self._clear_table("transfers")
        now = time.time()
        for t in transfers:
            self.conn.execute(
                "INSERT INTO transfers VALUES (?, ?, ?, ?, ?, ?)",
                [t.date, t.player, t.old_team, t.new_team, t.role, now],
            )

    def get_transfers(self) -> pd.DataFrame:
        return self.conn.execute(
            "SELECT date, player, old_team, new_team, role FROM transfers ORDER BY ROWID DESC"
        ).fetchdf()

    # ─── Agent Stats ─────────────────────────────────────────────────────
    def save_agent_stats(self, agents: list[dict], timespan: str = "60d"):
        self._clear_table("agent_stats", timespan=timespan)
        now = time.time()
        for a in agents:
            self.conn.execute(
                "INSERT INTO agent_stats VALUES (?, ?, ?, ?, ?, ?)",
                [a["agent"], a["pick_rate"], a["win_rate"], a["avg_acs"], timespan, now],
            )

    def get_agent_stats(self, timespan: str = "60d") -> pd.DataFrame:
        return self.conn.execute(
            "SELECT agent, pick_rate, win_rate, avg_acs FROM agent_stats WHERE timespan = ? ORDER BY pick_rate DESC",
            [timespan],
        ).fetchdf()

    # ─── Map Stats ───────────────────────────────────────────────────────
    def save_map_stats(self, maps: list[dict], timespan: str = "60d"):
        self._clear_table("map_stats", timespan=timespan)
        now = time.time()
        for m in maps:
            self.conn.execute(
                "INSERT INTO map_stats VALUES (?, ?, ?, ?, ?, ?)",
                [m["map"], m["times_played"], m["atk_win_rate"], m["def_win_rate"], timespan, now],
            )

    def get_map_stats(self, timespan: str = "60d") -> pd.DataFrame:
        return self.conn.execute(
            "SELECT map, times_played, atk_win_rate, def_win_rate FROM map_stats WHERE timespan = ?",
            [timespan],
        ).fetchdf()

    # ─── Leaderboard ─────────────────────────────────────────────────────
    def save_leaderboard(self, entries: list, region: str = "na"):
        self._clear_table("leaderboard", region=region)
        now = time.time()
        for e in entries:
            self.conn.execute(
                "INSERT INTO leaderboard VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [e.rank, e.name, e.tag, e.tier, e.rr, e.wins, e.games_played, region, now],
            )

    def get_leaderboard(self, region: str = "na") -> pd.DataFrame:
        return self.conn.execute(
            "SELECT rank, name, tag, tier, rr, wins, games_played FROM leaderboard WHERE region = ? ORDER BY rank",
            [region],
        ).fetchdf()

    # ─── Raw query for custom analysis ───────────────────────────────────
    def query(self, sql: str) -> pd.DataFrame:
        return self.conn.execute(sql).fetchdf()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
