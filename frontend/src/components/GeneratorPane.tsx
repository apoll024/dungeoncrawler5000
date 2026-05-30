import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Npc, Monster, Setting, DungeonMap } from '../types'
import { NpcCard } from './NpcCard'
import { MonsterCard } from './MonsterCard'
import { SettingCard } from './SettingCard'
import { MapCanvas } from './MapCanvas'
import styles from './GeneratorPane.module.scss'

type GenType = 'npc' | 'monster' | 'setting' | 'map'

interface Props { type: GenType }

const PLACEHOLDERS: Record<GenType, string> = {
  npc:     "Describe your NPC (optional)... e.g. 'A retired elven soldier haunted by a failed mission'\nLeave blank for a random NPC.",
  monster: "Describe your creature (optional)... e.g. 'A swamp-dwelling undead warlord CR 8'\nLeave blank for a random creature.",
  setting: "Describe your setting (optional)... e.g. 'A crumbling dwarven fortress reclaimed by a death cult'\nLeave blank for a random setting.",
  map:     "Describe your dungeon (optional)... e.g. 'A three-level tomb with trapped corridors and a boss chamber'\nLeave blank for a random dungeon.",
}

const LABELS: Record<GenType, { random: string; generate: string; loading: string }> = {
  npc:     { random: 'Random NPC',      generate: 'Conjure',    loading: 'The Oracle is weaving your character...' },
  monster: { random: 'Random Creature', generate: 'Summon',     loading: 'The Oracle is summoning a creature...' },
  setting: { random: 'Random Setting',  generate: 'Forge',      loading: 'The Oracle is forging a setting...' },
  map:     { random: 'Random Map',      generate: 'Forge Map',  loading: 'The Oracle is charting the dungeon depths...' },
}

type ResultData = Npc | Monster | Setting | DungeonMap | string | null

export function GeneratorPane({ type }: Props) {
  const [desc, setDesc] = useState('')
  const [result, setResult] = useState<ResultData>(null)
  const labels = LABELS[type]

  const mutation = useMutation({
    mutationFn: async (useDesc: boolean) => {
      const d = useDesc ? desc : ''
      switch (type) {
        case 'npc':     { const r = await api.generateNpc(d);     return r.npc }
        case 'monster': { const r = await api.generateMonster(d); return r.monster }
        case 'setting': { const r = await api.generateSetting(d); return r.setting }
        case 'map':     { const r = await api.generateMap(d);     return r.map }
      }
    },
    onSuccess: setResult,
  })

  function copyOutput() {
    if (!result) return
    const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2)
    navigator.clipboard.writeText(text)
  }

  return (
    <div className={styles.pane}>
      <div className={styles.form}>
        <textarea
          className={styles.input}
          placeholder={PLACEHOLDERS[type]}
          value={desc}
          onChange={e => setDesc(e.target.value)}
        />
        <button className={`${styles.btn} ${styles.random}`} disabled={mutation.isPending} onClick={() => mutation.mutate(false)}>
          {labels.random}
        </button>
        <button className={styles.btn} disabled={mutation.isPending} onClick={() => mutation.mutate(true)}>
          {labels.generate}
        </button>
      </div>

      <div className={styles.actions}>
        <button className={`${styles.outBtn} ${styles.copy}`} onClick={copyOutput}>Copy</button>
        <button className={`${styles.outBtn} ${styles.clear}`} onClick={() => setResult(null)}>Clear</button>
      </div>

      <div className={type === 'map' ? styles.mapWrap : styles.output}>
        {mutation.isPending && <div className={styles.loading}>{labels.loading}</div>}
        {mutation.isError && <div className={styles.error}>Error: {(mutation.error as Error).message}</div>}
        {!mutation.isPending && result === null && !mutation.isError && (
          <div className={styles.placeholder}>
            {type === 'npc'     && 'Describe an NPC above, or roll randomly.'}
            {type === 'monster' && 'Describe a creature above, or roll randomly.'}
            {type === 'setting' && 'Describe a setting above, or roll randomly.'}
            {type === 'map'     && 'Describe a dungeon above, or roll randomly.'}
          </div>
        )}
        {!mutation.isPending && result !== null && (
          <>
            {type === 'npc'     && typeof result !== 'string' && <NpcCard npc={result as Npc} />}
            {type === 'monster' && typeof result !== 'string' && <MonsterCard monster={result as Monster} />}
            {type === 'setting' && typeof result !== 'string' && <SettingCard setting={result as Setting} />}
            {type === 'map'     && typeof result !== 'string' && <MapCanvas map={result as DungeonMap} />}
            {typeof result === 'string' && <pre className={styles.raw}>{result}</pre>}
          </>
        )}
      </div>
    </div>
  )
}
