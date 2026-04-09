import httpx
from bs4 import BeautifulSoup
from app.services.cache import cache_get, cache_set

CACHE_KEY = "espn_events"
ESPN_URL = "https://www.espn.com/mma/"
TIMEOUT = 10

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


async def fetch_events() -> list[dict]:
    cached = cache_get(CACHE_KEY, ttl=300)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(ESPN_URL, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        events = _parse_espn(soup)
        if events:
            cache_set(CACHE_KEY, events)
            return events
    except Exception:
        pass

    cache_set(CACHE_KEY, FALLBACK_EVENTS)
    return FALLBACK_EVENTS


def _parse_espn(soup: BeautifulSoup) -> list[dict]:
    events = []
    schedule = soup.select(".ScoreboardPage, .Card, .contentItem")
    if not schedule:
        return []

    event = {"name": "", "date": "", "location": "", "fights": []}
    headings = soup.select("h1, h2, .headline")
    for h in headings:
        text = h.get_text(strip=True)
        if "UFC" in text or "Fight Night" in text:
            event["name"] = text
            break

    links = soup.select("a")
    for link in links:
        text = link.get_text(strip=True)
        if (" vs " in text or " vs. " in text) and len(text) < 80:
            parts = text.replace(" vs. ", " vs ").split(" vs ")
            if len(parts) == 2:
                a_name = parts[0].strip()
                b_name = parts[1].strip()
                # Validate: names should be short, contain only letters/spaces/hyphens
                if (2 < len(a_name) < 40 and 2 < len(b_name) < 40
                        and all(c.isalpha() or c in " -'." for c in a_name)
                        and all(c.isalpha() or c in " -'." for c in b_name)):
                    event["fights"].append({
                        "fighter_a": a_name,
                        "fighter_b": b_name,
                        "weight_class": "",
                        "is_main_event": len(event["fights"]) == 0,
                    })

    # Only return if we got reasonable fight data
    if len(event["fights"]) >= 3:
        if not event["name"]:
            event["name"] = "Upcoming UFC Event"
        events.append(event)

    return events
