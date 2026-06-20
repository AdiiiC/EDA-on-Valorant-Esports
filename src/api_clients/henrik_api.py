"""
HenrikDev Valorant API Client — MMR, match history, leaderboards, account data.
API Docs: https://docs.henrikdev.xyz/
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from config.settings import HENRIK_API_KEY, HENRIK_BASE_URL, REQUEST_DELAY


@dataclass
class AccountInfo:
    puuid: str
    name: str
    tag: str
    region: str
    account_level: int
    card_url: str = ""


@dataclass
class MMRData:
    name: str
    tag: str
    current_tier: str
    current_rr: int
    peak_tier: str
    peak_season: str
    elo: int = 0
    wins: int = 0
    losses: int = 0


@dataclass
class MatchInfo:
    match_id: str
    map: str
    mode: str
    started_at: str
    duration: int  # seconds
    team_blue_score: int
    team_red_score: int
    players: list[dict] = field(default_factory=list)


@dataclass
class LeaderboardEntry:
    rank: int
    name: str
    tag: str
    tier: str
    rr: int
    wins: int
    games_played: int


class HenrikAPIClient:
    """Client for HenrikDev's unofficial Valorant API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or HENRIK_API_KEY
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = self.api_key
        self.client = httpx.Client(
            base_url=HENRIK_BASE_URL, headers=headers, timeout=15, follow_redirects=True
        )
        self._last_request = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request = time.time()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        self._throttle()
        resp = self.client.get(path, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") and data["status"] != 200:
            raise ValueError(f"API error: {data.get('message', 'Unknown error')}")
        return data.get("data", data)

    # ─── Account ─────────────────────────────────────────────────────────
    def get_account(self, name: str, tag: str) -> AccountInfo:
        """Get account info by name#tag."""
        data = self._get(f"/valorant/v2/account/{name}/{tag}")
        return AccountInfo(
            puuid=data.get("puuid", ""),
            name=data.get("name", name),
            tag=data.get("tag", tag),
            region=data.get("region", ""),
            account_level=data.get("account_level", 0),
            card_url=data.get("card", {}).get("wide", ""),
        )

    # ─── MMR ─────────────────────────────────────────────────────────────
    def get_mmr(self, name: str, tag: str, region: str = "na") -> MMRData:
        """Get current MMR/rank data."""
        data = self._get(f"/valorant/v3/mmr/{region}/pc/{name}/{tag}")
        current = data.get("current", {})
        peak = data.get("peak", {})
        seasonal = data.get("seasonal", {})

        # Get latest season wins/losses
        wins = 0
        losses = 0
        if seasonal:
            latest_season = list(seasonal.values())[-1] if seasonal else {}
            wins = latest_season.get("wins", 0)
            losses = latest_season.get("number_of_games", 0) - wins

        return MMRData(
            name=data.get("name", name),
            tag=data.get("tag", tag),
            current_tier=current.get("tier", {}).get("name", "Unranked"),
            current_rr=current.get("rr", 0),
            peak_tier=peak.get("tier", {}).get("name", "Unranked"),
            peak_season=peak.get("season", {}).get("short", ""),
            elo=current.get("elo", 0),
            wins=wins,
            losses=losses,
        )

    # ─── Match History ───────────────────────────────────────────────────
    def get_match_history(self, name: str, tag: str, region: str = "na", mode: str = "competitive", size: int = 10) -> list[MatchInfo]:
        """Get recent match history for a player."""
        data = self._get(f"/valorant/v4/matches/{region}/pc/{name}/{tag}", params={"mode": mode, "size": str(size)})
        matches: list[MatchInfo] = []

        match_list = data if isinstance(data, list) else data.get("data", [])
        for match in match_list:
            try:
                metadata = match.get("metadata", {})
                teams = match.get("teams", {})
                players_data = match.get("players", [])

                blue = teams.get("blue", {})
                red = teams.get("red", {})

                player_summaries = []
                for p in players_data:
                    stats = p.get("stats", {})
                    player_summaries.append({
                        "name": p.get("name", ""),
                        "tag": p.get("tag", ""),
                        "team": p.get("team", ""),
                        "agent": p.get("agent", {}).get("name", ""),
                        "kills": stats.get("kills", 0),
                        "deaths": stats.get("deaths", 0),
                        "assists": stats.get("assists", 0),
                        "score": stats.get("score", 0),
                    })

                matches.append(MatchInfo(
                    match_id=metadata.get("match_id", ""),
                    map=metadata.get("map", {}).get("name", ""),
                    mode=metadata.get("mode", mode),
                    started_at=metadata.get("started_at", ""),
                    duration=metadata.get("game_length_in_ms", 0) // 1000,
                    team_blue_score=blue.get("rounds", {}).get("won", 0),
                    team_red_score=red.get("rounds", {}).get("won", 0),
                    players=player_summaries,
                ))
            except (ValueError, KeyError, TypeError):
                continue

        return matches

    # ─── Leaderboard ─────────────────────────────────────────────────────
    def get_leaderboard(self, region: str = "na", season: Optional[str] = None) -> list[LeaderboardEntry]:
        """Get ranked leaderboard."""
        params = {}
        if season:
            params["season"] = season
        data = self._get(f"/valorant/v2/leaderboard/{region}", params=params)

        entries: list[LeaderboardEntry] = []
        player_list = data if isinstance(data, list) else data.get("players", [])

        for player in player_list[:100]:  # top 100
            try:
                entries.append(LeaderboardEntry(
                    rank=player.get("leaderboardRank", 0),
                    name=player.get("gameName", ""),
                    tag=player.get("tagLine", ""),
                    tier=player.get("competitiveTier", "Radiant"),
                    rr=player.get("rankedRating", 0),
                    wins=player.get("numberOfWins", 0),
                    games_played=player.get("numberOfGames", 0) if "numberOfGames" in player else player.get("numberOfWins", 0),
                ))
            except (ValueError, KeyError, TypeError):
                continue

        return entries

    # ─── Premier Teams ───────────────────────────────────────────────────
    def get_premier_leaderboard(self, region: str = "na") -> list[dict]:
        """Get premier team leaderboard."""
        try:
            data = self._get(f"/valorant/v1/premier/leaderboard/{region}")
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
