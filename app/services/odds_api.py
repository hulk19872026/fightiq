import os
import httpx
from app.services.cache import cache_get, cache_set

API_KEY = os.getenv("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
CACHE_KEY = "odds_data"
TIMEOUT = 10

FALLBACK_ODDS = [
    {
        "fight": "Prochazka vs Ulberg",
        "fighter_a": "Jiri Prochazka",
        "fighter_b": "Carlos Ulberg",
        "fighter_a_odds": -121,
        "fighter_b_odds": 102,
        "fighter_a_prob": 55,
        "fighter_b_prob": 50,
    },
    {
        "fight": "Murzakanov vs Costa",
        "fighter_a": "Azamat Murzakanov",
        "fighter_b": "Paulo Costa",
        "fighter_a_odds": -175,
        "fighter_b_odds": 150,
        "fighter_a_prob": 64,
        "fighter_b_prob": 40,
    },
    {
        "fight": "Blaydes vs Hokit",
        "fighter_a": "Curtis Blaydes",
        "fighter_b": "Josh Hokit",
        "fighter_a_odds": -200,
        "fighter_b_odds": 170,
        "fighter_a_prob": 67,
        "fighter_b_prob": 37,
    },
    {
        "fight": "Reyes vs Walker",
        "fighter_a": "Dominick Reyes",
        "fighter_b": "Johnny Walker",
        "fighter_a_odds": 110,
        "fighter_b_odds": -130,
        "fighter_a_prob": 48,
        "fighter_b_prob": 57,
    },
    {
        "fight": "Pitbull vs Pico",
        "fighter_a": "Patricio Pitbull",
        "fighter_b": "Aaron Pico",
        "fighter_a_odds": 140,
        "fighter_b_odds": -160,
        "fighter_a_prob": 42,
        "fighter_b_prob": 62,
    },
]


def american_to_implied(odds: int) -> int:
    if odds < 0:
        return round(abs(odds) / (abs(odds) + 100) * 100)
    return round(100 / (odds + 100) * 100)


async def fetch_odds() -> list[dict]:
    cached = cache_get(CACHE_KEY, ttl=120)
    if cached:
        return cached

    if not API_KEY:
        cache_set(CACHE_KEY, FALLBACK_ODDS)
        return FALLBACK_ODDS

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "apiKey": API_KEY,
                    "regions": "us",
                    "markets": "h2h",
                    "oddsFormat": "american",
                },
            )
            resp.raise_for_status()

        raw = resp.json()
        odds_list = _parse_odds(raw)
        if odds_list:
            cache_set(CACHE_KEY, odds_list)
            return odds_list
    except Exception:
        pass

    cache_set(CACHE_KEY, FALLBACK_ODDS)
    return FALLBACK_ODDS


def _parse_odds(raw: list) -> list[dict]:
    results = []
    for event in raw:
        teams = event.get("outcomes") or []
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        markets = bookmakers[0].get("markets", [])
        if not markets:
            continue

        outcomes = markets[0].get("outcomes", [])
        if len(outcomes) < 2:
            continue

        a_name = outcomes[0]["name"]
        b_name = outcomes[1]["name"]
        a_odds = outcomes[0]["price"]
        b_odds = outcomes[1]["price"]

        results.append({
            "fight": f"{a_name} vs {b_name}",
            "fighter_a": a_name,
            "fighter_b": b_name,
            "fighter_a_odds": a_odds,
            "fighter_b_odds": b_odds,
            "fighter_a_prob": american_to_implied(a_odds),
            "fighter_b_prob": american_to_implied(b_odds),
        })

    return results
