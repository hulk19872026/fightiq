from app.services.odds_api import american_to_implied


def analyze_betting(fighter_a: dict, fighter_b: dict, odds: dict | None, prediction: dict) -> dict:
    best_bets = []

    a_name = fighter_a["name"]
    b_name = fighter_b["name"]
    winner = prediction["predicted_winner"]
    confidence = prediction["confidence"]
    method = prediction["method"]

    if odds:
        a_odds = odds.get("fighter_a_odds", 0)
        b_odds = odds.get("fighter_b_odds", 0)
        a_prob = odds.get("fighter_a_prob", 50)
        b_prob = odds.get("fighter_b_prob", 50)
    else:
        a_odds, b_odds = 100, -120
        a_prob, b_prob = 50, 55

    model_winner_prob = confidence
    if winner == a_name:
        market_prob = a_prob
        winner_odds = a_odds
    else:
        market_prob = b_prob
        winner_odds = b_odds

    edge = model_winner_prob - market_prob

    if edge > 5:
        risk = "Low" if edge > 15 else "Medium" if edge > 8 else "High"
        best_bets.append({
            "bet": f"{winner} Moneyline",
            "odds": f"{'+' if winner_odds > 0 else ''}{winner_odds}",
            "edge": f"+{round(edge)}%",
            "risk": risk,
            "reasoning": f"Model gives {winner} {model_winner_prob}% vs market {market_prob}%",
        })

    if "Submission" in method and confidence > 55:
        best_bets.append({
            "bet": f"{winner} by Submission",
            "odds": "+450",
            "edge": "Value",
            "risk": "High",
            "reasoning": f"{winner}'s grappling advantage creates submission opportunities",
        })
    elif "KO" in method and confidence > 55:
        best_bets.append({
            "bet": f"{winner} by KO/TKO",
            "odds": "+350",
            "edge": "Value",
            "risk": "High",
            "reasoning": f"{winner}'s striking power is the key differentiator",
        })

    grappler = fighter_a["takedowns_avg"] > 3 or fighter_b["takedowns_avg"] > 3
    if grappler and "Decision" in method:
        best_bets.append({
            "bet": "Over 2.5 Rounds",
            "odds": "-150",
            "edge": "Likely",
            "risk": "Low",
            "reasoning": "Wrestling-heavy fights tend to go the distance",
        })

    if not best_bets:
        best_bets.append({
            "bet": f"{winner} Moneyline",
            "odds": f"{'+' if winner_odds > 0 else ''}{winner_odds}",
            "edge": "Slight",
            "risk": "Medium",
            "reasoning": f"Model favors {winner} at {confidence}% confidence",
        })

    return {
        "fighter_a": a_name,
        "fighter_b": b_name,
        "best_bet": best_bets[0] if best_bets else None,
        "all_bets": best_bets,
        "odds": {
            "fighter_a": {"name": a_name, "odds": a_odds, "implied_prob": a_prob},
            "fighter_b": {"name": b_name, "odds": b_odds, "implied_prob": b_prob},
        },
    }


def build_parlay(picks: list[dict], num_legs: int = 3) -> dict:
    """Build a parlay from a list of analyzed fight picks, sorted by confidence.

    Deduplicates by fighter so each leg is a different fight.
    """
    sorted_picks = sorted(picks, key=lambda p: p["confidence"], reverse=True)

    legs = []
    used_fighters: set[str] = set()
    parlay_prob = 1.0
    combined_american = 100

    for pick in sorted_picks:
        if len(legs) >= num_legs:
            break

        winner = pick["predicted_winner"]
        # Skip if this fighter is already in the parlay
        if winner.lower() in used_fighters:
            continue

        conf = pick["confidence"]
        method = pick["method"]
        odds_val = pick.get("winner_odds", -150)

        leg = {
            "fighter": winner,
            "method": method,
            "confidence": conf,
            "odds": f"{'+' if odds_val > 0 else ''}{odds_val}",
            "reasoning": pick.get("reasoning", ""),
        }
        legs.append(leg)
        used_fighters.add(winner.lower())
        # Also mark the opponent so we don't pick the same fight twice
        for key in ("fighter_a", "fighter_b"):
            if key in pick:
                used_fighters.add(pick[key].lower())

        implied = american_to_implied(odds_val) / 100.0
        parlay_prob *= implied

    # Calculate parlay odds from combined probability
    if parlay_prob > 0 and parlay_prob < 1:
        if parlay_prob > 0.5:
            combined_american = -round(parlay_prob / (1 - parlay_prob) * 100)
        else:
            combined_american = round((1 - parlay_prob) / parlay_prob * 100)

    # Risk assessment
    if parlay_prob > 0.35:
        risk = "Medium"
    elif parlay_prob > 0.20:
        risk = "High"
    else:
        risk = "Very High"

    payout_100 = round(100 * (1 / parlay_prob - 1)) if parlay_prob > 0 else 0

    return {
        "type": "parlay",
        "legs": legs,
        "num_legs": len(legs),
        "combined_odds": f"{'+' if combined_american > 0 else ''}{combined_american}",
        "implied_probability": f"{round(parlay_prob * 100)}%",
        "payout_per_100": f"${payout_100}",
        "risk": risk,
    }


def build_best_bets_card(all_analyses: list[dict]) -> list[dict]:
    """Build a ranked list of the best individual bets across all fights."""
    bets = []
    for analysis in all_analyses:
        for bet in analysis.get("all_bets", []):
            bet_entry = {**bet, "fight": f"{analysis['fighter_a']} vs {analysis['fighter_b']}"}
            bets.append(bet_entry)

    # Sort: Low risk first, then by edge
    risk_order = {"Low": 0, "Medium": 1, "High": 2}
    bets.sort(key=lambda b: (risk_order.get(b["risk"], 3), b.get("edge", "")))
    return bets
