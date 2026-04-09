import re

from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.stats_agent import get_fighter_stats, compare_fighters
from app.agents.research_agent import analyze_matchup
from app.agents.betting_agent import analyze_betting, build_parlay, build_best_bets_card
from app.services.odds_api import fetch_odds
from app.services.espn import fetch_events
from app.services.search import search_fighter_stats, search_fight_info


# ── Intent Classification ──

INTENT_KEYWORDS = {
    "deep_analysis": [
        "break down", "breakdown", "break this", "analyze", "analysis",
        "deep dive", "who wins and why", "full breakdown", "matchup analysis",
    ],
    "parlay": [
        "parlay", "multi", "accumulator", "acca", "combo bet",
        "3 leg", "4 leg", "5 leg", "2 leg", "leg parlay",
    ],
    "build_bet": [
        "make me a bet", "make a bet", "build a bet", "give me a bet",
        "build me a", "make me a", "best parlay", "safest bet",
        "lock of the night", "locks", "sure thing", "gimme a pick",
        "what should i bet", "what to bet", "best bets tonight",
        "best bets", "top picks", "tonight's picks", "who do i bet on",
    ],
    "betting": [
        "odds", "bet", "bets", "betting", "money", "wager", "pick", "picks",
        "value", "line", "lines", "prop", "moneyline", "spread",
        "over under", "best bet",
    ],
    "prediction": [
        "predict", "prediction", "who wins", "who will win", "winner",
        "who takes", "chance", "beat", "beats", "winning",
    ],
    "stats": [
        "stat", "stats", "record", "takedown", "strike", "accuracy",
        "reach", "height", "weight", "compare", "comparison", "vs",
    ],
    "fights": [
        "fight card", "card", "event", "tonight", "next fight", "when",
        "prelim", "prelims", "main card", "upcoming", "schedule",
        "what fights", "list fights",
    ],
    "live": [
        "latest", "today", "current", "live", "right now", "recent",
        "news", "update",
    ],
}


def classify_intent(message: str) -> str:
    msg = message.lower()

    # Deep analysis gets highest priority
    for kw in INTENT_KEYWORDS["deep_analysis"]:
        if kw in msg:
            return "deep_analysis"

    # Parlay requests
    for kw in INTENT_KEYWORDS["parlay"]:
        if kw in msg:
            return "parlay"

    # "Make me a bet" / "best bets tonight"
    for kw in INTENT_KEYWORDS["build_bet"]:
        if kw in msg:
            return "build_bet"

    # Then check other intents by specificity
    for intent in ["betting", "prediction", "stats", "fights", "live"]:
        for kw in INTENT_KEYWORDS[intent]:
            if kw in msg:
                return intent

    return "chat"


# ── Fighter Name Extraction ──

NAME_MAP = {
    "prochazka": "Jiri Prochazka", "jiri": "Jiri Prochazka",
    "ulberg": "Carlos Ulberg", "carlos": "Carlos Ulberg",
    "murzakanov": "Azamat Murzakanov", "azamat": "Azamat Murzakanov",
    "costa": "Paulo Costa", "paulo costa": "Paulo Costa",
    "blaydes": "Curtis Blaydes", "curtis": "Curtis Blaydes",
    "hokit": "Josh Hokit",
    "reyes": "Dominick Reyes", "dominick": "Dominick Reyes",
    "walker": "Johnny Walker", "johnny walker": "Johnny Walker",
    "swanson": "Cub Swanson", "cub": "Cub Swanson",
    "landwehr": "Nate Landwehr",
    "pitbull": "Patricio Pitbull", "patricio": "Patricio Pitbull",
    "pico": "Aaron Pico",
    "holland": "Kevin Holland",
    "brown": "Randy Brown",
    "gamrot": "Mateusz Gamrot", "mateusz": "Mateusz Gamrot",
    "ribovics": "Esteban Ribovics", "esteban": "Esteban Ribovics",
}

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "be", "for", "and", "but", "or",
    "not", "so", "do", "does", "did", "will", "would", "could", "should",
    "can", "of", "at", "by", "with", "from", "to", "in", "on", "it", "this",
    "that", "what", "who", "how", "me", "my", "i", "you", "your", "we",
    "show", "tell", "give", "get", "find", "about", "think", "know",
    "fight", "fighter", "ufc", "mma", "stats", "stat", "record", "compare",
    "versus", "betting", "odds", "bet", "bets", "predict", "prediction",
    "analysis", "breakdown", "wins", "win", "best", "pick", "picks",
    "prelim", "prelims", "main", "card", "event", "tonight", "next",
    "upcoming", "current", "list", "between", "against", "why", "break",
    "down", "deep", "full", "analyze", "which", "if", "has", "have",
    "value", "line", "over", "under", "up", "out",
    "hey", "hi", "hello", "sup", "yo", "whats", "good", "thanks",
    "thank", "please", "help", "yes", "no", "yeah", "nah", "ok",
    "okay", "sure", "right", "well", "like", "want", "need",
    "man", "bro", "dude", "lol", "lmao", "great", "cool", "nice",
    "awesome", "got", "let", "much", "many", "really", "going",
    "think", "know", "see", "say", "make", "take", "come", "go",
}


def find_fighters(msg: str) -> list[str]:
    msg_lower = msg.lower()
    found = []

    # Check known name map first
    for key, full_name in NAME_MAP.items():
        if key in msg_lower and full_name not in found:
            found.append(full_name)
    if len(found) >= 2:
        return found[:2]

    # Extract from "X vs Y" pattern
    vs_match = re.search(
        r"([A-Za-z\s\-']+?)\s+(?:vs\.?|versus|against|and)\s+([A-Za-z\s\-']+)",
        msg, re.IGNORECASE,
    )
    if vs_match:
        for idx in [1, 2]:
            raw = vs_match.group(idx).strip()
            words = [w for w in raw.split() if w.lower() not in STOP_WORDS and len(w) > 1]
            if words:
                name = " ".join(words).title()
                if name not in found and len(name) > 2:
                    found.append(name)

    if len(found) >= 2:
        return found[:2]

    # Single name detection — only if message seems fighter-related
    # (has "stats", "record", etc. or a recognizable proper noun pattern)
    if not found:
        words = re.findall(r"[A-Za-z\-']+", msg)
        candidates = [w for w in words if w.lower() not in STOP_WORDS and len(w) > 2]
        # Only treat as a name if there are 1-3 candidates and message is short
        if 1 <= len(candidates) <= 3 and len(msg.split()) <= 8:
            found.append(" ".join(candidates).title())

    return found[:2]


# ── Response Formatters ──

def _format_fight_card(events: list[dict]) -> str:
    if not events:
        return "No upcoming events found."
    lines = []
    for ev in events:
        lines.append(f"🔥 **{ev.get('name', 'UFC Event')}**")
        lines.append(f"📅 {ev.get('date', 'TBD')} — {ev.get('location', 'TBD')}")
        lines.append("")
        main_fights = []
        prelim_fights = []
        for i, f in enumerate(ev.get("fights", [])):
            fa, fb = f.get("fighter_a", "TBD"), f.get("fighter_b", "TBD")
            wc = f" • {f['weight_class']}" if f.get("weight_class") else ""
            if f.get("is_main_event"):
                main_fights.insert(0, f"🏆 {fa} vs {fb}{wc}")
            elif i < 5:
                main_fights.append(f"  ⚔️ {fa} vs {fb}{wc}")
            else:
                prelim_fights.append(f"  ⚔️ {fa} vs {fb}{wc}")
        if main_fights:
            lines.append("**Main Card:**")
            lines.extend(main_fights)
        if prelim_fights:
            lines.append("\n**Prelims:**")
            lines.extend(prelim_fights)
    return "\n".join(lines)


def _format_stats(stats: dict) -> str:
    src = " _(via web)_" if stats.get("source") == "web_search" else ""
    text = f"📊 **{stats['name']}**{src}\n\n"
    text += f"**Record:** {stats['wins']}-{stats['losses']}"
    if stats.get("win_streak"):
        text += f" ({stats['win_streak']} fight win streak 🔥)"
    text += "\n"
    if stats.get("strikes_per_min"):
        text += f"**Striking:** {stats['strikes_per_min']} SLpM | {stats.get('strike_accuracy', 0)}% accuracy\n"
    if stats.get("takedowns_avg"):
        text += f"**Wrestling:** {stats['takedowns_avg']} TD/15m | {stats.get('td_defense', 0)}% TD defense\n"
    if stats.get("submission_avg"):
        text += f"**Submissions:** {stats['submission_avg']}/15m\n"
    if stats.get("height") and stats["height"] != "N/A":
        text += f"**Physical:** {stats['height']} | {stats.get('reach', 'N/A')}\" reach | {stats.get('stance', 'N/A')}"
    return text


def _format_deep_analysis(a: dict, b: dict, prediction: dict, betting_data: dict | None, odds_data: dict | None) -> str:
    lines = [
        f"🔥 **Fight Breakdown: {a['name']} vs {b['name']}**\n",
        "---",
        f"\n📊 **Stats Summary**\n",
        f"| Stat | {a['name'].split()[-1]} | {b['name'].split()[-1]} |",
        f"|---|---|---|",
        f"| Record | {a['wins']}-{a['losses']} | {b['wins']}-{b['losses']} |",
        f"| Win Streak | {a.get('win_streak', 0)} | {b.get('win_streak', 0)} |",
        f"| Strikes/Min | {a.get('strikes_per_min', 0)} | {b.get('strikes_per_min', 0)} |",
        f"| Str. Accuracy | {a.get('strike_accuracy', 0)}% | {b.get('strike_accuracy', 0)}% |",
        f"| Takedowns | {a.get('takedowns_avg', 0)}/15m | {b.get('takedowns_avg', 0)}/15m |",
        f"| TD Defense | {a.get('td_defense', 0)}% | {b.get('td_defense', 0)}% |",
        f"| Submissions | {a.get('submission_avg', 0)}/15m | {b.get('submission_avg', 0)}/15m |",
    ]

    # Analysis section
    lines.append(f"\n🧠 **Analysis**\n")
    for factor in prediction.get("factors", []):
        lines.append(f"• {factor}")

    # Style breakdown
    a_style = "Striker" if a.get("striking", 0) > a.get("wrestling", 0) else "Grappler"
    b_style = "Striker" if b.get("striking", 0) > b.get("wrestling", 0) else "Grappler"
    if a_style != b_style:
        lines.append(f"\nThis is a classic **{a_style} vs {b_style}** matchup.")
    else:
        lines.append(f"\nBoth fighters are primarily **{a_style}s** — expect a technical battle on the feet.")

    # Prediction
    conf = prediction.get("confidence", 50)
    emoji = "🟢" if conf > 65 else "🟡" if conf > 55 else "🔴"
    lines.append(f"\n⚔️ **Prediction**\n")
    lines.append(f"{emoji} **{prediction['predicted_winner']}** by {prediction['method']}")
    lines.append(f"Confidence: {conf}%")

    # Betting insight
    if betting_data and betting_data.get("all_bets"):
        lines.append(f"\n💰 **Betting Insight**\n")
        if odds_data:
            lines.append(
                f"Lines: {odds_data.get('fighter_a', 'A')} "
                f"({'+' if odds_data.get('fighter_a_odds', 0) > 0 else ''}{odds_data.get('fighter_a_odds', '?')}) / "
                f"{odds_data.get('fighter_b', 'B')} "
                f"({'+' if odds_data.get('fighter_b_odds', 0) > 0 else ''}{odds_data.get('fighter_b_odds', '?')})"
            )
        for bet in betting_data["all_bets"][:3]:
            risk_emoji = "🟢" if bet["risk"] == "Low" else "🟡" if bet["risk"] == "Medium" else "🔴"
            lines.append(f"• {risk_emoji} **{bet['bet']}** ({bet['odds']}) — {bet['risk']} risk")
            lines.append(f"  _{bet['reasoning']}_")

    return "\n".join(lines)


# ── Fight Pairs for Card-Wide Analysis ──

CARD_FIGHTS = [
    ("Jiri Prochazka", "Carlos Ulberg"),
    ("Azamat Murzakanov", "Paulo Costa"),
    ("Curtis Blaydes", "Josh Hokit"),
    ("Dominick Reyes", "Johnny Walker"),
    ("Cub Swanson", "Nate Landwehr"),
    ("Patricio Pitbull", "Aaron Pico"),
    ("Kevin Holland", "Randy Brown"),
    ("Mateusz Gamrot", "Esteban Ribovics"),
]


async def _analyze_all_fights(db: AsyncSession) -> list[dict]:
    """Run analysis on all fights on the card."""
    all_odds = await fetch_odds()
    results = []

    for fa_name, fb_name in CARD_FIGHTS:
        a = await get_fighter_stats(fa_name, db)
        b = await get_fighter_stats(fb_name, db)
        if not a or not b:
            continue

        prediction = analyze_matchup(a, b)
        fight_odds = _find_odds([fa_name, fb_name], all_odds)

        # Determine winner odds
        winner_odds = -150  # default
        if fight_odds:
            if prediction["predicted_winner"] == fa_name:
                winner_odds = fight_odds.get("fighter_a_odds", -150)
            else:
                winner_odds = fight_odds.get("fighter_b_odds", -150)

        betting = analyze_betting(a, b, fight_odds, prediction)

        results.append({
            "fighter_a": fa_name,
            "fighter_b": fb_name,
            "predicted_winner": prediction["predicted_winner"],
            "method": prediction["method"],
            "confidence": prediction["confidence"],
            "winner_odds": winner_odds,
            "reasoning": prediction["factors"][0] if prediction["factors"] else "",
            "betting": betting,
        })

    return results


async def _handle_parlay(num_legs: int, db: AsyncSession) -> dict:
    """Build a parlay with the specified number of legs."""
    analyses = await _analyze_all_fights(db)
    if not analyses:
        return {"intent": "parlay", "response": "Couldn't analyze fights for parlay.", "data": None}

    parlay = build_parlay(analyses, num_legs)

    lines = [
        f"🎰 **{parlay['num_legs']}-Leg Parlay**\n",
        "---\n",
    ]

    for i, leg in enumerate(parlay["legs"], 1):
        conf = leg["confidence"]
        emoji = "🟢" if conf > 65 else "🟡" if conf > 55 else "🔴"
        lines.append(f"**Leg {i}:** {emoji} **{leg['fighter']}** ({leg['odds']})")
        lines.append(f"  By {leg['method']} — {conf}% confidence")
        if leg.get("reasoning"):
            lines.append(f"  _{leg['reasoning']}_\n")

    lines.append("---\n")
    lines.append(f"💰 **Combined Odds:** {parlay['combined_odds']}")
    lines.append(f"📊 **Implied Probability:** {parlay['implied_probability']}")
    lines.append(f"💵 **$100 Payout:** {parlay['payout_per_100']}")

    risk_emoji = "🟢" if parlay["risk"] == "Medium" else "🟡" if parlay["risk"] == "High" else "🔴"
    lines.append(f"⚠️ **Risk:** {risk_emoji} {parlay['risk']}")
    lines.append("\n_This is not financial advice._")

    return {"intent": "parlay", "response": "\n".join(lines), "data": parlay}


async def _handle_best_bets(db: AsyncSession) -> dict:
    """Generate the best bets across all fights on the card."""
    analyses = await _analyze_all_fights(db)
    if not analyses:
        return {"intent": "build_bet", "response": "Couldn't analyze fights.", "data": None}

    all_betting = [a["betting"] for a in analyses if a.get("betting")]
    ranked_bets = build_best_bets_card(all_betting)

    lines = [
        "🔥 **Best Bets — UFC 327**\n",
        "---\n",
    ]

    # Top picks (max 5)
    for i, bet in enumerate(ranked_bets[:5], 1):
        risk_emoji = "🟢" if bet["risk"] == "Low" else "🟡" if bet["risk"] == "Medium" else "🔴"
        lines.append(f"**{i}.** {risk_emoji} **{bet['bet']}** ({bet['odds']})")
        lines.append(f"   {bet.get('fight', '')} — {bet['risk']} risk")
        lines.append(f"   _{bet['reasoning']}_\n")

    # Also suggest a parlay
    parlay = build_parlay(analyses, 3)
    lines.append("---\n")
    lines.append("🎰 **Quick 3-Leg Parlay:**")
    for leg in parlay["legs"]:
        lines.append(f"  • **{leg['fighter']}** ({leg['odds']})")
    lines.append(f"  💰 Combined: {parlay['combined_odds']} | Payout: {parlay['payout_per_100']} per $100")

    lines.append("\n_This is not financial advice._")

    return {"intent": "build_bet", "response": "\n".join(lines), "data": {"bets": ranked_bets, "parlay": parlay}}


# ── Main Chat Processor ──

async def process_chat(message: str, db: AsyncSession) -> dict:
    intent = classify_intent(message)
    fighters = find_fighters(message)

    # ─── Fight Card ───
    if intent == "fights":
        events = await fetch_events()
        text = _format_fight_card(events)
        return {"intent": intent, "response": text, "data": events}

    # ─── Parlay Builder ───
    if intent == "parlay":
        num_legs = 3
        leg_match = re.search(r"(\d+)\s*leg", message.lower())
        if leg_match:
            num_legs = min(int(leg_match.group(1)), 5)
        return await _handle_parlay(num_legs, db)

    # ─── Build Me a Bet / Best Bets ───
    if intent == "build_bet":
        if any(w in message.lower() for w in ["parlay", "multi", "combo", "leg"]):
            return await _handle_parlay(3, db)
        return await _handle_best_bets(db)

    # ─── Deep Analysis Mode ───
    if intent == "deep_analysis" and len(fighters) >= 2:
        a = await get_fighter_stats(fighters[0], db)
        b = await get_fighter_stats(fighters[1], db)
        if a and b:
            prediction = analyze_matchup(a, b)
            all_odds = await fetch_odds()
            fight_odds = _find_odds(fighters, all_odds)
            betting = analyze_betting(a, b, fight_odds, prediction)

            # Also search web for extra context
            web_info = await search_fight_info(fighters[0], fighters[1])
            text = _format_deep_analysis(a, b, prediction, betting, fight_odds)
            if web_info and web_info.get("snippets"):
                text += "\n\n📡 **Latest from the web:**\n"
                for snip in web_info["snippets"][:3]:
                    text += f"• _{snip}_\n"
            return {"intent": intent, "response": text, "data": {"prediction": prediction, "betting": betting}}

    # ─── Stats ───
    if intent == "stats" and fighters:
        if len(fighters) >= 2:
            comp = await compare_fighters(fighters[0], fighters[1], db)
            a, b = comp.get("fighter_a"), comp.get("fighter_b")
            if a and b:
                text = (
                    f"📊 **{a['name']} vs {b['name']}**\n\n"
                    f"| Stat | {a['name'].split()[-1]} | {b['name'].split()[-1]} |\n"
                    f"|---|---|---|\n"
                    f"| Record | {a['wins']}-{a['losses']} | {b['wins']}-{b['losses']} |\n"
                    f"| Strikes/Min | {a['strikes_per_min']} | {b['strikes_per_min']} |\n"
                    f"| Str. Accuracy | {a['strike_accuracy']}% | {b['strike_accuracy']}% |\n"
                    f"| Takedowns | {a['takedowns_avg']}/15m | {b['takedowns_avg']}/15m |\n"
                    f"| TD Defense | {a['td_defense']}% | {b['td_defense']}% |\n"
                    f"| Submissions | {a['submission_avg']}/15m | {b['submission_avg']}/15m |\n"
                    f"| Win Streak | {a['win_streak']} | {b['win_streak']} |"
                )
                return {"intent": intent, "response": text, "data": comp}
            found = a or b
            missing = fighters[1] if a else fighters[0]
            if found:
                text = f"Found **{found['name']}** but couldn't find **{missing}**.\n\n" + _format_stats(found)
                return {"intent": intent, "response": text, "data": comp}
        else:
            stats = await get_fighter_stats(fighters[0], db)
            if stats:
                return {"intent": intent, "response": _format_stats(stats), "data": stats}
            else:
                text = f"Couldn't find stats for **{fighters[0]}** — searched database and web.\n\nTry someone on the current card: Prochazka, Ulberg, Costa, Blaydes, etc."
                return {"intent": intent, "response": text, "data": None}

    # ─── Prediction ───
    if intent == "prediction" and len(fighters) >= 2:
        a = await get_fighter_stats(fighters[0], db)
        b = await get_fighter_stats(fighters[1], db)
        if a and b:
            prediction = analyze_matchup(a, b)
            conf = prediction["confidence"]
            emoji = "🟢" if conf > 65 else "🟡" if conf > 55 else "🔴"
            text = (
                f"⚔️ **{a['name']} vs {b['name']}**\n\n"
                f"{emoji} **{prediction['predicted_winner']}** by {prediction['method']} "
                f"({conf}% confidence)\n\n"
                "Key factors:\n" +
                "\n".join(f"• {f}" for f in prediction["factors"])
            )
            return {"intent": intent, "response": text, "data": prediction}

    # ─── Betting ───
    if intent == "betting":
        if len(fighters) >= 2:
            a = await get_fighter_stats(fighters[0], db)
            b = await get_fighter_stats(fighters[1], db)
            if a and b:
                prediction = analyze_matchup(a, b)
                all_odds = await fetch_odds()
                fight_odds = _find_odds(fighters, all_odds)
                betting = analyze_betting(a, b, fight_odds, prediction)
                text = f"💰 **Betting Analysis: {a['name']} vs {b['name']}**\n\n"
                if fight_odds:
                    text += (
                        f"**Current Lines:**\n"
                        f"  {fight_odds['fighter_a']}: {'+' if fight_odds['fighter_a_odds'] > 0 else ''}{fight_odds['fighter_a_odds']} ({fight_odds['fighter_a_prob']}%)\n"
                        f"  {fight_odds['fighter_b']}: {'+' if fight_odds['fighter_b_odds'] > 0 else ''}{fight_odds['fighter_b_odds']} ({fight_odds['fighter_b_prob']}%)\n\n"
                    )
                for bet in betting["all_bets"]:
                    risk_emoji = "🟢" if bet["risk"] == "Low" else "🟡" if bet["risk"] == "Medium" else "🔴"
                    text += f"• {risk_emoji} **{bet['bet']}** ({bet['odds']}) — {bet['risk']} risk\n  _{bet['reasoning']}_\n\n"
                text += "_This is not financial advice._"
                return {"intent": intent, "response": text, "data": betting}
        else:
            # Show all odds
            all_odds = await fetch_odds()
            text = "💰 **Tonight's Lines**\n\n"
            for o in all_odds:
                text += (
                    f"**{o['fight']}**\n"
                    f"  {o['fighter_a']}: {'+' if o['fighter_a_odds'] > 0 else ''}{o['fighter_a_odds']} ({o['fighter_a_prob']}%)\n"
                    f"  {o['fighter_b']}: {'+' if o['fighter_b_odds'] > 0 else ''}{o['fighter_b_odds']} ({o['fighter_b_prob']}%)\n\n"
                )
            return {"intent": intent, "response": text, "data": all_odds}

    # ─── Live / Latest (Web Search) ───
    if intent == "live":
        if fighters:
            web_stats = await search_fighter_stats(fighters[0])
            web_info = await search_fight_info(fighters[0], fighters[1] if len(fighters) > 1 else "UFC")
            if web_stats or web_info:
                text = f"📡 **Latest on {fighters[0]}**\n\n"
                if web_stats:
                    text += _format_stats(web_stats) + "\n\n"
                if web_info and web_info.get("snippets"):
                    text += "**From the web:**\n"
                    for snip in web_info["snippets"][:4]:
                        text += f"• _{snip}_\n"
                return {"intent": intent, "response": text, "data": web_stats}
        # General live search
        events = await fetch_events()
        text = "📡 **Latest UFC Updates**\n\n" + _format_fight_card(events)
        return {"intent": intent, "response": text, "data": events}

    # ─── General Chat / Fighter Detected ───
    if fighters:
        stats = await get_fighter_stats(fighters[0], db)
        if stats:
            text = _format_stats(stats)
            text += f"\n\nWant more? Try:\n• \"break down {stats['name'].split()[-1]} vs [opponent]\"\n• \"best bets {stats['name'].split()[-1]} vs [opponent]\""
            return {"intent": "chat", "response": text, "data": stats}
        else:
            # Try web search as last resort
            web = await search_fighter_stats(fighters[0])
            if web:
                text = _format_stats(web)
                return {"intent": "chat", "response": text, "data": web}
            text = f"Hmm, couldn't find **{fighters[0]}** in our database or on the web.\n\nTry a fighter on the UFC 327 card — like Prochazka, Ulberg, Costa, or Blaydes."
            return {"intent": "chat", "response": text, "data": None}

    # ─── Default Welcome ───
    events = await fetch_events()
    text = (
        "Hey! I'm **FightIQ AI** 🥊 — your UFC analyst, stats guru, and betting brain.\n\n"
        + _format_fight_card(events) + "\n\n"
        "What do you want to know? Try:\n"
        "• \"Break down Prochazka vs Ulberg\"\n"
        "• \"Stats for Costa\"\n"
        "• \"Best bets tonight\"\n"
        "• \"Who wins Blaydes vs Hokit?\""
    )
    return {"intent": "chat", "response": text, "data": None}


def _find_odds(fighters: list[str], all_odds: list[dict]) -> dict | None:
    for o in all_odds:
        fl = o["fight"].lower()
        for f in fighters:
            if f.split()[-1].lower() in fl:
                return o
    return None
