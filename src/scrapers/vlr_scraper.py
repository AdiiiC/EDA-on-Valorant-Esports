"""
VLR.gg Scraper — pulls live rankings, match results, player stats, and event data.
"""

import time
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag
from config.settings import VLR_BASE_URL, HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT


@dataclass
class TeamRanking:
    rank: int
    team: str
    region: str
    country: str
    rating: float
    earnings: str
    logo_url: str = ""


@dataclass
class PlayerStats:
    player: str
    team: str
    agents: list[str] = field(default_factory=list)
    acs: float = 0.0
    kd: float = 0.0
    adr: float = 0.0
    kast: float = 0.0
    kpr: float = 0.0
    apr: float = 0.0
    fkpr: float = 0.0
    fdpr: float = 0.0
    headshot_pct: float = 0.0
    clutch_pct: float = 0.0
    rating: float = 0.0


@dataclass
class MatchResult:
    event: str
    date: str
    team1: str
    team2: str
    score1: int
    score2: int
    maps: list[str] = field(default_factory=list)
    match_url: str = ""


@dataclass
class EventInfo:
    name: str
    dates: str
    status: str
    prize_pool: str
    region: str
    event_url: str = ""


class VLRScraper:
    """Scraper for VLR.gg — respects rate limits."""

    def __init__(self):
        self.client = httpx.Client(headers=HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        self._last_request = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        self._last_request = time.time()

    def _get(self, path: str) -> BeautifulSoup:
        self._throttle()
        url = f"{VLR_BASE_URL}{path}"
        resp = self.client.get(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    # ─── Team Rankings ───────────────────────────────────────────────────
    def get_team_rankings(self, region: str = "all") -> list[TeamRanking]:
        """Fetch current world team rankings from VLR.gg."""
        path = "/rankings" if region == "all" else f"/rankings/{region}"
        soup = self._get(path)
        rankings: list[TeamRanking] = []

        # VLR uses <div class="world-rankings-col"> per region, with tables inside
        columns = soup.select("div.world-rankings-col")
        for col in columns:
            region_el = col.select_one("h2")
            col_region = region_el.get_text(strip=True) if region_el else region

            rows = col.select("tr.wf-card")
            for row in rows:
                try:
                    rank_td = row.select_one("td.rank-item-rank")
                    team_td = row.select_one("td.rank-item-team")
                    rating_td = row.select_one("td.rank-item-rating")

                    rank_text = rank_td.get_text(strip=True) if rank_td else "0"
                    rank = int(rank_text)

                    team_name = team_td.get("data-sort-value", "") if team_td else ""
                    if not team_name and team_td:
                        team_a = team_td.select_one("a")
                        team_name = team_a.get_text(strip=True) if team_a else ""

                    country_el = row.select_one("div.rank-item-team-country")
                    country = country_el.get_text(strip=True) if country_el else ""

                    logo_el = team_td.select_one("img") if team_td else None
                    logo_url = logo_el.get("src", "") if logo_el else ""

                    rating_text = rating_td.get_text(strip=True).replace(",", "") if rating_td else "0"
                    rating = float(rating_text)

                    if team_name:
                        rankings.append(TeamRanking(
                            rank=rank,
                            team=team_name,
                            region=col_region,
                            country=country,
                            rating=rating,
                            earnings="",
                            logo_url=logo_url,
                        ))
                except (ValueError, AttributeError):
                    continue

        return rankings

    # ─── Player Stats ────────────────────────────────────────────────────
    def get_player_stats(self, timespan: str = "60d", region: str = "all") -> list[PlayerStats]:
        """
        Fetch player stats from VLR.gg stats page.
        timespan: '30d', '60d', '90d', 'all'
        """
        path = f"/stats/?event_group_id=all&event_id=all&region={region}&min_rounds=200&min_rating=1550&agent=all&map_id=all&timespan={timespan}"
        soup = self._get(path)
        players: list[PlayerStats] = []

        table = soup.select_one("table")
        if not table:
            return players

        rows = table.select("tbody tr")
        for row in rows:
            try:
                cols = row.select("td")
                if len(cols) < 10:
                    continue

                # Player name and team
                player_cell = cols[0]
                name_el = player_cell.select_one("div.text-of")
                team_el = player_cell.select_one("div.stats-player-country")

                player_name = name_el.get_text(strip=True) if name_el else ""
                team_name = team_el.get_text(strip=True) if team_el else ""

                # Agents
                agent_cell = cols[1]
                agent_imgs = agent_cell.select("img")
                agents = []
                for img in agent_imgs:
                    src = img.get("src", "")
                    # Extract agent name from src like /img/vlr/game/agents/jett.png
                    if "/agents/" in src:
                        agent_name = src.split("/agents/")[-1].replace(".png", "").capitalize()
                        agents.append(agent_name)

                def safe_float(el, default=0.0):
                    txt = el.get_text(strip=True).replace("%", "").replace(",", "")
                    try:
                        return float(txt)
                    except ValueError:
                        return default

                # cols[2] = rounds, cols[3] = rating, cols[4] = ACS, cols[5] = K/D,
                # cols[6] = KAST%, cols[7] = ADR, cols[8] = KPR, cols[9] = APR,
                # cols[10] = FKPR, cols[11] = FDPR, cols[12] = HS%, cols[13] = CL%
                rating = safe_float(cols[3])
                acs = safe_float(cols[4])
                kd = safe_float(cols[5])
                kast = safe_float(cols[6])
                adr = safe_float(cols[7])
                kpr = safe_float(cols[8])
                apr = safe_float(cols[9])
                fkpr = safe_float(cols[10]) if len(cols) > 10 else 0.0
                fdpr = safe_float(cols[11]) if len(cols) > 11 else 0.0
                hs_pct = safe_float(cols[12]) if len(cols) > 12 else 0.0
                clutch_pct = safe_float(cols[13]) if len(cols) > 13 else 0.0

                if player_name:
                    players.append(PlayerStats(
                        player=player_name,
                        team=team_name,
                        agents=agents,
                        rating=rating,
                        acs=acs,
                        kd=kd,
                        kast=kast,
                        adr=adr,
                        kpr=kpr,
                        apr=apr,
                        fkpr=fkpr,
                        fdpr=fdpr,
                        headshot_pct=hs_pct,
                        clutch_pct=clutch_pct,
                    ))
            except (ValueError, AttributeError, IndexError):
                continue

        return players

    # ─── Recent Match Results ────────────────────────────────────────────
    def get_recent_matches(self, page: int = 1) -> list[MatchResult]:
        """Fetch recent match results."""
        path = f"/matches/results?page={page}"
        soup = self._get(path)
        matches: list[MatchResult] = []

        match_items = soup.select("a.wf-module-item.match-item")
        for item in match_items:
            try:
                teams_els = item.select("div.match-item-vs-team")
                if len(teams_els) < 2:
                    continue

                team1_name_el = teams_els[0].select_one("div.text-of")
                team2_name_el = teams_els[1].select_one("div.text-of")
                team1_score_el = teams_els[0].select_one("div.match-item-vs-team-score")
                team2_score_el = teams_els[1].select_one("div.match-item-vs-team-score")

                team1 = team1_name_el.get_text(strip=True) if team1_name_el else ""
                team2 = team2_name_el.get_text(strip=True) if team2_name_el else ""

                score1_text = team1_score_el.get_text(strip=True) if team1_score_el else "0"
                score2_text = team2_score_el.get_text(strip=True) if team2_score_el else "0"
                score1 = int(score1_text) if score1_text.isdigit() else 0
                score2 = int(score2_text) if score2_text.isdigit() else 0

                # Event name from the match item event section
                event_el = item.select_one("div.match-item-event") or item.select_one("div.match-item-note")
                event_name = event_el.get_text(strip=True) if event_el else ""

                # Time/date
                time_el = item.select_one("div.match-item-time")
                date = time_el.get_text(strip=True) if time_el else ""

                match_url = item.get("href", "")

                if team1 and team2:
                    matches.append(MatchResult(
                        event=event_name,
                        date=date,
                        team1=team1,
                        team2=team2,
                        score1=score1,
                        score2=score2,
                        match_url=f"{VLR_BASE_URL}{match_url}" if match_url else "",
                    ))
            except (ValueError, AttributeError, IndexError):
                continue

        return matches

    # ─── Events ──────────────────────────────────────────────────────────
    def get_events(self, status: str = "ongoing") -> list[EventInfo]:
        """
        Fetch events. status: 'ongoing', 'upcoming', 'completed'
        """
        path = f"/events/{status}" if status != "ongoing" else "/events"
        soup = self._get(path)
        events: list[EventInfo] = []

        event_items = soup.select("a.wf-card.mod-flex")
        for item in event_items:
            try:
                name_el = item.select_one("div.event-item-title")
                dates_el = item.select_one("div.event-item-desc-item.mod-dates")
                prize_el = item.select_one("div.event-item-desc-item.mod-prize")
                region_el = item.select_one("div.event-item-desc-item.mod-location")
                status_el = item.select_one("span.event-item-desc-item-status")

                name = name_el.get_text(strip=True) if name_el else ""
                dates = dates_el.get_text(strip=True) if dates_el else ""
                prize_pool = prize_el.get_text(strip=True) if prize_el else ""
                region = region_el.get_text(strip=True) if region_el else ""
                ev_status = status_el.get_text(strip=True) if status_el else status
                event_url = item.get("href", "")

                if name:
                    events.append(EventInfo(
                        name=name,
                        dates=dates,
                        status=ev_status,
                        prize_pool=prize_pool,
                        region=region,
                        event_url=f"{VLR_BASE_URL}{event_url}" if event_url else "",
                    ))
            except (ValueError, AttributeError):
                continue

        return events

    # ─── Agent Meta ──────────────────────────────────────────────────────
    def get_agent_stats(self, timespan: str = "60d") -> list[dict]:
        """Compute agent pick rates and avg stats from the main player stats page."""
        path = f"/stats/?event_group_id=all&event_id=all&series_id=all&region=all&country=all&min_rounds=200&min_rating=1550&agent=all&map_id=all&timespan={timespan}"
        soup = self._get(path)

        table = soup.select_one("table")
        if not table:
            return []

        rows = table.select("tbody tr")
        total_players = len(rows)
        if total_players == 0:
            return []

        # Aggregate stats by primary agent (first agent image per player)
        agent_data: dict[str, list[float]] = {}  # agent -> list of ACS values
        for row in rows:
            try:
                cols = row.select("td")
                if len(cols) < 5:
                    continue
                # Col 1 has agent images; primary agent is first img
                agent_cell = cols[1]
                imgs = agent_cell.select("img")
                if not imgs:
                    continue
                src = imgs[0].get("src", "")
                if "/agents/" not in src:
                    continue
                agent_name = src.split("/agents/")[-1].replace(".png", "").capitalize()
                # Col 4 = ACS
                acs_text = cols[4].get_text(strip=True)
                acs = float(acs_text) if acs_text else 0.0
                agent_data.setdefault(agent_name, []).append(acs)
            except (ValueError, AttributeError, IndexError):
                continue

        # Compute aggregate stats per agent
        agents: list[dict] = []
        for agent_name, acs_values in agent_data.items():
            count = len(acs_values)
            pick_rate = round(count / total_players * 100, 1)
            avg_acs = round(sum(acs_values) / count, 1) if count else 0.0
            # Win rate approximation: use rating relative to average (not exact but useful)
            agents.append({
                "agent": agent_name,
                "pick_rate": pick_rate,
                "win_rate": round(50 + (avg_acs - 200) / 10, 1),  # heuristic from ACS
                "avg_acs": avg_acs,
            })

        return sorted(agents, key=lambda x: x["pick_rate"], reverse=True)

    # ─── Map Stats ───────────────────────────────────────────────────────
    def get_map_stats(self, timespan: str = "60d") -> list[dict]:
        """Compute map stats by querying the stats page filtered per map."""
        # First get the map options from the main stats page
        path = f"/stats/?timespan={timespan}"
        soup = self._get(path)

        map_select = soup.select_one("select[name=map_id]")
        if not map_select:
            return []

        map_options = []
        for opt in map_select.select("option"):
            val = opt.get("value", "")
            name = opt.get_text(strip=True)
            if val and val != "all":
                map_options.append((val, name))

        maps: list[dict] = []
        for map_id, map_name in map_options:
            try:
                map_path = f"/stats/?event_group_id=all&event_id=all&series_id=all&region=all&country=all&min_rounds=50&min_rating=1550&agent=all&map_id={map_id}&timespan={timespan}"
                map_soup = self._get(map_path)
                table = map_soup.select_one("table")
                if not table:
                    continue
                rows = table.select("tbody tr")
                if not rows:
                    continue

                # Sum total rounds and compute avg stats across players on this map
                total_rounds = 0
                total_kills = 0
                total_deaths = 0
                player_count = len(rows)
                for row in rows:
                    cols = row.select("td")
                    if len(cols) < 18:
                        continue
                    try:
                        rounds = int(cols[2].get_text(strip=True).replace(",", ""))
                        kills = int(cols[16].get_text(strip=True).replace(",", ""))
                        deaths = int(cols[17].get_text(strip=True).replace(",", ""))
                        total_rounds += rounds
                        total_kills += kills
                        total_deaths += deaths
                    except (ValueError, IndexError):
                        continue

                # Approximate attack/defense win rates from kill ratios
                if total_kills + total_deaths > 0:
                    kill_ratio = total_kills / (total_kills + total_deaths) * 100
                    atk_wr = round(kill_ratio + 2, 1)  # slight attacker advantage heuristic
                    def_wr = round(100 - atk_wr, 1)
                else:
                    atk_wr = 50.0
                    def_wr = 50.0

                maps.append({
                    "map": map_name,
                    "times_played": total_rounds,
                    "atk_win_rate": atk_wr,
                    "def_win_rate": def_wr,
                })
            except (ValueError, AttributeError):
                continue

        return maps

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
