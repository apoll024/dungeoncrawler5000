import { useRef, useState } from 'react'
import { api } from '../api/client'
import styles from './ChatPane.module.scss'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function escHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export function ChatPane() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Welcome, adventurer. I am the Oracle — your guide through the archives of D&D lore and rules. Ask me anything from the tomes in the Grimoire.\n\nTry: "How does grappling work?" or "What are the rules for opportunity attacks?"' },
  ])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function autoResize() {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  async function send() {
    if (streaming || !input.trim()) return
    const q = input.trim()
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const history = messages.map(m => ({ role: m.role, content: m.content }))
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])
    setStreaming(true)

    try {
      let full = ''
      for await (const token of api.chat(q, history.slice(-10))) {
        full += token
        setMessages(prev => {
          const next = [...prev]
          next[next.length - 1] = { role: 'assistant', content: full }
          return next
        })
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Connection error'
      setMessages(prev => {
        const next = [...prev]
        next[next.length - 1] = { role: 'assistant', content: `Error: ${msg}` }
        return next
      })
    }
    setStreaming(false)
  }

  function clearChat() {
    if (!confirm('Clear chat history?')) return
    setMessages([{ role: 'assistant', content: 'Chat cleared. Ask the Oracle anything.' }])
  }

  return (
    <div className={styles.pane}>
      <div className={styles.messages}>
        {messages.map((m, i) => (
          <div key={i} className={`${styles.msg} ${styles[m.role]}`}>
            <div className={styles.avatar}>{m.role === 'user' ? 'You' : 'Oracle'}</div>
            <div
              className={styles.bubble}
              dangerouslySetInnerHTML={{ __html: escHtml(m.content).replace(/\n/g, '<br/>') }}
            />
          </div>
        ))}
        {streaming && <div className={styles.cursor} />}
        <div ref={bottomRef} />
      </div>
      <div className={styles.hint}>Shift+Enter for new line &middot; Enter to send</div>
      <div className={styles.inputRow}>
        <textarea
          ref={textareaRef}
          className={styles.input}
          placeholder="Ask the Oracle..."
          rows={1}
          value={input}
          onChange={e => { setInput(e.target.value); autoResize() }}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
        />
        <button className={styles.clearBtn} onClick={clearChat} title="Clear chat">Clear</button>
        <button className={styles.sendBtn} disabled={streaming} onClick={send}>
          Consult Oracle
        </button>
      </div>
    </div>
  )
}
