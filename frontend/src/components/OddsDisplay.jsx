export default function OddsDisplay({ odds }) {
  const aOdds = odds.fighter_a_odds
  const bOdds = odds.fighter_b_odds

  return (
    <div className="flex rounded-xl overflow-hidden mb-3 text-[13px] font-semibold border border-dark-500">
      <div className="flex-[36] bg-dark-600 px-3.5 py-3 flex justify-between items-center">
        <span className="text-gray-400">{odds.fighter_a?.split(' ').pop()}:</span>
        <span className="text-red-400">{aOdds > 0 ? '+' : ''}{aOdds} ({odds.fighter_a_prob}%)</span>
      </div>
      <div className="flex-[64] bg-[#0f2a0f] px-3.5 py-3 flex justify-between items-center text-brand-green">
        <span>{odds.fighter_b?.split(' ').pop()}</span>
        <span>{bOdds > 0 ? '+' : ''}{bOdds} ({odds.fighter_b_prob}%)</span>
      </div>
    </div>
  )
}
