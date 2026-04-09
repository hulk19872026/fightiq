import { useState, useRef, useEffect } from 'react'
import { sendChat } from '../api/client'

// Simple markdown renderer for bold, italic, tables, bullets
function renderMarkdown(text) {
  const lines = text.split('\n')
  const elements = []
  let tableRows = []
  let inTable = false

  function flushTable() {
    if (tableRows.length > 0) {
      const headerCells = tableRows[0]
      const bodyRows = tableRows.slice(1).filter(r => !r.every(c => /^[-|]+$/.test(c.trim())))
      elements.push(
        <div key={`t-${elements.length}`} className="overflow-x-auto my-2">
          <table className="text-xs w-full border-collapse">
            <thead>
              <tr className="border-b border-dark-500">
                {headerCells.map((c, i) => <th key={i} className="py-1.5 px-2 text-left text-gray-400 font-semibold">{formatInline(c.trim())}</th>)}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, ri) => (
                <tr key={ri} className="border-b border-dark-600/50">
                  {row.map((c, ci) => <td key={ci} className="py-1 px-2 text-gray-300">{formatInline(c.trim())}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
      tableRows = []
    }
    inTable = false
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // Table detection
    if (line.includes('|') && line.trim().startsWith('|')) {
      const cells = line.split('|').filter(c => c.trim() !== '')
      if (cells.length >= 2) {
        // Skip separator rows but keep them in for flushing logic
        if (cells.every(c => /^[\s-:]+$/.test(c))) {
          tableRows.push(cells)
          inTable = true
          continue
        }
        tableRows.push(cells)
        inTable = true
        continue
      }
    }

    if (inTable) flushTable()

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={`hr-${i}`} className="border-dark-500 my-2" />)
      continue
    }

    // Empty line
    if (!line.trim()) {
      elements.push(<div key={`br-${i}`} className="h-1.5" />)
      continue
    }

    // Bullet points
    if (/^\s*[•\-\*]\s/.test(line)) {
      const content = line.replace(/^\s*[•\-\*]\s/, '')
      elements.push(
        <div key={`li-${i}`} className="flex gap-1.5 ml-1">
          <span className="text-gray-500 shrink-0">•</span>
          <span>{formatInline(content)}</span>
        </div>
      )
      continue
    }

    // Regular line
    elements.push(<div key={`p-${i}`}>{formatInline(line)}</div>)
  }

  if (inTable) flushTable()
  return elements
}

function formatInline(text) {
  // Process bold, italic, inline code
  const parts = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // Bold **text** or __text__
    const boldMatch = remaining.match(/\*\*(.+?)\*\*|__(.+?)__/)
    // Italic _text_ or *text*
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)/)

    let firstMatch = null
    let matchType = null

    if (boldMatch && (!italicMatch || boldMatch.index <= italicMatch.index)) {
      firstMatch = boldMatch
      matchType = 'bold'
    } else if (italicMatch) {
      firstMatch = italicMatch
      matchType = 'italic'
    }

    if (!firstMatch) {
      parts.push(<span key={key++}>{remaining}</span>)
      break
    }

    if (firstMatch.index > 0) {
      parts.push(<span key={key++}>{remaining.substring(0, firstMatch.index)}</span>)
    }

    const content = firstMatch[1] || firstMatch[2]
    if (matchType === 'bold') {
      parts.push(<strong key={key++} className="text-white font-bold">{content}</strong>)
    } else {
      parts.push(<em key={key++} className="text-gray-400 italic">{content}</em>)
    }

    remaining = remaining.substring(firstMatch.index + firstMatch[0].length)
  }

  return parts
}

const SUGGESTIONS = [
  'Break down Prochazka vs Ulberg',
  'Best bets tonight',
  'Stats for Costa',
  'Who wins Blaydes vs Hokit?',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hey! I\'m **FightIQ AI** 🥊\n\nYour UFC analyst, stats guru, and betting brain.\n\nAsk me anything about **UFC 327**, fighter stats, predictions, or betting.' },
  ])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typing])

  async function send(msg) {
    const text = (msg || input).trim()
    if (!text) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text }])
    setTyping(true)

    try {
      const res = await sendChat(text)
      setMessages(m => [...m, { role: 'bot', text: res.response || 'No response.' }])
    } catch {
      setMessages(m => [...m, { role: 'bot', text: 'Something went wrong — try again in a sec.' }])
    } finally {
      setTyping(false)
    }
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 140px)' }}>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[88%] px-4 py-3 rounded-2xl text-[13px] leading-relaxed ${
              m.role === 'bot'
                ? 'self-start bg-dark-700 rounded-bl-sm text-gray-300'
                : 'self-end bg-brand-red rounded-br-sm text-white ml-auto'
            }`}
          >
            {m.role === 'bot' ? renderMarkdown(m.text) : m.text}
          </div>
        ))}

        {/* Quick suggestions after first message */}
        {messages.length === 1 && !typing && (
          <div className="flex flex-wrap gap-2 mt-2">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => send(s)}
                className="text-xs px-3 py-1.5 rounded-full bg-dark-600 border border-dark-500 text-gray-400 hover:text-white hover:border-brand-red transition-all active:scale-95"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {typing && (
          <div className="self-start bg-dark-700 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%]">
            <div className="flex gap-1.5 items-center">
              <span className="text-xs text-gray-500 mr-2">Analyzing</span>
              <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="flex gap-2.5 px-4 py-3 bg-dark-800 border-t border-dark-500">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Ask about a fight, stats, or bets..."
          className="flex-1 bg-dark-700 border border-dark-500 rounded-3xl px-5 py-3 text-sm text-white outline-none focus:border-brand-red placeholder:text-gray-600"
        />
        <button onClick={() => send()} className="w-11 h-11 rounded-full bg-brand-red flex items-center justify-center text-lg hover:bg-red-800 transition-colors active:scale-95">
          ➤
        </button>
      </div>
    </div>
  )
}
