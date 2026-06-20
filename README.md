# Valorant Esports Analytics Dashboard

A professional-grade, ML-powered analytics platform for Valorant competitive esports. Built with Streamlit, featuring live data from VLR.gg, HenrikDev API, and Liquipedia.

## Features

### 🌐 Live Data Pipeline
- **VLR.gg scraper** — team rankings, player stats, match results, agent/map meta
- **HenrikDev API** — player MMR, match history, leaderboards
- **Liquipedia scraper** — roster changes, transfers, tournament brackets
- **DuckDB cache** — persistent storage with TTL-based auto-refresh

### 📊 8 Dashboard Pages
1. **Team Rankings** — Global rankings with interactive charts
2. **Player Stats** — Filterable stats table, distributions, breakout detection
3. **Player Comparison** — Radar charts, percentile analysis, side-by-side
4. **Match Results** — Recent matches, win rates, scoreline analysis
5. **Agent & Map Meta** — Pick/win rates, tier lists, map balance
6. **ML Insights** — K-Means clustering, win predictor, Elo ratings, forecasting
7. **Network Analysis** — Transfer Sankey diagrams, co-play graphs, super team builder
8. **Live Tracker** — Player lookup (MMR/rank), regional leaderboards

### 🤖 ML Models
- **Player Clustering** (K-Means + DBSCAN) — playstyle archetypes
- **Win Probability** (Gradient Boosting) — match outcome prediction
- **Elo Rating System** — computed from match history
- **Time-Series Forecasting** — team trajectory predictions
- **Breakout Detection** — anomalous performer identification

### 🕸️ Network Analysis
- Transfer flow networks (Sankey diagrams)
- Co-play networks (teammate connections)
- Team centrality rankings (market activity)
- Super team builder (role-based optimization)

## Quick Start

```bash
# 1. Clone and enter
cd EDA-on-Valorant-Esports

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API key (optional, for Live Tracker page)
cp .env.example .env
# Edit .env and add your HenrikDev API key

# 5. Run the dashboard
streamlit run app.py
```

## Docker

```bash
docker compose up --build
# Open http://localhost:8501
```

## Configuration

- **API Key**: Get a free key from [HenrikDev](https://docs.henrikdev.xyz/) for the Live Tracker
- **Region**: Set in sidebar — affects team rankings and player stats
- **Timespan**: 30d/60d/90d — controls how far back stats are pulled
- **Force Refresh**: Button in sidebar to bypass cache

## Project Structure

```
├── app.py                  # Main Streamlit entry point
├── config/settings.py      # Configuration & environment
├── src/
│   ├── scrapers/
│   │   ├── vlr_scraper.py  # VLR.gg data extraction
│   │   └── liquipedia.py   # Liquipedia transfers/rosters
│   ├── api_clients/
│   │   └── henrik_api.py   # HenrikDev Valorant API
│   ├── models/
│   │   ├── clustering.py   # K-Means player clustering
│   │   ├── win_predictor.py # Match outcome prediction
│   │   └── forecasting.py  # Rating/performance forecasting
│   └── analysis/
│       ├── network.py      # Graph/network analysis
│       └── stats.py        # Statistical computations
├── data/db.py              # DuckDB persistence layer
├── pages/                  # Streamlit multi-page modules
├── ui/                     # Reusable chart builders & components
├── tests/                  # Pytest test suite
├── Dockerfile              # Container support
└── docker-compose.yml
```

## Data Sources

| Source | What | Rate Limit |
|--------|------|-----------|
| VLR.gg | Rankings, stats, matches, events | 1.5s between requests |
| HenrikDev API | MMR, match history, leaderboards | Free tier available |
| Liquipedia | Transfers, rosters, tournaments | 2s+ between requests (TOS) |

## Running Tests

```bash
pytest
```

## Tech Stack

- **Frontend**: Streamlit + Plotly
- **Backend**: Python 3.11+
- **Storage**: DuckDB (embedded OLAP)
- **ML**: scikit-learn, scipy
- **Network**: NetworkX
- **Scraping**: httpx + BeautifulSoup4
- **Deployment**: Docker

## License

MIT