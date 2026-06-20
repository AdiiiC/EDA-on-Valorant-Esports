"""Application configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "valorant_esports.duckdb"

# HenrikDev API
HENRIK_API_KEY = os.getenv("HENRIK_API_KEY", "")
HENRIK_BASE_URL = "https://api.henrikdev.xyz"

# Scraper settings
VLR_BASE_URL = "https://www.vlr.gg"
LIQUIPEDIA_BASE_URL = "https://liquipedia.net/valorant"
REQUEST_DELAY = 1.5  # seconds between requests (be respectful)
REQUEST_TIMEOUT = 15

# Cache TTL (seconds)
CACHE_TTL_RANKINGS = 3600  # 1 hour
CACHE_TTL_MATCHES = 300  # 5 minutes
CACHE_TTL_STATS = 1800  # 30 minutes

# User agent for scraping
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
