const STATS = [
  { label: 'Strikes Per Min', key: 'strikes_per_min' },
  { label: 'Str. Accuracy', key: 'strike_accuracy', suffix: '%' },
  { label: 'Takedowns / 15m', key: 'takedowns_avg' },
  { label: 'TD Defense', key: 'td_defense', suffix: '%' },
  { label: 'Sub Avg / 15m', key: 'submission_avg' },
  { label: 'Win Streak', key: 'win_streak' },
]

export default function FighterCompare({ a, b }) {
  return (
    <div>
      <div className="px-4 pt-4 pb-2 flex justify-between items-center">
        <h3 className="text-[15px] font-bold">Head to Head</h3>
        <div className="flex gap-4 text-[10px] font-bold text-gray-500">
          <span className="text-red-400">{a.name?.split(' ').pop()}</span>
          <span className="text-yellow-400">{b.name?.split(' ').pop()}</span>
        </div>
      </div>
      {STATS.map((s, i) => {
        const av = a[s.key] ?? 0
        const bv = b[s.key] ?? 0
        const suf = s.suffix || ''
        return (
          <div key={i} className={`flex justify-between items-center px-4 py-3 ${i < STATS.length - 1 ? 'border-b border-dark-800' : ''}`}>
            <span className="text-sm text-gray-500">{s.label}</span>
            <div className="flex gap-6">
              <div className="text-center">
                <div className={`text-base font-bold ${av >= bv ? 'text-red-400' : 'text-gray-500'}`}>{av}{suf}</div>
              </div>
              <div className="text-center">
                <div className={`text-base font-bold ${bv >= av ? 'text-yellow-400' : 'text-gray-500'}`}>{bv}{suf}</div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
