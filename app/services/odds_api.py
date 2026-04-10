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

async def fetch_events(query: str = "") -> list[dict]:
    # No date query → check cache first
    if not query:
        cached = cache_get("events_live", ttl=600)
        if cached:
            return cached

    # ALWAYS try the Odds API when key is available (it returns ALL events)
    if API_KEY:
        events = await _fetch_events_from_odds_api()
        if events:
            cache_set("events_live", events)
            # If user asked about a date, filter to matching events
            if query:
                filtered = _filter_events_by_query(events, query)
                if filtered:
                    return filtered
            return events

    # Try web search (with custom query if provided)
    events = await _fetch_events_from_web(query)
    if events:
        if not query:
            cache_set("events_live", events)
        return events

    # Fallback
    if not query:
        cache_set("events_live", FALLBACK_EVENTS)
    return FALLBACK_EVENTS


def _filter_events_by_query(events: list[dict], query: str) -> list[dict]:
    """Filter events to those matching a date in the query string."""
    import re
    # Extract month + day from query like "UFC event April 17 2026 fight card"
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})",
        query, re.IGNORECASE,
    )
    if not match:
        return []

    month_str = match.group(1)[:3]  # "Apr"
    day = match.group(2)

    filtered = []
    for ev in events:
        ev_date = ev.get("date", "")
        # Match "Sat, Apr 17" or "Apr 17" format
        if month_str.lower() in ev_date.lower() and day in re.findall(r"\d+", ev_date):
            filtered.append(ev)
    return filtered


def _is_ufc_event(evt: dict) -> bool:
    """Determine if an API event is a UFC fight (not regional MMA, BKFC, etc.)."""
    # Check all text fields for "UFC"
    for field in ("description", "sport_title", "id"):
        val = (evt.get(field) or "")
        if "ufc" in val.lower():
            return True

    # Check by known UFC fighter names (last names)
    home = (evt.get("home_team") or "").lower()
    away = (evt.get("away_team") or "").lower()
    home_last = home.split()[-1] if home else ""
    away_last = away.split()[-1] if away else ""
    for name in (home_last, away_last):
        if name in _KNOWN_UFC_FIGHTERS:
            return True

    return False


# Known UFC fighter last names — used to identify UFC events when the API
# doesn't include a description field. Kept broad to catch most cards.
_KNOWN_UFC_FIGHTERS = {
    # UFC 327 card (seeded)
    "prochazka", "ulberg", "murzakanov", "costa", "blaydes", "hokit",
    "reyes", "walker", "swanson", "landwehr", "pitbull", "pico",
    "holland", "brown", "gamrot", "ribovics",
    # Common UFC fighters
    "adesanya", "pereira", "strickland", "du plessis", "dvalishvili",
    "nurmagomedov", "volkanovski", "topuria", "makhachev", "oliveira",
    "poirier", "gaethje", "chandler", "mcgregor", "diaz", "covington",
    "edwards", "usman", "chimaev", "burns", "luque", "thompson",
    "jones", "aspinall", "miocic", "tuivasa", "gane", "lewis",
    "ankalaev", "hill", "rakic", "smith", "craig", "santos",
    "whittaker", "imavov", "cannonier", "brunson", "vettori",
    "gastelum", "nascimento", "romanov", "sherman", "dariush",
    "tsarukyan", "holloway", "allen", "emmett", "kattar", "yair",
    "moreno", "pantoja", "royval", "figueiredo", "kara-france",
    "shevchenko", "grasso", "fiorot", "namajunas", "zhang",
    "nunes", "pena", "aldana", "holm", "lemos", "andrade",
    "o'malley", "yan", "sandhagen", "font", "aldo", "cruz",
    "sterling", "dillashaw", "garbrandt", "barboza", "mitchell",
    "dober", "cerrone", "perry", "masvidal", "colby", "wonderboy",
    "nakatani", "perreira", "poppeck", "narkun",
    # Add more as needed
}


async def _fetch_events_from_odds_api() -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(EVENTS_URL, params={"apiKey": API_KEY})
            if resp.status_code != 200:
                print(f"[FightIQ] Odds API events: HTTP {resp.status_code}")
                return []
            resp.raise_for_status()

        raw = resp.json()
        print(f"[FightIQ] Events API returned {len(raw)} total MMA fights")
        if not raw:
            return []

        # Log a sample event so we can see available fields
        if raw:
            sample = raw[0]
            print(f"[FightIQ] Sample event fields: {list(sample.keys())}")
            print(f"[FightIQ] Sample: desc={sample.get('description')!r} "
                  f"home={sample.get('home_team')!r} away={sample.get('away_team')!r}")

        # Filter to UFC-only events
        ufc_fights = [evt for evt in raw if _is_ufc_event(evt)]
        print(f"[FightIQ] Filtered to {len(ufc_fights)} UFC fights (from {len(raw)} total)")

        if not ufc_fights:
            print("[FightIQ] WARNING: No UFC fights identified, using all events")
            ufc_fights = raw

        # Group fights by commence_time (events on the same day = same card)
        from collections import defaultdict
        cards = defaultdict(list)
        for evt in ufc_fights:
            date = evt.get("commence_time", "")[:10]  # YYYY-MM-DD
            cards[date].append(evt)
        print(f"[FightIQ] UFC events grouped into {len(cards)} cards: {list(cards.keys())}")

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
            for i, f in enumerate(fights[:15]):
                event["fights"].append({
                    "fighter_a": f.get("home_team", "TBD"),
                    "fighter_b": f.get("away_team", "TBD"),
                    "weight_class": "",
                    "is_main_event": i == 0,
                })
            events.append(event)

        return events[:3]
    except Exception as e:
        print(f"[FightIQ] Events API error: {e}")
        return []


async def _fetch_events_from_web(query: str = "") -> list[dict]:
    """Search the web for UFC events. Uses custom query if provided."""
    search_query = query or "UFC fight card schedule 2026 site:ufc.com OR site:espn.com"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": search_query},
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
            )
            resp.raise_for_status()

        import re
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text)

        # Look for "UFC XXX" event name
        name_match = re.search(r"(UFC\s+\d{3}[^.,:]{0,40})", text)
        event_name = name_match.group(1).strip() if name_match else "Upcoming UFC Event"

        # Extract fighter matchups — broader patterns to catch more names
        fights = []
        seen = set()
        patterns = [
            r"([A-Z][a-z]+(?:[-'\s][A-Z][a-z]+){0,3})\s+vs\.?\s+([A-Z][a-z]+(?:[-'\s][A-Z][a-z]+){0,3})",
            r"([A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})?)\s+(?:versus|v\.?s?\.?|against)\s+([A-Z][a-z]{2,}(?:\s[A-Z][a-z]{2,})?)",
        ]
        for pat in patterns:
            for match in re.finditer(pat, text):
                a, b = match.group(1).strip(), match.group(2).strip()
                key = f"{a.lower()}|{b.lower()}"
                if key in seen or 2 >= len(a) or len(a) >= 30 or 2 >= len(b) or len(b) >= 30:
                    continue
                seen.add(key)
                fights.append({
                    "fighter_a": a,
                    "fighter_b": b,
                    "weight_class": "",
                    "is_main_event": len(fights) == 0,
                })
                if len(fights) >= 12:
                    break
            if len(fights) >= 12:
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
                    "dateFormat": "iso",
                },
            )
            if resp.status_code != 200:
                print(f"[FightIQ] Odds API odds: HTTP {resp.status_code}")
                return []
            resp.raise_for_status()

        raw = resp.json()
        print(f"[FightIQ] Odds API returned {len(raw)} total fights with odds")

        # Filter to UFC-only
        ufc_events = [e for e in raw if _is_ufc_event(e)]
        events_to_parse = ufc_events if ufc_events else raw
        print(f"[FightIQ] Filtered to {len(events_to_parse)} UFC fights with odds (from {len(raw)} total)")

        results = []
        for event in events_to_parse:
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
    except Exception as e:
        print(f"[FightIQ] Odds API error: {e}")
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
    {"fight": "Swanson vs Landwehr", "fighter_a": "Cub Swanson", "fighter_b": "Nate Landwehr", "fighter_a_odds": 115, "fighter_b_odds": -135, "fighter_a_prob": 47, "fighter_b_prob": 57},
    {"fight": "Pitbull vs Pico", "fighter_a": "Patricio Pitbull", "fighter_b": "Aaron Pico", "fighter_a_odds": 140, "fighter_b_odds": -160, "fighter_a_prob": 42, "fighter_b_prob": 62},
    {"fight": "Holland vs Brown", "fighter_a": "Kevin Holland", "fighter_b": "Randy Brown", "fighter_a_odds": -110, "fighter_b_odds": -110, "fighter_a_prob": 52, "fighter_b_prob": 52},
    {"fight": "Gamrot vs Ribovics", "fighter_a": "Mateusz Gamrot", "fighter_b": "Esteban Ribovics", "fighter_a_odds": -300, "fighter_b_odds": 240, "fighter_a_prob": 75, "fighter_b_prob": 29},
]
