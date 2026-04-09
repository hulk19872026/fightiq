import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: API_BASE, timeout: 15000 })

export async function fetchEvents() {
  const { data } = await api.get('/events')
  return data.events || []
}

export async function fetchFighterStats(name) {
  const { data } = await api.get('/fighter-stats', { params: { name } })
  return data
}

export async function fetchAllFighters() {
  const { data } = await api.get('/fighter-stats/all')
  return data
}

export async function fetchOdds(fight = '') {
  const { data } = await api.get('/odds', { params: { fight } })
  return data.odds || []
}

export async function fetchAnalysis(fighterA, fighterB) {
  const { data } = await api.get('/fight-analysis', { params: { fighterA, fighterB } })
  return data
}

export async function sendChat(message) {
  const { data } = await api.post('/chat', { message })
  return data
}
