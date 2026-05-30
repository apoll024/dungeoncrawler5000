import type { Monster, MonsterAction } from '../types'
import styles from './Card.module.scss'

function mod(score: number) {
  const m = Math.floor((score - 10) / 2)
  return (m >= 0 ? '+' : '') + m
}

function ActionList({ items, title }: { items: (MonsterAction | string)[]; title: string }) {
  if (!items?.length) return null
  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>{title}</div>
      {items.map((item, i) => (
        <div key={i} className={styles.action}>
          {typeof item === 'string'
            ? <span>{item}</span>
            : <><span className={styles.actionName}>{item.name}.</span> <span>{item.description}</span></>
          }
        </div>
      ))}
    </div>
  )
}

export function MonsterCard({ monster: m }: { monster: Monster }) {
  const abs = m.ability_scores || {}
  const stats = ['str', 'dex', 'con', 'int', 'wis', 'cha'] as const

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.name}>{m.name || 'Unknown Creature'}</div>
        <div className={styles.subtitle}>{[m.size, m.type, m.alignment].filter(Boolean).join(' Â· ')}</div>
      </div>

      <div className={styles.crBadge}>âš” CR {m.challenge_rating || '?'} Â· {(m.xp || 0).toLocaleString()} XP</div>

      <div className={styles.section}>
        <p>
          <strong className={styles.label}>HP:</strong> {m.hit_points || '?'} &nbsp;
          <strong className={styles.label}>AC:</strong> {m.armor_class || '?'} &nbsp;
          <strong className={styles.label}>Speed:</strong> {m.speed || '?'}
        </p>
      </div>

      <div className={styles.divider} />

      <div className={styles.abilityRow}>
        {stats.map(a => (
          <div key={a} className={styles.abilityCell}>
            <div className={styles.abilLabel}>{a.toUpperCase()}</div>
            <div className={styles.abilVal}>{abs[a] || 10}</div>
            <div className={styles.abilMod}>{mod(abs[a] || 10)}</div>
          </div>
        ))}
      </div>

      <div className={styles.divider} />

      {m.saving_throws?.length  ? <div className={styles.section}><p><strong className={styles.label}>Saves:</strong> {m.saving_throws.join(', ')}</p></div> : null}
      {m.skills?.length         ? <div className={styles.section}><p><strong className={styles.label}>Skills:</strong> {m.skills.join(', ')}</p></div> : null}
      {m.senses                 ? <div className={styles.section}><p><strong className={styles.label}>Senses:</strong> {m.senses}</p></div> : null}
      {m.languages              ? <div className={styles.section}><p><strong className={styles.label}>Languages:</strong> {m.languages}</p></div> : null}

      <ActionList items={m.special_abilities} title="Special Abilities" />
      <ActionList items={m.actions} title="Actions" />
      {m.legendary_actions?.length ? <ActionList items={m.legendary_actions} title="Legendary Actions" /> : null}

      {m.lore && <><div className={styles.divider} /><div className={styles.section}><div className={styles.sectionTitle}>Lore</div><p>{m.lore}</p></div></>}
      {m.description && <div className={styles.section}><div className={styles.sectionTitle}>Description</div><p>{m.description}</p></div>}
    </div>
  )
}

