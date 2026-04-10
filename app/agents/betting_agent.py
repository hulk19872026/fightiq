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


# ── Elite Parlay Engine ──────────────────────────────────────────────


def _pick_edge(pick: dict) -> float:
    """Calculate edge: model confidence minus market implied probability."""
    conf = pick.get("confidence", 50)
    odds_val = pick.get("winner_odds", -150)
    market_prob = american_to_implied(odds_val)
    return conf - market_prob


def _pick_ev(pick: dict) -> float:
    """Expected value per $100 wagered."""
    conf = pick.get("confidence", 50) / 100.0
    odds_val = pick.get("winner_odds", -150)
    if odds_val > 0:
        payout = odds_val / 100.0
    else:
        payout = 100.0 / abs(odds_val)
    return round((conf * payout - (1 - conf)) * 100, 1)


def _style_tag(pick: dict) -> str:
    method = pick.get("method", "")
    if "KO" in method or "TKO" in method:
        return "Striker"
    if "Submission" in method:
        return "Grappler"
    return "Tactician"


def _select_legs(picks: list[dict], num_legs: int, *, sort_key: str) -> list[dict]:
    """Select num_legs unique-fight picks sorted by sort_key.

    sort_key: 'confidence' (safe), 'edge' (balanced), 'payout' (risky)
    """
    if sort_key == "edge":
        ordered = sorted(picks, key=lambda p: _pick_edge(p), reverse=True)
    elif sort_key == "payout":
        # Prefer underdogs (positive odds first, then by magnitude)
        ordered = sorted(picks, key=lambda p: p.get("winner_odds", -150), reverse=True)
    else:
        ordered = sorted(picks, key=lambda p: p["confidence"], reverse=True)

    legs = []
    used: set[str] = set()
    for pick in ordered:
        if len(legs) >= num_legs:
            break
        winner = pick["predicted_winner"]
        if winner.lower() in used:
            continue
        legs.append(pick)
        used.add(winner.lower())
        for key in ("fighter_a", "fighter_b"):
            if key in pick:
                used.add(pick[key].lower())
    return legs


def _build_single_parlay(legs: list[dict]) -> dict:
    """Compute combined odds, probability, EV, payout for a set of legs."""
    parlay_prob = 1.0
    for pick in legs:
        odds_val = pick.get("winner_odds", -150)
        implied = american_to_implied(odds_val) / 100.0
        parlay_prob *= implied

    if 0 < parlay_prob < 1:
        if parlay_prob > 0.5:
            combined_american = -round(parlay_prob / (1 - parlay_prob) * 100)
        else:
            combined_american = round((1 - parlay_prob) / parlay_prob * 100)
    else:
        combined_american = 100

    payout_100 = round(100 * (1 / parlay_prob - 1)) if parlay_prob > 0 else 0

    # AI win probability uses model confidence instead of market implied
    ai_prob = 1.0
    for pick in legs:
        ai_prob *= pick["confidence"] / 100.0

    # EV = (ai_win_prob * payout) - (ai_loss_prob * stake)
    ev_raw = ai_prob * payout_100 - (1 - ai_prob) * 100
    ev_label = "Positive" if ev_raw > 0 else "Negative"

    if ai_prob > 0.35:
        risk = "Low"
    elif ai_prob > 0.20:
        risk = "Medium"
    elif ai_prob > 0.10:
        risk = "High"
    else:
        risk = "Very High"

    formatted_legs = []
    for pick in legs:
        odds_val = pick.get("winner_odds", -150)
        formatted_legs.append({
            "fighter": pick["predicted_winner"],
            "method": pick["method"],
            "confidence": pick["confidence"],
            "odds": f"{'+' if odds_val > 0 else ''}{odds_val}",
            "edge": f"{'+' if _pick_edge(pick) > 0 else ''}{round(_pick_edge(pick))}%",
            "ev": _pick_ev(pick),
            "style": _style_tag(pick),
            "reasoning": pick.get("reasoning", ""),
            "fighter_a": pick.get("fighter_a", ""),
            "fighter_b": pick.get("fighter_b", ""),
        })

    return {
        "type": "parlay",
        "legs": formatted_legs,
        "num_legs": len(formatted_legs),
        "combined_odds": f"{'+' if combined_american > 0 else ''}{combined_american}",
        "implied_probability": f"{round(parlay_prob * 100)}%",
        "ai_win_probability": f"{round(ai_prob * 100)}%",
        "ev": f"{'+'  if ev_raw > 0 else ''}{round(ev_raw)}",
        "ev_label": ev_label,
        "payout_per_100": f"${payout_100}",
        "risk": risk,
    }


def build_parlay(picks: list[dict], num_legs: int = 3) -> dict:
    """Build a single parlay from picks, sorted by confidence."""
    legs = _select_legs(picks, num_legs, sort_key="confidence")
    return _build_single_parlay(legs)


def build_elite_parlays(picks: list[dict], num_legs: int = 3) -> dict:
    """Generate three parlay tiers: safe, balanced, risky."""
    safe_legs = _select_legs(picks, num_legs, sort_key="confidence")
    balanced_legs = _select_legs(picks, num_legs, sort_key="edge")
    risky_legs = _select_legs(picks, num_legs, sort_key="payout")

    return {
        "safe": _build_single_parlay(safe_legs),
        "balanced": _build_single_parlay(balanced_legs),
        "risky": _build_single_parlay(risky_legs),
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
