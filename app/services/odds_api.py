import os
import httpx
from app.services.cache import cache_get, cache_set

API_KEY = os.getenv("ODDS_API_KEY", "")
EVENTS_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/events"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
TIMEOUT = 12


def american_to_implied(odds: int) -> int:
    if odds < 0:
        return round(abs(odds) / (abs(odds) + 100) * 100)
    return round(100 / (odds + 100) * 100)


# ── Events (fight card) ──

async def fetch_events() -> list[dict]:
    cached = cache_get("events_live", ttl=600)
    if cached:
        return cached

    # Try The Odds API for live event data
    if API_KEY:
        events = await _fetch_events_from_odds_api()
        if events:
            cache_set("events_live", events)
            return events

    # Try web search
    events = await _fetch_events_from_web()
    if events:
        cache_set("events_live", events)
        return events

    # Fallback
    cache_set("events_live", FALLBACK_EVENTS)
    return FALLBACK_EVENTS


async def _fetch_events_from_odds_api() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(EVENTS_URL, params={"apiKey": API_KEY})
            resp.raise_for_status()

        raw = resp.json()
        if not raw:
            return []

        # Group fights by commence_time (events on the same day = same card)
        from collections import defaultdict
        cards = defaultdict(list)
        for evt in raw:
            date = evt.get("commence_time", "")[:10]  # YYYY-MM-DD
            cards[date].append(evt)

        events = []
        for date, fights in sorted(cards.items()):
            if not fights:
                continue
            event_name = _detect_event_name(fights)
            event = {
                "name": event_name,
                "date": _format_date(date),
                "location": "TBD",
                "fights": [],
            }
            for i, f in enumerate(fights):
                event["fights"].append({
                    "fighter_a": f.get("home_team", "TBD"),
                    "fighter_b": f.get("away_team", "TBD"),
                    "weight_class": "",
                    "is_main_event": i == 0,
                })
            events.append(event)

        return events[:3]  # Next 3 events max
    except Exception:
        return []


async def _fetch_events_from_web() -> list[dict]:
    """Search the web for the next UFC event."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": "next UFC event fight card 2026"},
                headers={"User-Agent": "Mozilla/5.0 (compatible; FightIQ/1.0)"},
            )
            resp.raise_for_status()

        import re
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text)

        # Look for "UFC XXX" event name
        name_match = re.search(r"(UFC\s+\d{3}[^.,:]{0,40})", text)
        event_name = name_match.group(1).strip() if name_match else "Upcoming UFC Event"

        # Extract fighter matchups
        fights = []
        for match in re.finditer(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+vs\.?\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", text):
            a, b = match.group(1).strip(), match.group(2).strip()
            if 2 < len(a) < 30 and 2 < len(b) < 30:
                fights.append({
                    "fighter_a": a,
                    "fighter_b": b,
                    "weight_class": "",
                    "is_main_event": len(fights) == 0,
                })
            if len(fights) >= 8:
                break

        if fights:
            return [{"name": event_name, "date": "Upcoming", "location": "TBD", "fights": fights}]
    except Exception:
        pass
    return []


def _detect_event_name(fights: list) -> str:
    """Try to determine the UFC event name from the fights list."""
    if fights:
        home = fights[0].get("home_team", "")
        away = fights[0].get("away_team", "")
        if home and away:
            return f"UFC: {home.split()[-1]} vs {away.split()[-1]}"
    return "Upcoming UFC Event"


def _format_date(date_str: str) -> str:
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%a, %b %d")
    except Exception:
        return date_str


# ── Odds ──

async def fetch_odds() -> list[dict]:
    cached = cache_get("odds_live", ttl=120)
    if cached:
        return cached

    if API_KEY:
        odds = await _fetch_odds_from_api()
        if odds:
            cache_set("odds_live", odds)
            return odds

    cache_set("odds_live", FALLBACK_ODDS)
    return FALLBACK_ODDS


async def _fetch_odds_from_api() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(
                ODDS_URL,
                params={
                    "apiKey": API_KEY,
                    "regions": "us",
                    "markets": "h2h",
                    "oddsFormat": "american",
                },
            )
            resp.raise_for_status()

        raw = resp.json()
        results = []
        for event in raw:
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
    except Exception:
        return []


# ── Fallback Data (only used when APIs are unavailable) ──

FALLBACK_EVENTS = [
    {
        "name": "UFC 327: Prochazka vs Ulberg",
        "date": "Sat, Apr 11 – 9 PM ET",
        "location": "Kaseya Center, Miami, FL",
        "fights": [
            {"fighter_a": "Jiri Prochazka", "fighter_b": "Carlos Ulberg", "weight_class": "Light Heavyweight Title", "is_main_event": True},
            {"fighter_a": "Azamat Murzakanov", "fighter_b": "Paulo Costa", "weight_class": "Light Heavyweight", "is_main_event": False},
            {"fighter_a": "Curtis Blaydes", "fighter_b": "Josh Hokit", "weight_class": "Heavyweight", "is_main_event": False},
            {"fighter_a": "Dominick Reyes", "fighter_b": "Johnny Walker", "weight_class": "Light Heavyweight", "is_main_event": False},
            {"fighter_a": "Cub Swanson", "fighter_b": "Nate Landwehr", "weight_class": "Featherweight", "is_main_event": False},
            {"fighter_a": "Patricio Pitbull", "fighter_b": "Aaron Pico", "weight_class": "Featherweight", "is_main_event": False},
            {"fighter_a": "Kevin Holland", "fighter_b": "Randy Brown", "weight_class": "Welterweight", "is_main_event": False},
            {"fighter_a": "Mateusz Gamrot", "fighter_b": "Esteban Ribovics", "weight_class": "Lightweight", "is_main_event": False},
        ],
    }
]

FALLBACK_ODDS = [
    {"fight": "Prochazka vs Ulberg", "fighter_a": "Jiri Prochazka", "fighter_b": "Carlos Ulberg", "fighter_a_odds": -121, "fighter_b_odds": 102, "fighter_a_prob": 55, "fighter_b_prob": 50},
    {"fight": "Murzakanov vs Costa", "fighter_a": "Azamat Murzakanov", "fighter_b": "Paulo Costa", "fighter_a_odds": -175, "fighter_b_odds": 150, "fighter_a_prob": 64, "fighter_b_prob": 40},
    {"fight": "Blaydes vs Hokit", "fighter_a": "Curtis Blaydes", "fighter_b": "Josh Hokit", "fighter_a_odds": -200, "fighter_b_odds": 170, "fighter_a_prob": 67, "fighter_b_prob": 37},
    {"fight": "Reyes vs Walker", "fighter_a": "Dominick Reyes", "fighter_b": "Johnny Walker", "fighter_a_odds": 110, "fighter_b_odds": -130, "fighter_a_prob": 48, "fighter_b_prob": 57},
    {"fight": "Pitbull vs Pico", "fighter_a": "Patricio Pitbull", "fighter_b": "Aaron Pico", "fighter_a_odds": 140, "fighter_b_odds": -160, "fighter_a_prob": 42, "fighter_b_prob": 62},
]
