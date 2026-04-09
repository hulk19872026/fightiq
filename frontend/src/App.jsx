import { useState } from 'react'
import FightsPage from './pages/FightsPage'
import StatsPage from './pages/StatsPage'
import BettingPage from './pages/BettingPage'
import ChatPage from './pages/ChatPage'

const TABS = [
  { id: 'fights', label: 'Fights', icon: '🥊' },
  { id: 'stats', label: 'Stats', icon: '📊' },
  { id: 'betting', label: 'Betting', icon: '🏆' },
  { id: 'chat', label: 'Chat', icon: '💬' },
]

export default function App() {
  const [page, setPage] = useState('fights')
  const [selectedFight, setSelectedFight] = useState(null)

  return (
    <div className="max-w-[480px] mx-auto min-h-screen pb-24">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-[#0a0a0a] border-b-[3px] border-brand-red flex items-center justify-between px-5 py-3.5">
        <span className="text-2xl cursor-pointer">☰</span>
        <span className="text-2xl font-extrabold italic tracking-wide">FightIQ</span>
        <span className="text-2xl cursor-pointer">🔔</span>
      </header>

      {/* Pages */}
      <main>
        {page === 'fights' && <FightsPage onSelectFight={(f) => { setSelectedFight(f); setPage('stats') }} />}
        {page === 'stats' && <StatsPage fight={selectedFight} />}
        {page === 'betting' && <BettingPage />}
        {page === 'chat' && <ChatPage />}
      </main>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[480px] bg-[#0f0f0f] border-t border-dark-500 flex items-center px-3 pb-2.5 pt-1.5 z-50">
        <div className="flex flex-1 justify-around">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setPage(t.id)}
              className={`flex flex-col items-center gap-1 py-2 px-3 rounded-xl transition-colors ${page === t.id ? 'text-brand-red' : 'text-gray-600'}`}
            >
              <span className="text-xl">{t.icon}</span>
              <span className="text-[10px] font-semibold">{t.label}</span>
            </button>
          ))}
        </div>
        <button className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-700 to-blue-400 flex items-center justify-center text-xl shadow-lg shadow-blue-500/30 ml-1 active:scale-95 transition-transform">
          🎤
        </button>
      </nav>
    </div>
  )
}
