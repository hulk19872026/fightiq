import { useState, useEffect } from 'react'
import { fetchEvents, fetchOdds } from '../api/client'
import FightCard from '../components/FightCard'
import OddsDisplay from '../components/OddsDisplay'

export default function FightsPage({ onSelectFight }) {
  const [events, setEvents] = useState([])
  const [odds, setOdds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([fetchEvents(), fetchOdds()])
      .then(([ev, od]) => { setEvents(ev); setOdds(od) })
      .catch((e) => { setError(e.message || 'Failed to load'); console.error(e) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="w-8 h-8 border-2 border-brand-red border-t-transparent rounded-full animate-spin" /></div>
  }

  if (error) {
    return <div className="p-6 text-center text-gray-500">Failed to load events. Pull to refresh.</div>
  }

  return (
    <div>
      {events.map((ev, i) => (
        <div key={i} className="mx-4 mt-3.5 bg-dark-700 rounded-2xl border border-dark-500 p-4">
          <h2 className="text-[17px] font-bold">🔥 {ev.name}</h2>
          <p className="text-[13px] text-gray-500 mt-1">{ev.date || 'TBD'} – {ev.location || 'TBD'}</p>
          <div className="mt-4 flex flex-col gap-3">
            {(ev.fights || []).map((f, j) => (
              <FightCard
                key={j}
                fight={f}
                onClick={() => onSelectFight(f)}
              />
            ))}
          </div>
        </div>
      ))}

      {odds.length > 0 && (
        <div className="mx-4 mt-3.5 bg-dark-700 rounded-2xl border border-dark-500 p-4">
          <h2 className="text-[19px] font-bold mb-3.5">Odds & Picks</h2>
          <p className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">🏈 Current Odds</p>
          {odds.map((o, i) => (
            <OddsDisplay key={i} odds={o} />
          ))}
        </div>
      )}
    </div>
  )
}
