import os
import httpx
from app.services.cache import cache_get, cache_set

API_KEY = os.getenv("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
CACHE_KEY = "odds_data"
TIMEOUT = 10

FALLBACK_ODDS = [
    {
        "fight": "Oliveira vs Makhachev",
        "fighter_a": "Charles Oliveira",
        "fighter_b": "Islam Makhachev",
        "fighter_a_odds": 175,
        "fighter_b_odds": -210,
        "fighter_a_prob": 36,
        "fighter_b_prob": 68,
    },
    {
        "fight": "Gaethje vs Holloway",
        "fighter_a": "Justin Gaethje",
        "fighter_b": "Max Holloway",
        "fighter_a_odds": -130,
        "fighter_b_odds": 110,
        "fighter_a_prob": 57,
        "fighter_b_prob": 48,
    },
    {
        "fight": "Yan vs Figueiredo",
        "fighter_a": "Petr Yan",
        "fighter_b": "Deiveson Figueiredo",
        "fighter_a_odds": -160,
        "fighter_b_odds": 140,
        "fighter_a_prob": 62,
        "fighter_b_prob": 42,
    },
    {
        "fight": "Pereira vs Hill",
        "fighter_a": "Alex Pereira",
        "fighter_b": "Jamahal Hill",
        "fighter_a_odds": -280,
        "fighter_b_odds": 220,
        "fighter_a_prob": 74,
        "fighter_b_prob": 31,
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
