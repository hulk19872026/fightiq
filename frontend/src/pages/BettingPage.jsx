import { useState, useEffect } from 'react'
import { fetchOdds, fetchAnalysis } from '../api/client'

const FIGHTS = [
  ['Charles Oliveira', 'Islam Makhachev'],
  ['Justin Gaethje', 'Max Holloway'],
  ['Petr Yan', 'Deiveson Figueiredo'],
  ['Alex Pereira', 'Jamahal Hill'],
]

export default function BettingPage() {
  const [odds, setOdds] = useState([])
  const [analyses, setAnalyses] = useState([])
  const [selected, setSelected] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetchOdds(),
      ...FIGHTS.map(([a, b]) => fetchAnalysis(a, b).catch(() => null)),
    ])
      .then(([od, ...anl]) => {
        setOdds(od)
        setAnalyses(anl.filter(Boolean))
      })
      .finally(() => setLoading(false))
  }, [])

  function toggleSelect(group, idx) {
    setSelected(s => ({ ...s, [group]: s[group] === idx ? null : idx }))
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-brand-red border-t-transparent rounded-full animate-spin" /></div>
  }

  return (
    <div>
      <h1 className="text-[22px] font-extrabold px-4 pt-5 pb-1">Betting Lines</h1>
      <p className="text-[13px] text-gray-500 px-4 pb-4">UFC 300 – Best Picks</p>

      {/* AI Best Bets */}
      {analyses.length > 0 && (
        <div className="mx-4 mb-3.5 bg-dark-700 rounded-2xl border border-dark-500 p-4">
          <h2 className="text-[15px] font-bold mb-1">🎯 AI Best Bets</h2>
          <p className="text-[12px] text-gray-600 mb-3.5">Top value picks from FightIQ analysis</p>
          {analyses.map((a, i) => {
            const bet = a.betting?.best_bet
            if (!bet) return null
            return (
              <div key={i} className="bg-dark-800 rounded-xl p-3.5 border border-dark-600 mb-2.5 flex justify-between items-center">
                <div>
                  <p className="text-[13px] font-semibold">{bet.bet}</p>
                  <p className="text-[11px] text-gray-500 mt-1">{bet.reasoning}</p>
                </div>
                <div className="text-right ml-3 shrink-0">
                  <p className="text-sm font-bold text-brand-green">{bet.odds}</p>
                  <p className={`text-[10px] font-semibold ${bet.risk === 'Low' ? 'text-brand-green' : bet.risk === 'Medium' ? 'text-brand-yellow' : 'text-brand-red'}`}>{bet.risk} Risk</p>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Odds Cards */}
      {odds.map((o, i) => (
        <div key={i} className="mx-4 mb-3 bg-dark-700 rounded-2xl border border-dark-500 p-4">
          <h3 className="text-[15px] font-bold mb-1">{o.fight}</h3>
          <p className="text-[12px] text-gray-600 mb-3">Moneyline</p>
          <div
            onClick={() => toggleSelect(`ml-${i}`, 0)}
            className={`flex justify-between items-center bg-dark-800 rounded-xl p-3.5 border mb-2 cursor-pointer transition-all active:scale-[0.98] ${selected[`ml-${i}`] === 0 ? 'border-brand-green bg-[#0a1f0a]' : 'border-dark-600 hover:border-dark-500'}`}
          >
            <span className="text-sm font-semibold">{o.fighter_a}</span>
            <span className="text-sm font-bold text-brand-green">{o.fighter_a_odds > 0 ? '+' : ''}{o.fighter_a_odds} ({o.fighter_a_prob}%)</span>
          </div>
          <div
            onClick={() => toggleSelect(`ml-${i}`, 1)}
            className={`flex justify-between items-center bg-dark-800 rounded-xl p-3.5 border cursor-pointer transition-all active:scale-[0.98] ${selected[`ml-${i}`] === 1 ? 'border-brand-green bg-[#0a1f0a]' : 'border-dark-600 hover:border-dark-500'}`}
          >
            <span className="text-sm font-semibold">{o.fighter_b}</span>
            <span className="text-sm font-bold text-brand-green">{o.fighter_b_odds > 0 ? '+' : ''}{o.fighter_b_odds} ({o.fighter_b_prob}%)</span>
          </div>
        </div>
      ))}
    </div>
  )
}
