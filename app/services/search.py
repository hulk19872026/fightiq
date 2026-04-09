import re
import httpx
from app.services.cache import cache_get, cache_set

TIMEOUT = 10
DDG_URL = "https://html.duckduckgo.com/html/"


async def search_fighter_stats(name: str) -> dict | None:
    cache_key = f"search_stats_{name.lower().replace(' ', '_')}"
    cached = cache_get(cache_key, ttl=600)
    if cached:
        return cached

    try:
        query = f"{name} UFC MMA fighter stats record sherdog"
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                DDG_URL,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; FightIQ/1.0)"},
            )
            resp.raise_for_status()

        stats = _parse_search_results(name, resp.text)
        if stats:
            cache_set(cache_key, stats)
            return stats
    except Exception:
        pass

    return None


def _parse_search_results(name: str, html: str) -> dict | None:
    stats = {
        "name": name,
        "source": "web_search",
    }

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    # Try to extract record (W-L or W-L-D)
    record_patterns = [
        rf"{re.escape(name)}[^0-9]{{0,60}}(\d{{1,2}})\s*-\s*(\d{{1,2}})(?:\s*-\s*(\d{{1,2}}))?",
        r"(?:Record|MMA record)[:\s]+(\d{1,2})\s*-\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?",
        r"(\d{1,2})\s*-\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s*(?:MMA|record|UFC)",
    ]
    for pattern in record_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            stats["wins"] = int(match.group(1))
            stats["losses"] = int(match.group(2))
            stats["draws"] = int(match.group(3)) if match.group(3) else 0
            break

    # Height
    height_match = re.search(r"""(\d)['\\u2019]\s*(\d{1,2})["\\u201D]?""", text)
    if height_match:
        stats["height"] = f"{height_match.group(1)}'{height_match.group(2)}\""

    # Reach
    reach_match = re.search(r"""[Rr]each[:\s]+(\d{2}(?:\.\d)?)["'\s]*(?:in)?""", text)
    if reach_match:
        stats["reach"] = float(reach_match.group(1))

    # Weight class
    for wc in ["Heavyweight", "Light Heavyweight", "Middleweight", "Welterweight",
                "Lightweight", "Featherweight", "Bantamweight", "Flyweight", "Strawweight"]:
        if wc.lower() in text.lower():
            stats["weight_class"] = wc
            break

    # Stance
    for stance in ["Orthodox", "Southpaw", "Switch"]:
        if stance.lower() in text.lower():
            stats["stance"] = stance
            break

    # SLpM (strikes landed per minute)
    slpm_match = re.search(r"(?:SLpM|Strikes?\s*(?:Landed\s*)?(?:per|/)\s*Min(?:ute)?)[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
    if slpm_match:
        stats["strikes_per_min"] = float(slpm_match.group(1))

    # Strike accuracy
    acc_match = re.search(r"(?:Str(?:ike|iking)?\.?\s*Acc(?:uracy)?)[:\s]+(\d{1,3})%?", text, re.IGNORECASE)
    if acc_match:
        stats["strike_accuracy"] = int(acc_match.group(1))

    # Takedowns
    td_match = re.search(r"(?:TD|Takedown)\s*(?:Avg|average)?[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
    if td_match:
        stats["takedowns_avg"] = float(td_match.group(1))

    # TD defense
    tdd_match = re.search(r"(?:TD|Takedown)\s*Def(?:ense)?[:\s]+(\d{1,3})%?", text, re.IGNORECASE)
    if tdd_match:
        stats["td_defense"] = int(tdd_match.group(1))

    # Submission avg
    sub_match = re.search(r"(?:Sub(?:mission)?\.?\s*Avg)[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
    if sub_match:
        stats["submission_avg"] = float(sub_match.group(1))

    # If we found at least a record, return the stats
    if "wins" in stats:
        return stats

    return None


async def search_fight_info(fighter_a: str, fighter_b: str) -> dict | None:
    cache_key = f"search_fight_{fighter_a}_{fighter_b}".lower().replace(" ", "_")
    cached = cache_get(cache_key, ttl=300)
    if cached:
        return cached

    try:
        query = f"{fighter_a} vs {fighter_b} UFC odds prediction 2026"
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                DDG_URL,
                data={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; FightIQ/1.0)"},
            )
            resp.raise_for_status()

        info = _parse_fight_search(fighter_a, fighter_b, resp.text)
        if info:
            cache_set(cache_key, info)
            return info
    except Exception:
        pass

    return None


def _parse_fight_search(fighter_a: str, fighter_b: str, html: str) -> dict | None:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    info = {"fighter_a": fighter_a, "fighter_b": fighter_b, "snippets": []}

    # Extract relevant snippets
    sentences = re.split(r"[.!]", text)
    keywords = [fighter_a.split()[-1].lower(), fighter_b.split()[-1].lower(),
                "odds", "prediction", "pick", "favorite", "underdog", "bet"]
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20 or len(sent) > 300:
            continue
        sent_lower = sent.lower()
        if sum(1 for kw in keywords if kw in sent_lower) >= 2:
            info["snippets"].append(sent)
            if len(info["snippets"]) >= 5:
                break

    # Try to extract odds
    a_last = fighter_a.split()[-1]
    b_last = fighter_b.split()[-1]
    odds_pattern = rf"({re.escape(a_last)}|{re.escape(b_last)})[^0-9]{{0,30}}([+-]\d{{3}})"
    for match in re.finditer(odds_pattern, text, re.IGNORECASE):
        name = match.group(1)
        odds_val = int(match.group(2))
        if name.lower() == a_last.lower():
            info["fighter_a_odds"] = odds_val
        else:
            info["fighter_b_odds"] = odds_val

    if info["snippets"] or "fighter_a_odds" in info:
        return info

    return None
