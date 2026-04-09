import re

from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.stats_agent import get_fighter_stats, compare_fighters
from app.agents.research_agent import analyze_matchup
from app.agents.betting_agent import analyze_betting
from app.services.odds_api import fetch_odds
from app.services.espn import fetch_events
from app.services.search import search_fighter_stats, search_fight_info

NOISE_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "for", "and", "but", "or",
    "nor", "not", "so", "yet", "both", "each", "all", "any", "few",
    "more", "most", "other", "some", "such", "no", "only", "own",
    "same", "than", "too", "very", "just", "about", "above", "after",
    "before", "between", "into", "through", "during", "of", "at", "by",
    "with", "from", "up", "out", "on", "off", "over", "under", "to",
    "in", "it", "its", "this", "that", "these", "those", "what", "which",
    "who", "whom", "how", "when", "where", "why", "if", "then", "me",
    "my", "i", "you", "your", "he", "she", "they", "we", "us",
    "show", "tell", "give", "get", "list", "find", "look", "search",
    "stats", "stat", "record", "compare", "versus", "fight", "fighter",
    "fights", "card", "event", "odds", "bet", "bets", "betting",
    "predict", "prediction", "analysis", "breakdown", "wins", "win",
    "best", "pick", "picks", "ufc", "mma", "prelim", "prelims",
    "main", "tonight", "next", "upcoming", "current", "info",
}


def detect_intent(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["odds", "bet", "money", "wager", "pick", "value", "line"]):
        return "betting"
    if any(w in msg for w in ["stat", "compare", "record", "takedown", "strike", "accuracy", "reach", "height"]):
        return "stats"
    if any(w in msg for w in ["fight", "card", "event", "ufc", "tonight", "next", "when", "prelim", "main card", "list"]):
        return "fights"
    if any(w in msg for w in ["predict", "win", "who", "analysis", "breakdown", "chance", "beat"]):
        return "analysis"
    return "general"


# Known fighters on the current card
NAME_MAP = {
    "prochazka": "Jiri Prochazka", "jiri": "Jiri Prochazka",
    "ulberg": "Carlos Ulberg",
    "murzakanov": "Azamat Murzakanov", "azamat": "Azamat Murzakanov",
    "costa": "Paulo Costa", "paulo": "Paulo Costa",
    "blaydes": "Curtis Blaydes", "curtis": "Curtis Blaydes",
    "hokit": "Josh Hokit",
    "reyes": "Dominick Reyes", "dominick": "Dominick Reyes",
    "walker": "Johnny Walker", "johnny": "Johnny Walker",
    "swanson": "Cub Swanson", "cub": "Cub Swanson",
    "landwehr": "Nate Landwehr",
    "pitbull": "Patricio Pitbull", "patricio": "Patricio Pitbull",
    "pico": "Aaron Pico", "aaron": "Aaron Pico",
    "holland": "Kevin Holland", "kevin": "Kevin Holland",
    "brown": "Randy Brown", "randy": "Randy Brown",
    "gamrot": "Mateusz Gamrot", "mateusz": "Mateusz Gamrot",
    "ribovics": "Esteban Ribovics", "esteban": "Esteban Ribovics",
}


def find_fighters_in_message(msg: str) -> list[str]:
    msg_lower = msg.lower()
    found = []

    # Check known fighters first
    for key, full_name in NAME_MAP.items():
        if key in msg_lower and full_name not in found:
            found.append(full_name)

    if len(found) >= 2:
        return found[:2]

    # Try to extract unknown fighter names from "vs" pattern
    vs_match = re.search(r"([A-Za-z\s\-']+?)\s+(?:vs\.?|versus)\s+([A-Za-z\s\-']+)", msg, re.IGNORECASE)
    if vs_match:
        for group_idx in [1, 2]:
            name = vs_match.group(group_idx).strip()
            # Clean up: remove noise words from the start
            words = name.split()
            cleaned = [w for w in words if w.lower() not in NOISE_WORDS]
            if cleaned:
                clean_name = " ".join(cleaned).title()
                if clean_name not in found and len(clean_name) > 2:
                    found.append(clean_name)

    if found:
        return found[:2]

    # Try to detect a single name: look for capitalized words that aren't noise
    words = re.findall(r"[A-Za-z\-']+", msg)
    potential_names = [w for w in words if w.lower() not in NOISE_WORDS and len(w) > 2]
    if potential_names:
        # Join consecutive potential name words
        name = " ".join(potential_names[:3]).title()
        found.append(name)

    return found[:2]


def _format_fight_card(events: list[dict]) -> str:
    if not events:
        return "No upcoming events found."

    lines = []
    for ev in events:
        lines.append(f"**{ev.get('name', 'UFC Event')}**")
        lines.append(f"{ev.get('date', 'TBD')} — {ev.get('location', 'TBD')}")
        lines.append("")

        main_card = []
        prelims = []
        for i, f in enumerate(ev.get("fights", [])):
            fa = f.get("fighter_a", "TBD")
            fb = f.get("fighter_b", "TBD")
            wc = f.get("weight_class", "")
            wc_str = f" ({wc})" if wc else ""
            if f.get("is_main_event"):
                main_card.insert(0, f"🏆 **Main Event:** {fa} vs {fb}{wc_str}")
            elif i < 5:
                main_card.append(f"  {fa} vs {fb}{wc_str}")
            else:
                prelims.append(f"  {fa} vs {fb}{wc_str}")

        if main_card:
            lines.append("**Main Card:**")
            lines.extend(main_card)

        if prelims:
            lines.append("")
            lines.append("**Prelims:**")
            lines.extend(prelims)

    return "\n".join(lines)


async def process_chat(message: str, db: AsyncSession) -> dict:
    intent = detect_intent(message)
    fighters = find_fighters_in_message(message)

    if intent == "fights":
        events = await fetch_events()
        text = _format_fight_card(events)
        return {"intent": intent, "response": text, "data": events}

    if intent == "stats" and fighters:
        if len(fighters) >= 2:
            comp = await compare_fighters(fighters[0], fighters[1], db)
            a = comp.get("fighter_a", {})
            b = comp.get("fighter_b", {})
            if a and b:
                text = (
                    f"**{a['name']}** vs **{b['name']}**\n\n"
                    f"Record: {a['wins']}-{a['losses']} vs {b['wins']}-{b['losses']}\n"
                    f"Strikes/Min: {a['strikes_per_min']} vs {b['strikes_per_min']}\n"
                    f"Strike Accuracy: {a['strike_accuracy']}% vs {b['strike_accuracy']}%\n"
                    f"Takedowns/15m: {a['takedowns_avg']} vs {b['takedowns_avg']}\n"
                    f"TD Defense: {a['td_defense']}% vs {b['td_defense']}%\n"
                    f"Sub Attempts: {a['submission_avg']} vs {b['submission_avg']}\n"
                    f"Win Streak: {a['win_streak']} vs {b['win_streak']}"
                )
                return {"intent": intent, "response": text, "data": comp}
            # Partial: one found, one not
            found_fighter = a or b
            missing = fighters[1] if a else fighters[0]
            if found_fighter:
                text = (
                    f"Found **{found_fighter['name']}** but couldn't find stats for **{missing}**.\n\n"
                    f"**{found_fighter['name']}**: {found_fighter['wins']}-{found_fighter['losses']}, "
                    f"{found_fighter['strikes_per_min']} SLpM"
                )
                return {"intent": intent, "response": text, "data": comp}
        else:
            stats = await get_fighter_stats(fighters[0], db)
            if stats:
                source_tag = " *(via web)*" if stats.get("source") == "web_search" else ""
                text = f"**{stats['name']}**{source_tag}\n"
                text += f"Record: {stats['wins']}-{stats['losses']}"
                if stats.get("win_streak"):
                    text += f" ({stats['win_streak']} win streak)"
                text += "\n"
                if stats.get("strikes_per_min"):
                    text += f"Strikes/Min: {stats['strikes_per_min']} | Accuracy: {stats['strike_accuracy']}%\n"
                if stats.get("takedowns_avg"):
                    text += f"Takedowns: {stats['takedowns_avg']}/15m | TD Defense: {stats['td_defense']}%\n"
                if stats.get("submission_avg"):
                    text += f"Submissions: {stats['submission_avg']}/15m\n"
                if stats.get("height") and stats["height"] != "N/A":
                    text += f"Height: {stats['height']} | Reach: {stats['reach']}\" | Stance: {stats.get('stance', 'N/A')}"
                return {"intent": intent, "response": text, "data": stats}
            else:
                text = f"Couldn't find stats for **{fighters[0]}**. Searched database and web.\n\nTry a fighter on the current card like: Prochazka, Ulberg, Costa, Blaydes"
                return {"intent": intent, "response": text, "data": None}

    if intent in ("analysis", "betting", "general") and len(fighters) >= 2:
        a = await get_fighter_stats(fighters[0], db)
        b = await get_fighter_stats(fighters[1], db)
        if a and b:
            prediction = analyze_matchup(a, b)
            if intent == "betting":
                all_odds = await fetch_odds()
                fight_odds = None
                for o in all_odds:
                    if (fighters[0].split()[-1].lower() in o["fight"].lower() or
                            fighters[1].split()[-1].lower() in o["fight"].lower()):
                        fight_odds = o
                        break
                betting = analyze_betting(a, b, fight_odds, prediction)
                bets_text = []
                for bet in betting["all_bets"]:
                    bets_text.append(f"• **{bet['bet']}** ({bet['odds']}) — Risk: {bet['risk']}\n  {bet['reasoning']}")
                text = (
                    f"**Betting Analysis: {a['name']} vs {b['name']}**\n\n"
                    + "\n".join(bets_text)
                )
                return {"intent": intent, "response": text, "data": betting}

            text = (
                f"**{prediction['predicted_winner']}** predicted to win by {prediction['method']} "
                f"({prediction['confidence']}% confidence)\n\n"
                f"Key factors:\n" +
                "\n".join(f"• {f}" for f in prediction["factors"])
            )
            return {"intent": intent, "response": text, "data": prediction}

    if fighters:
        stats = await get_fighter_stats(fighters[0], db)
        if stats:
            source_tag = " *(via web search)*" if stats.get("source") == "web_search" else ""
            text = (
                f"**{stats['name']}**{source_tag}\n"
                f"Record: {stats['wins']}-{stats['losses']}\n"
            )
            if stats.get("strikes_per_min"):
                text += f"Strikes: {stats['strikes_per_min']}/min | Takedowns: {stats['takedowns_avg']}/15m\n"
            if stats.get("height") and stats["height"] != "N/A":
                text += f"Height: {stats['height']} | Reach: {stats['reach']}\" | Stance: {stats.get('stance', 'N/A')}\n"
            text += f"\nTry: \"compare {stats['name'].split()[-1]} vs [opponent]\" or \"who wins {stats['name'].split()[-1]} vs [opponent]\""
            return {"intent": "general", "response": text, "data": stats}
        else:
            text = (
                f"Couldn't find stats for **{fighters[0]}**. Searched the database and web.\n\n"
                f"Try a UFC fighter name like: Prochazka, Ulberg, Costa, Blaydes, Holloway, etc."
            )
            return {"intent": "general", "response": text, "data": None}

    # Default — show the fight card
    events = await fetch_events()
    text = (
        "Welcome to **FightIQ AI**! 🥊\n\n"
        + _format_fight_card(events) + "\n\n"
        "Ask me anything:\n"
        "• \"Show the fight card\"\n"
        "• \"Stats for Prochazka\"\n"
        "• \"Who wins Prochazka vs Ulberg?\"\n"
        "• \"Best bets for Prochazka vs Ulberg\""
    )
    return {"intent": "general", "response": text, "data": None}
