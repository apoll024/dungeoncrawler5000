import { useState } from 'react'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { ChatPane } from './components/ChatPane'
import { GeneratorPane } from './components/GeneratorPane'
import styles from './App.module.scss'

type Tab = 'chat' | 'npc' | 'monster' | 'setting' | 'map'

const TABS: { id: Tab; label: string }[] = [
  { id: 'chat',    label: '\u{1F4AC} The Oracle' },
  { id: 'npc',     label: '\u{1F9D9} Conjure NPC' },
  { id: 'monster', label: '\u{1F409} Summon Creature' },
  { id: 'setting', label: '\u{1F3F0} Forge Setting' },
  { id: 'map',     label: '\u{1F5FA} Forge Map' },
]

export function App() {
  const [tab, setTab] = useState<Tab>('chat')

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
            {tab === 'npc'     && <GeneratorPane type="npc" />}
            {tab === 'monster' && <GeneratorPane type="monster" />}
            {tab === 'setting' && <GeneratorPane type="setting" />}
            {tab === 'map'     && <GeneratorPane type="map" />}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
