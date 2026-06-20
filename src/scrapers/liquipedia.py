"""
Liquipedia Scraper — roster changes, tournament brackets, transfer history.
"""

import time
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup
from config.settings import LIQUIPEDIA_BASE_URL, REQUEST_DELAY, REQUEST_TIMEOUT


LIQUIPEDIA_HEADERS = {
    "User-Agent": "ValorantEDABot/1.0 (educational project; contact: github.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


@dataclass
class Transfer:
    date: str
    player: str
    old_team: str
    new_team: str
    role: str = ""


@dataclass
class RosterEntry:
    team: str
    player: str
    role: str
    country: str
    join_date: str = ""


@dataclass
class TournamentResult:
    placement: str
    team: str
    prize: str
    event: str


class LiquipediaScraper:
    """Scraper for Liquipedia Valorant — aggressive rate-limiting (required by their TOS)."""

    def __init__(self):
        self.client = httpx.Client(
            headers=LIQUIPEDIA_HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=True
        )
        self._last_request = 0.0
        # Liquipedia requires 2s+ between requests
        self._delay = max(REQUEST_DELAY, 2.0)

    def _throttle(self):
        elapsed = time.time() - self._last_request
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_request = time.time()

    def _get(self, path: str) -> BeautifulSoup:
        self._throttle()
        url = f"{LIQUIPEDIA_BASE_URL}{path}"
        resp = self.client.get(url)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    # ─── Recent Transfers ────────────────────────────────────────────────
    def get_recent_transfers(self, limit: int = 50) -> list[Transfer]:
        """Fetch recent player transfers/roster moves."""
        soup = self._get("/Portal:Transfers")
        transfers: list[Transfer] = []

        rows = soup.select("div.divRow")
        for row in rows[:limit]:
            try:
                date_el = row.select_one("div.divCell.Date")
                player_el = row.select_one("div.divCell.Name a")
                old_el = row.select_one("div.divCell.OldTeam a")
                new_el = row.select_one("div.divCell.NewTeam a")
                role_el = row.select_one("div.divCell.Position")

                date = date_el.get_text(strip=True) if date_el else ""
                player = player_el.get_text(strip=True) if player_el else ""
                old_team = old_el.get_text(strip=True) if old_el else "Free Agent"
                new_team = new_el.get_text(strip=True) if new_el else "Free Agent"
                role = role_el.get_text(strip=True) if role_el else ""

                if player:
                    transfers.append(Transfer(
                        date=date, player=player, old_team=old_team,
                        new_team=new_team, role=role,
                    ))
            except (ValueError, AttributeError):
                continue

        return transfers

    # ─── Team Roster ─────────────────────────────────────────────────────
    def get_team_roster(self, team_slug: str) -> list[RosterEntry]:
        """Fetch current roster for a team. team_slug e.g. 'Sentinels'."""
        soup = self._get(f"/{team_slug}")
        roster: list[RosterEntry] = []

        # Liquipedia team pages have roster tables
        roster_table = soup.select_one("div.roster-card") or soup.select_one("table.roster-card")
        if not roster_table:
            # Fallback: look for the active roster section
            tables = soup.select("table.wikitable")
            if tables:
                roster_table = tables[0]

        if not roster_table:
            return roster

        rows = roster_table.select("tr")
        for row in rows:
            try:
                cols = row.select("td")
                if len(cols) < 2:
                    continue
                player_el = row.select_one("a")
                country_el = row.select_one("span.flag img") or row.select_one("img.flag")

                player = player_el.get_text(strip=True) if player_el else ""
                country = country_el.get("alt", "") if country_el else ""
                role = cols[-1].get_text(strip=True) if cols else ""

                if player:
                    roster.append(RosterEntry(
                        team=team_slug, player=player, role=role,
                        country=country,
                    ))
            except (ValueError, AttributeError):
                continue

        return roster

    # ─── Tournament Results ──────────────────────────────────────────────
    def get_tournament_results(self, event_slug: str) -> list[TournamentResult]:
        """Fetch results from a specific tournament page."""
        soup = self._get(f"/{event_slug}")
        results: list[TournamentResult] = []

        prize_table = soup.select_one("div.prizepooltable") or soup.select_one("table.prizepooltable")
        if not prize_table:
            tables = soup.select("table.wikitable")
            prize_table = tables[0] if tables else None

        if not prize_table:
            return results

        rows = prize_table.select("tr")
        for row in rows[1:]:  # skip header
            try:
                cols = row.select("td")
                if len(cols) < 3:
                    continue
                placement = cols[0].get_text(strip=True)
                team_el = row.select_one("a") or cols[1]
                team = team_el.get_text(strip=True) if team_el else ""
                prize = cols[2].get_text(strip=True) if len(cols) > 2 else "$0"

                if team:
                    results.append(TournamentResult(
                        placement=placement, team=team,
                        prize=prize, event=event_slug,
                    ))
            except (ValueError, AttributeError):
                continue

        return results

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
