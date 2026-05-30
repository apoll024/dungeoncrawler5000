import { useEffect, useRef } from 'react'
import type { DungeonMap, MapRoom } from '../types'
import styles from './MapCanvas.module.scss'

const ROOM_COLORS: Record<string, { fill: string; text: string }> = {
  entrance: { fill: '#c9921a', text: '#1a0f00' },
  corridor: { fill: '#3a2a18', text: '#9a7a50' },
  room:     { fill: '#26190c', text: '#e8d5b0' },
  chamber:  { fill: '#31200f', text: '#e8d5b0' },
  boss:     { fill: '#5a0a0a', text: '#f08080' },
  treasure: { fill: '#3a3000', text: '#f5d080' },
  trap:     { fill: '#4a2a00', text: '#e8803a' },
  stairs:   { fill: '#1a2a3a', text: '#80b8d0' },
  secret:   { fill: '#2a1a3a', text: '#b080d0' },
  default:  { fill: '#2a1f12', text: '#c8a060' },
}

function roomColor(type: string) {
  return ROOM_COLORS[type] ?? ROOM_COLORS.default
}

function parseRooms(raw: DungeonMap['rooms']): MapRoom[] {
  return (raw ?? []).map((r, idx) => ({
    ...r,
    id: Number(r.id ?? idx + 1),
    x: Number(r.x ?? 0),
    y: Number(r.y ?? 0),
    w: Math.max(1, Number(r.w ?? 6)),
    h: Math.max(1, Number(r.h ?? 6)),
    connections: Array.isArray(r.connections) ? r.connections.map(Number).filter(Number.isFinite) : [],
  }))
}

export function MapCanvas({ map }: { map: DungeonMap }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rooms = parseRooms(map.rooms)
  const GRID = 64, CELL = 8
  const W = GRID * CELL, H = GRID * CELL

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!

    ctx.fillStyle = '#0d0905'
    ctx.fillRect(0, 0, W, H)

    ctx.strokeStyle = 'rgba(90,58,24,0.25)'
    ctx.lineWidth = 0.5
    for (let x = 0; x <= GRID; x++) {
      ctx.beginPath(); ctx.moveTo(x * CELL, 0); ctx.lineTo(x * CELL, H); ctx.stroke()
    }
    for (let y = 0; y <= GRID; y++) {
      ctx.beginPath(); ctx.moveTo(0, y * CELL); ctx.lineTo(W, y * CELL); ctx.stroke()
    }

    ctx.strokeStyle = 'rgba(201,146,26,0.35)'
    ctx.lineWidth = 1.5
    rooms.forEach(r => {
      const cx = (r.x + r.w / 2) * CELL
      const cy = (r.y + r.h / 2) * CELL
      r.connections.forEach(toId => {
        const target = rooms.find(t => t.id === toId)
        if (!target) return
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo((target.x + target.w / 2) * CELL, (target.y + target.h / 2) * CELL)
        ctx.stroke()
      })
    })

    rooms.forEach(r => {
      const x = Math.max(0, r.x) * CELL
      const y = Math.max(0, r.y) * CELL
      const w = Math.min(r.w, GRID - r.x) * CELL
      const h = Math.min(r.h, GRID - r.y) * CELL
      if (w <= 0 || h <= 0) return
      const col = roomColor(r.type)
      ctx.fillStyle = col.fill
      ctx.fillRect(x + 1, y + 1, w - 2, h - 2)
      ctx.strokeStyle = col.text
      ctx.lineWidth = 1
      ctx.strokeRect(x + 1, y + 1, w - 2, h - 2)
      if (w >= 24 && h >= 14) {
        ctx.fillStyle = col.text
        ctx.font = `bold ${Math.min(9, w / 8)}px 'Courier New', monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        const label = r.name?.length > 14 ? r.name.slice(0, 13) + 'â€¦' : r.name || ''
        ctx.fillText(label, x + w / 2, y + h / 2)
      }
    })
  }, [map])

  const usedTypes = [...new Set(rooms.map(r => r.type || 'room'))]

  return (
    <>
      <div className={styles.title}>{map.name || 'Unnamed Dungeon'}</div>
      {map.theme && <div className={styles.theme}>{map.theme}</div>}
      <canvas ref={canvasRef} width={W} height={H} className={styles.canvas} />
      <div className={styles.legend}>
        {usedTypes.map(type => {
          const col = roomColor(type)
          return (
            <div key={type} className={styles.legendItem}>
              <div className={styles.swatch} style={{ background: col.fill, borderColor: col.text }} />
              <span>{type}</span>
            </div>
          )
        })}
      </div>
      {rooms.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>#</th><th>Name</th><th>Type</th><th>Description</th>
            </tr>
          </thead>
          <tbody>
            {rooms.map(r => {
              const col = roomColor(r.type)
              return (
                <tr key={r.id}>
                  <td className={styles.idCell}>{r.id}</td>
                  <td className={styles.nameCell}>{r.name}</td>
                  <td>
                    <span className={styles.badge} style={{ background: col.fill, color: col.text }}>
                      {r.type || 'room'}
                    </span>
                  </td>
                  <td>{r.description}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </>
  )
}

