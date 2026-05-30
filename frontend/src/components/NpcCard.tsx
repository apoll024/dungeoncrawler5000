import type { Npc } from '../types'
import styles from './Card.module.scss'

export function NpcCard({ npc }: { npc: Npc }) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.name}>{npc.name || 'Unknown'}</div>
        <div className={styles.subtitle}>{[npc.ancestry, npc.role].filter(Boolean).join(' Â· ')}</div>
      </div>
      {npc.appearance && <Section title="Appearance"><p>{npc.appearance}</p></Section>}
      {npc.backstory  && <Section title="Backstory"><p>{npc.backstory}</p></Section>}
      {npc.personality_traits?.length > 0 && (
        <Section title="Personality">
          {npc.personality_traits.map((t, i) => <span key={i} className={styles.tag}>{t}</span>)}
        </Section>
      )}
      {npc.ideal && (
        <Section title="Ideal Â· Bond Â· Flaw">
          <p><strong className={styles.label}>Ideal:</strong> {npc.ideal}</p>
          {npc.bond && <p><strong className={styles.label}>Bond:</strong> {npc.bond}</p>}
          {npc.flaw && <p><strong className={styles.label}>Flaw:</strong> {npc.flaw}</p>}
        </Section>
      )}
      {npc.plot_hooks?.length > 0 && (
        <Section title="Plot Hooks">
          {npc.plot_hooks.map((h, i) => (
            <div key={i} className={styles.hook}><span className={styles.label}>{i + 1}.</span> {h}</div>
          ))}
        </Section>
      )}
      {npc.stat_block_suggestions?.cr && (
        <Section title="Stat Block Hints">
          <p><strong className={styles.label}>CR:</strong> {npc.stat_block_suggestions.cr}</p>
          {npc.stat_block_suggestions.key_abilities?.map((a, i) => <span key={i} className={styles.tag}>{a}</span>)}
        </Section>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>{title}</div>
      {children}
    </div>
  )
}

