export default function StatBars({ a, b }) {
  const maxSpm = Math.max(a.strikes_per_min, b.strikes_per_min, 1)
  const aH = Math.round((a.strikes_per_min / maxSpm) * 80)
  const bH = Math.round((b.strikes_per_min / maxSpm) * 80)

  return (
    <div className="bg-dark-800 rounded-xl p-3.5 border border-dark-600">
      <p className="text-[11px] font-bold text-gray-500 mb-3 text-center uppercase tracking-wider">Strikes Per Minute</p>
      <div className="flex items-end justify-center gap-6 h-[110px] pt-1">
        <div className="flex flex-col items-center gap-1">
          <span className="text-lg font-extrabold text-red-400">{a.strikes_per_min}</span>
          <div className="w-11 rounded-t-md bg-gradient-to-t from-red-900 to-red-400" style={{ height: `${aH}px` }} />
          <span className="text-[11px] font-bold text-red-400 mt-1.5">{a.name?.split(' ').pop()}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <span className="text-lg font-extrabold text-yellow-400">{b.strikes_per_min}</span>
          <div className="w-11 rounded-t-md bg-gradient-to-t from-yellow-900 to-yellow-400" style={{ height: `${bH}px` }} />
          <span className="text-[11px] font-bold text-yellow-400 mt-1.5">{b.name?.split(' ').pop()}</span>
        </div>
      </div>
    </div>
  )
}
