from app.services.odds_api import american_to_implied


def analyze_betting(fighter_a: dict, fighter_b: dict, odds: dict | None, prediction: dict) -> dict:
    best_bets = []

    a_name = fighter_a["name"]
    b_name = fighter_b["name"]
    winner = prediction["predicted_winner"]
    confidence = prediction["confidence"]
    method = prediction["method"]

    # Determine odds
    if odds:
        a_odds = odds.get("fighter_a_odds", 0)
        b_odds = odds.get("fighter_b_odds", 0)
        a_prob = odds.get("fighter_a_prob", 50)
        b_prob = odds.get("fighter_b_prob", 50)
    else:
        a_odds, b_odds = 100, -120
        a_prob, b_prob = 50, 55

    # Check for value
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

    # Method of victory bet
    if "Submission" in method and confidence > 55:
        best_bets.append({
            "bet": f"{winner} by {method}",
            "odds": "+450",
            "edge": "Value",
            "risk": "High",
            "reasoning": f"{winner}'s grappling advantage creates submission opportunities",
        })
    elif "KO" in method and confidence > 55:
        best_bets.append({
            "bet": f"{winner} by {method}",
            "odds": "+350",
            "edge": "Value",
            "risk": "High",
            "reasoning": f"{winner}'s striking power is the key differentiator",
        })

    # Round prop
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
