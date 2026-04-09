export default function FightCard({ fight, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-2.5 text-sm cursor-pointer hover:bg-dark-600/50 rounded-lg p-2 -mx-2 transition-colors active:scale-[0.98]"
    >
      <span className="text-base w-5 text-center">🥊</span>
      <div>
        <span className="font-bold text-gray-300">{fight.is_main_event ? 'Main Event: ' : ''}</span>
        <span>{fight.fighter_a} vs {fight.fighter_b}</span>
        {fight.weight_class && <span className="text-gray-600 text-xs ml-2">{fight.weight_class}</span>}
      </div>
    </div>
  )
}
