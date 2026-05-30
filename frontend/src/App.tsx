import { useState } from 'react'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { ChatPane } from './components/ChatPane'
import { GeneratorPane } from './components/GeneratorPane'
import type { Npc, Monster, Setting, DungeonMap } from './types'

type ResultData = Npc | Monster | Setting | DungeonMap | string | null
import styles from './App.module.scss'

type Tab = 'chat' | 'npc' | 'monster' | 'setting' | 'map'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat',    label: 'The Oracle' },
  { id: 'npc',     label: 'Conjure NPC' },
  { id: 'monster', label: 'Summon Creature' },
  { id: 'setting', label: 'Forge Setting' },
  { id: 'map',     label: 'Forge Map' },
]

export interface GeneratorResults {
  npc:     Npc     | string | null
  monster: Monster | string | null
  setting: Setting | string | null
  map:     DungeonMap | string | null
}

export function App() {
  const [tab, setTab] = useState<Tab>('chat')
  const [results, setResults] = useState<GeneratorResults>({
    npc: null, monster: null, setting: null, map: null,
  })

  function setResult(key: keyof GeneratorResults, value: ResultData) {
    setResults(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className={styles.root}>
      <Header />
      <div className={styles.layout}>
        <Sidebar />
        <div className={styles.main}>
          <div className={styles.tabBar}>
            {TABS.map(t => (
              <button
                key={t.id}
                className={`${styles.tab} ${tab === t.id ? styles.active : ''}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className={styles.paneWrap}>
            {tab === 'chat'    && <ChatPane />}
            {tab === 'npc'     && <GeneratorPane type="npc"     result={results.npc}     onResult={v => setResult('npc', v)} />}
            {tab === 'monster' && <GeneratorPane type="monster" result={results.monster} onResult={v => setResult('monster', v)} />}
            {tab === 'setting' && <GeneratorPane type="setting" result={results.setting} onResult={v => setResult('setting', v)} />}
            {tab === 'map'     && <GeneratorPane type="map"     result={results.map}     onResult={v => setResult('map', v)} />}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
