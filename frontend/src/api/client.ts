import type { Status, Book, SearchResult, Npc, Monster, Setting, DungeonMap } from '../types'

const BASE = ''

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  status: (): Promise<Status> =>
    fetch(`${BASE}/api/status`).then(r => json<Status>(r)),

  books: (): Promise<Book[]> =>
    fetch(`${BASE}/api/books`).then(r => json<Book[]>(r)),

  deleteBook: (source: string): Promise<{ status: string }> =>
    fetch(`${BASE}/api/books/${source}`, { method: 'DELETE' }).then(r => json(r)),

  uploadBook: (file: File, source: string): Promise<{ status: string; source: string; pages: number; chunks: number }> => {
    const form = new FormData()
    form.append('file', file)
    form.append('source', source)
    return fetch(`${BASE}/api/upload`, { method: 'POST', body: form }).then(r => json(r))
  },

  search: (q: string, source?: string, mode = 'semantic'): Promise<SearchResult[]> => {
    const params = new URLSearchParams({ q, mode })
    if (source) params.set('source', source)
    return fetch(`${BASE}/api/search?${params}`).then(r => json<SearchResult[]>(r))
  },

  generateNpc: (description: string): Promise<{ npc: Npc | string }> =>
    fetch(`${BASE}/api/generate/npc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    }).then(r => json(r)),

  generateMonster: (description: string): Promise<{ monster: Monster | string }> =>
    fetch(`${BASE}/api/generate/monster`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    }).then(r => json(r)),

  generateSetting: (description: string): Promise<{ setting: Setting | string }> =>
    fetch(`${BASE}/api/generate/setting`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    }).then(r => json(r)),

  generateMap: (description: string): Promise<{ map: DungeonMap | string }> =>
    fetch(`${BASE}/api/generate/map`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description }),
    }).then(r => json(r)),

  async *chat(question: string, history: { role: string; content: string }[]): AsyncGenerator<string> {
    const res = await fetch(`${BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    })
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const reader = res.body!.getReader()
    const dec = new TextDecoder()
    let buf = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buf += dec.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop() ?? ''
      for (const part of parts) {
        if (!part.startsWith('data: ')) continue
        const payload = part.slice(6).trim()
        if (payload === '[DONE]') return
        try {
          const d = JSON.parse(payload)
          if (d.token) yield d.token
          if (d.error) throw new Error(d.error)
        } catch { /* skip malformed */ }
      }
    }
  },
}
