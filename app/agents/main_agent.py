from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.stats_agent import get_fighter_stats, compare_fighters
from app.agents.research_agent import analyze_matchup
from app.agents.betting_agent import analyze_betting
from app.services.odds_api import fetch_odds
from app.services.espn import fetch_events

FIGHTER_NAMES = [
    "makhachev", "oliveira", "gaethje", "holloway",
    "yan", "figueiredo", "pereira", "hill",
]


def detect_intent(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["odds", "bet", "money", "wager", "pick", "value"]):
        return "betting"
    if any(w in msg for w in ["stat", "compare", "record", "takedown", "strike", "accuracy"]):
        return "stats"
    if any(w in msg for w in ["fight", "card", "event", "ufc", "tonight", "next", "when"]):
        return "fights"
    if any(w in msg for w in ["predict", "win", "who", "analysis", "breakdown", "chance"]):
        return "analysis"
    return "general"


def find_fighters_in_message(msg: str) -> list[str]:
    msg_lower = msg.lower()
    found = []
    name_map = {
        "makhachev": "Islam Makhachev", "islam": "Islam Makhachev",
        "oliveira": "Charles Oliveira", "charles": "Charles Oliveira", "do bronx": "Charles Oliveira",
        "gaethje": "Justin Gaethje", "justin": "Justin Gaethje",
        "holloway": "Max Holloway", "max": "Max Holloway",
        "yan": "Petr Yan", "petr": "Petr Yan",
        "figueiredo": "Deiveson Figueiredo", "figgy": "Deiveson Figueiredo",
        "pereira": "Alex Pereira", "alex": "Alex Pereira",
        "hill": "Jamahal Hill", "jamahal": "Jamahal Hill",
    }
    for key, full_name in name_map.items():
        if key in msg_lower and full_name not in found:
            found.append(full_name)
    return found[:2]


async def process_chat(message: str, db: AsyncSession) -> dict:
    intent = detect_intent(message)
    fighters = find_fighters_in_message(message)

    if intent == "fights":
        events = await fetch_events()
        fights_text = []
        for ev in events:
            fights_text.append(f"**{ev['name']}** — {ev.get('date', 'TBD')} in {ev.get('location', 'TBD')}")
            for i, f in enumerate(ev["fights"]):
                tag = "🏆 Main Event" if f.get("is_main_event") else f"  Fight {i+1}"
                fights_text.append(f"{tag}: {f['fighter_a']} vs {f['fighter_b']}")
        return {"intent": intent, "response": "\n".join(fights_text), "data": events}

    if intent == "stats" and fighters:
        if len(fighters) >= 2:
            comp = await compare_fighters(fighters[0], fighters[1], db)
            a = comp.get("fighter_a", {})
            b = comp.get("fighter_b", {})
            if a and b:
                text = (
                    f"**{a['name']}** vs **{b['name']}**\n\n"
                    f"Strikes/Min: {a['strikes_per_min']} vs {b['strikes_per_min']}\n"
                    f"Strike Accuracy: {a['strike_accuracy']}% vs {b['strike_accuracy']}%\n"
                    f"Takedowns/15m: {a['takedowns_avg']} vs {b['takedowns_avg']}\n"
                    f"TD Defense: {a['td_defense']}% vs {b['td_defense']}%\n"
                    f"Sub Attempts: {a['submission_avg']} vs {b['submission_avg']}\n"
                    f"Record: {a['wins']}-{a['losses']} vs {b['wins']}-{b['losses']}"
                )
                return {"intent": intent, "response": text, "data": comp}
        else:
            stats = await get_fighter_stats(fighters[0], db)
            if stats:
                text = (
                    f"**{stats['name']}**\n"
                    f"Record: {stats['wins']}-{stats['losses']} ({stats['win_streak']} win streak)\n"
                    f"Strikes/Min: {stats['strikes_per_min']} | Accuracy: {stats['strike_accuracy']}%\n"
                    f"Takedowns: {stats['takedowns_avg']}/15m | TD Defense: {stats['td_defense']}%\n"
                    f"Submissions: {stats['submission_avg']}/15m\n"
                    f"Height: {stats['height']} | Reach: {stats['reach']}\" | Stance: {stats['stance']}"
                )
                return {"intent": intent, "response": text, "data": stats}

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
            text = (
                f"**{stats['name']}** — {stats['wins']}-{stats['losses']}\n"
                f"Strikes: {stats['strikes_per_min']}/min | Takedowns: {stats['takedowns_avg']}/15m\n"
                f"What would you like to know? Try asking about odds, predictions, or compare with another fighter."
            )
            return {"intent": "general", "response": text, "data": stats}

    events = await fetch_events()
    text = (
        "Welcome to **FightIQ**! 🥊\n\n"
        "I can help you with:\n"
        "• **Fight cards** — \"What fights are tonight?\"\n"
        "• **Fighter stats** — \"Show me Oliveira's stats\"\n"
        "• **Comparisons** — \"Compare Makhachev vs Oliveira\"\n"
        "• **Predictions** — \"Who wins Makhachev vs Oliveira?\"\n"
        "• **Betting** — \"Best bets for Oliveira vs Makhachev\""
    )
    return {"intent": "general", "response": text, "data": None}
