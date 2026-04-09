from app.services.odds_api import fetch_events  # noqa: F401 — re-export

# Events are now fetched from odds_api.py which handles:
# 1. The Odds API (live data, if ODDS_API_KEY is set)
# 2. Web search fallback
# 3. Hardcoded fallback as last resort
