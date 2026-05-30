import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Book } from '../types'
import styles from './Sidebar.module.scss'

export function Sidebar() {
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [sourceId, setSourceId] = useState('')
  const [progress, setProgress] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState<{ source: string; page: number; text: string }[]>([])

  const { data: books = [] } = useQuery<Book[]>({
    queryKey: ['books'],
    queryFn: api.books,
  })

  const deleteMutation = useMutation({
    mutationFn: (source: string) => api.deleteBook(source),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['books'] }),
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file, source }: { file: File; source: string }) =>
      api.uploadBook(file, source),
    onMutate: () => setProgress('Ingesting... this may take a minute'),
    onSuccess: (d) => {
      setProgress(`Done: ${d.source} - ${d.pages} pages, ${d.chunks} passages`)
      setSelectedFile(null)
      setSourceId('')
      if (fileRef.current) fileRef.current.value = ''
      qc.invalidateQueries({ queryKey: ['books'] })
      qc.invalidateQueries({ queryKey: ['status'] })
    },
    onError: (e: Error) => setProgress(`Error: ${e.message}`),
  })

  function handleFile(f: File) {
    if (!f.name.endsWith('.pdf')) return
    setSelectedFile(f)
    if (!sourceId) {
      setSourceId(f.name.replace('.pdf', '').replace(/[^a-zA-Z0-9]/g, '').toUpperCase().slice(0, 10))
    }
    setProgress(`Ready: ${f.name}`)
  }

  async function handleSearch() {
    if (!searchQ.trim()) return
    const results = await api.search(searchQ.trim(), undefined, 'semantic')
    setSearchResults(results.slice(0, 5))
  }

  return (
    <aside className={styles.sidebar}>
      <div className={styles.sectionTitle}>Grimoire</div>

      <div className={styles.bookList}>
        {books.length === 0 ? (
          <div className={styles.noBooks}>No tomes indexed yet.<br />Upload a PDF to begin.</div>
        ) : (
          books.map((b) => (
            <div key={b.source} className={styles.bookItem}>
              <div className={styles.bookInfo}>
                <div className={styles.bookName}>{b.source}</div>
                <div className={styles.bookMeta}>{b.chunks ?? '?'} passages &middot; {b.pages ?? '?'} pages</div>
              </div>
              <button
                className={styles.bookDel}
                onClick={() => {
                  if (confirm(`Remove "${b.source}" from the Grimoire?`)) {
                    deleteMutation.mutate(b.source)
                  }
                }}
              >x</button>
            </div>
          ))
        )}
      </div>

      <div className={styles.sectionTitle} style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
        Search Lore
      </div>
      <div className={styles.searchRow}>
        <input
          className={styles.sourceInput}
          placeholder="Search sourcebooks..."
          value={searchQ}
          onChange={e => setSearchQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
        />
        <button className={styles.uploadBtn} onClick={handleSearch} style={{ padding: '6px 10px' }}>Go</button>
      </div>
      {searchResults.length > 0 && (
        <div className={styles.searchResults}>
          {searchResults.map((r, i) => (
            <div key={i} className={styles.searchResult}>
              <span className={styles.searchMeta}>[{r.source} p.{r.page}]</span>
              <span className={styles.searchText}>{r.text.slice(0, 140)}...</span>
            </div>
          ))}
        </div>
      )}

      <div className={styles.uploadArea}>
        <div
          className={`${styles.uploadDrop} ${dragOver ? styles.dragOver : ''}`}
          onClick={() => fileRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => {
            e.preventDefault()
            setDragOver(false)
            const f = e.dataTransfer.files[0]
            if (f) handleFile(f)
          }}
        >
          <div className={styles.dropText}>
            <strong>Drop PDF or click</strong>
            to add a sourcebook
          </div>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
        <div className={styles.sourceRow}>
          <input
            className={styles.sourceInput}
            placeholder="Source ID (e.g. PHB)"
            maxLength={12}
            value={sourceId}
            onChange={e => setSourceId(e.target.value.toUpperCase())}
          />
          <button
            className={styles.uploadBtn}
            disabled={!selectedFile || uploadMutation.isPending}
            onClick={() => {
              if (selectedFile && sourceId.trim()) {
                uploadMutation.mutate({ file: selectedFile, source: sourceId.trim() })
              }
            }}
          >Up</button>
        </div>
        {progress && (
          <div className={styles.progress} style={{
            color: progress.startsWith('Done') ? 'var(--green2)' : progress.startsWith('Error') ? 'var(--red2)' : 'var(--gold)',
          }}>
            {progress}
          </div>
        )}
      </div>
    </aside>
  )
}
