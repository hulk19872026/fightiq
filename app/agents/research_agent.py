def analyze_matchup(fighter_a: dict, fighter_b: dict) -> dict:
    a = fighter_a
    b = fighter_b

    factors = []
    a_score = 0
    b_score = 0

    # Striking comparison
    if a["strikes_per_min"] > b["strikes_per_min"]:
        diff = a["strikes_per_min"] - b["strikes_per_min"]
        a_score += diff * 5
        factors.append(f"{a['name']} has higher output ({a['strikes_per_min']} vs {b['strikes_per_min']} SLpM)")
    else:
        diff = b["strikes_per_min"] - a["strikes_per_min"]
        b_score += diff * 5
        factors.append(f"{b['name']} has higher output ({b['strikes_per_min']} vs {a['strikes_per_min']} SLpM)")

    # Wrestling
    if a["takedowns_avg"] > b["takedowns_avg"] + 1:
        a_score += (a["takedowns_avg"] - b["takedowns_avg"]) * 6
        factors.append(f"{a['name']} has dominant wrestling ({a['takedowns_avg']} TD/15m)")
    elif b["takedowns_avg"] > a["takedowns_avg"] + 1:
        b_score += (b["takedowns_avg"] - a["takedowns_avg"]) * 6
        factors.append(f"{b['name']} has dominant wrestling ({b['takedowns_avg']} TD/15m)")

    # TD defense vs opponent wrestling
    if a["takedowns_avg"] > 2 and b["td_defense"] < 65:
        a_score += 10
        factors.append(f"{b['name']} has weak TD defense ({b['td_defense']}%) against {a['name']}'s wrestling")
    if b["takedowns_avg"] > 2 and a["td_defense"] < 65:
        b_score += 10
        factors.append(f"{a['name']} has weak TD defense ({a['td_defense']}%) against {b['name']}'s wrestling")

    # Submission threat
    if a["submission_avg"] > b["submission_avg"] + 1:
        a_score += 8
        factors.append(f"{a['name']} has elite submission game ({a['submission_avg']} sub attempts/15m)")
    elif b["submission_avg"] > a["submission_avg"] + 1:
        b_score += 8
        factors.append(f"{b['name']} has elite submission game ({b['submission_avg']} sub attempts/15m)")

    # Win streak momentum
    if a["win_streak"] > b["win_streak"] + 3:
        a_score += 5
        factors.append(f"{a['name']} has strong momentum ({a['win_streak']} win streak)")
    elif b["win_streak"] > a["win_streak"] + 3:
        b_score += 5
        factors.append(f"{b['name']} has strong momentum ({b['win_streak']} win streak)")

    # Determine method prediction
    winner = a if a_score >= b_score else b
    loser = b if a_score >= b_score else a

    if winner["takedowns_avg"] > 3 and loser["td_defense"] < 65:
        method = "Decision (wrestling control)"
    elif winner["submission_avg"] > 2:
        method = "Submission"
    elif winner["strikes_per_min"] > 5:
        method = "KO/TKO"
    else:
        method = "Decision"

    total = a_score + b_score
    confidence = round(max(a_score, b_score) / total * 100) if total > 0 else 50

    return {
        "predicted_winner": winner["name"],
        "method": method,
        "confidence": min(confidence, 85),
        "factors": factors,
        "a_score": round(a_score, 1),
        "b_score": round(b_score, 1),
    }
