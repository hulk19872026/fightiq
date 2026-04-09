import { useState, useEffect } from 'react'
import { fetchAnalysis } from '../api/client'
import FighterCompare from '../components/FighterCompare'
import RadarChart from '../components/RadarChart'
import StatBars from '../components/StatBars'

export default function StatsPage({ fight }) {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('stats')
  const [loading, setLoading] = useState(true)

  const fighterA = fight?.fighter_a || 'Charles Oliveira'
  const fighterB = fight?.fighter_b || 'Islam Makhachev'

  useEffect(() => {
    setLoading(true)
    fetchAnalysis(fighterA, fighterB)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [fighterA, fighterB])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-brand-red border-t-transparent rounded-full animate-spin" /></div>
  }

  if (!data || data.error) {
    return <div className="p-6 text-center text-gray-500">Could not load fighter data.</div>
  }

  const a = data.fighters?.fighter_a
  const b = data.fighters?.fighter_b
  const pred = data.prediction
  const betting = data.betting

  return (
    <div>
      {/* Fighter Breakdown Card */}
      <div className="mx-4 mt-3.5 bg-dark-700 rounded-2xl border border-dark-500 overflow-hidden">
        <div className="px-4 pt-4 pb-2">
          <h2 className="text-[19px] font-bold">Fighter Breakdown</h2>
        </div>
        <div className="flex items-center justify-between px-4 pb-3">
          <p className="text-sm text-gray-400">
            <span className="text-white font-bold">{a?.name?.split(' ')[0]}</span> vs <span className="text-white font-bold">{b?.name?.split(' ')[0]}</span>{' '}
            <span className="text-gray-600">{b?.name?.split(' ').slice(1).join(' ')}</span>
          </p>
          <div className="flex">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-dark-600 to-dark-800 border-2 border-dark-500 flex items-center justify-center text-xl">🥊</div>
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-dark-600 to-dark-800 border-2 border-dark-500 flex items-center justify-center text-xl -ml-3">🥊</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex mx-4 mb-3.5 bg-dark-800 rounded-xl p-1 gap-1">
          {['stats', 'analysis', 'betting'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 text-center py-2.5 text-[13px] font-semibold rounded-lg transition-all capitalize ${tab === t ? 'bg-brand-red text-white' : 'text-gray-600 hover:text-gray-400'}`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Stats Tab */}
        {tab === 'stats' && a && b && (
          <div className="grid grid-cols-2 gap-3 px-4 pb-4">
            <StatBars a={a} b={b} />
            <RadarChart a={a} b={b} />
          </div>
        )}

        {/* Analysis Tab */}
        {tab === 'analysis' && pred && (
          <div className="px-4 pb-4 space-y-3">
            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
              <h3 className="text-sm font-bold text-gray-300 mb-2">🎯 AI Prediction</h3>
              <p className="text-sm text-gray-400 leading-relaxed">
                <span className="text-white font-bold">{pred.predicted_winner}</span> by {pred.method} ({pred.confidence}% confidence)
              </p>
            </div>
            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
              <h3 className="text-sm font-bold text-gray-300 mb-2">📊 Key Factors</h3>
              <ul className="space-y-1.5">
                {(pred.factors || []).map((f, i) => (
                  <li key={i} className="text-[13px] text-gray-400 leading-relaxed">• {f}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Betting Tab */}
        {tab === 'betting' && betting && (
          <div className="px-4 pb-4 space-y-2.5">
            {(betting.all_bets || []).map((bet, i) => (
              <div key={i} className="bg-dark-800 rounded-xl p-3.5 border border-dark-600 flex justify-between items-center cursor-pointer hover:border-brand-red transition-colors active:scale-[0.98]">
                <div>
                  <p className="text-[13px] font-semibold">{bet.bet}</p>
                  <p className="text-[11px] text-gray-500 mt-1">{bet.reasoning}</p>
                </div>
                <div className="text-right ml-3">
                  <p className="text-sm font-bold text-brand-green">{bet.odds}</p>
                  <p className="text-[10px] text-gray-500">{bet.risk}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Head to Head Stats */}
      {a && b && (
        <div className="mx-4 mt-3.5 bg-dark-700 rounded-2xl border border-dark-500 overflow-hidden">
          <FighterCompare a={a} b={b} />
        </div>
      )}
    </div>
  )
}
