import { useState, useRef, useEffect } from 'react'
import { sendChat } from '../api/client'

export default function ChatPage() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hey! I\'m FightIQ AI. Ask me anything about UFC 327, fighter stats, or betting analysis. 🥊' },
  ])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typing])

  async function send() {
    const msg = input.trim()
    if (!msg) return
    setInput('')
    setMessages(m => [...m, { role: 'user', text: msg }])
    setTyping(true)

    try {
      const res = await sendChat(msg)
      setMessages(m => [...m, { role: 'bot', text: res.response || 'No response.' }])
    } catch {
      setMessages(m => [...m, { role: 'bot', text: 'Sorry, something went wrong. Try again!' }])
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
            className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
              m.role === 'bot'
                ? 'self-start bg-dark-700 rounded-bl-sm text-gray-300'
                : 'self-end bg-brand-red rounded-br-sm text-white ml-auto'
            }`}
          >
            {m.text}
          </div>
        ))}
        {typing && (
          <div className="self-start bg-dark-700 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%]">
            <div className="flex gap-1.5">
              <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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
          placeholder="Ask about the fight..."
          className="flex-1 bg-dark-700 border border-dark-500 rounded-3xl px-5 py-3 text-sm text-white outline-none focus:border-brand-red placeholder:text-gray-600"
        />
        <button onClick={send} className="w-11 h-11 rounded-full bg-brand-red flex items-center justify-center text-lg hover:bg-red-800 transition-colors active:scale-95">
          ➤
        </button>
      </div>
    </div>
  )
}
