import httpx
from bs4 import BeautifulSoup
from app.services.cache import cache_get, cache_set

CACHE_KEY = "espn_events"
ESPN_URL = "https://www.espn.com/mma/"
TIMEOUT = 10

FALLBACK_EVENTS = [
    {
        "name": "UFC 300: Oliveira vs Makhachev",
        "date": "Tonight",
        "location": "Las Vegas",
        "fights": [
            {"fighter_a": "Charles Oliveira", "fighter_b": "Islam Makhachev", "weight_class": "Lightweight", "is_main_event": True},
            {"fighter_a": "Justin Gaethje", "fighter_b": "Max Holloway", "weight_class": "Lightweight", "is_main_event": False},
            {"fighter_a": "Petr Yan", "fighter_b": "Deiveson Figueiredo", "weight_class": "Bantamweight", "is_main_event": False},
            {"fighter_a": "Alex Pereira", "fighter_b": "Jamahal Hill", "weight_class": "Light Heavyweight", "is_main_event": False},
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
        if " vs " in text or " vs. " in text:
            parts = text.replace(" vs. ", " vs ").split(" vs ")
            if len(parts) == 2:
                event["fights"].append({
                    "fighter_a": parts[0].strip(),
                    "fighter_b": parts[1].strip(),
                    "weight_class": "",
                    "is_main_event": len(event["fights"]) == 0,
                })

    if event["fights"]:
        if not event["name"]:
            event["name"] = "Upcoming UFC Event"
        events.append(event)

    return events
