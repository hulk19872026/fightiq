import { Radar } from 'react-chartjs-2'
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler } from 'chart.js'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler)

export default function RadarChart({ a, b }) {
  const data = {
    labels: ['Striking', 'Wrestling', 'Submissions', 'Cardio', 'Defense'],
    datasets: [
      {
        label: a.name,
        data: [a.striking, a.wrestling, a.submission_avg * 30 + 10, a.cardio, a.defense],
        borderColor: '#ef5350',
        backgroundColor: 'rgba(239,83,80,0.12)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#ef5350',
      },
      {
        label: b.name,
        data: [b.striking, b.wrestling, b.submission_avg * 30 + 10, b.cardio, b.defense],
        borderColor: '#ffd600',
        backgroundColor: 'rgba(255,214,0,0.08)',
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: '#ffd600',
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: { display: false, stepSize: 20 },
        grid: { color: '#222' },
        angleLines: { color: '#222' },
        pointLabels: { color: '#888', font: { size: 8, weight: '600' } },
      },
    },
    plugins: { legend: { display: false } },
  }

  return (
    <div className="bg-dark-800 rounded-xl p-3.5 border border-dark-600">
      <p className="text-[11px] font-bold text-gray-500 mb-2 text-center uppercase tracking-wider">Skill Comparison</p>
      <div className="h-[140px] flex items-center justify-center">
        <Radar data={data} options={options} />
      </div>
    </div>
  )
}
