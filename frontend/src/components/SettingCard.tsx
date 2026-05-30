import type { Setting, Faction } from '../types'
import styles from './Card.module.scss'

function List({ items, title }: { items: string[]; title: string }) {
  if (!items?.length) return null
  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>{title}</div>
      {items.map((item, i) => (
        <div key={i} className={styles.hook}><span className={styles.label}>{i + 1}.</span> {item}</div>
      ))}
    </div>
  )
}

export function SettingCard({ setting: s }: { setting: Setting }) {
  const factions: (Faction | string)[] = Array.isArray(s.factions) ? s.factions : []

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.name}>{s.name || 'Source-Inspired Setting'}</div>
        <div className={styles.subtitle}>{s.region_type || ''}</div>
      </div>

      {s.premise && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Premise</div>
          <p>{s.premise}</p>
        </div>
      )}

      {factions.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Factions</div>
          {factions.map((f, i) => (
            <div key={i} className={styles.action}>
              {typeof f === 'string'
                ? <span>{f}</span>
                : <><span className={styles.actionName}>{f.name}.</span> <span>{f.description}</span></>
              }
            </div>
          ))}
        </div>
      )}

      <List items={s.key_conflicts}   title="Key Conflicts" />
      <List items={s.adventure_seeds} title="Adventure Seeds" />
      <List items={s.rumors}          title="Rumors" />
    </div>
  )
}

