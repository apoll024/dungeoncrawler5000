import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import styles from './Header.module.scss'

export function Header() {
  const { data } = useQuery({
    queryKey: ['status'],
    queryFn: api.status,
    refetchInterval: 30_000,
  })

  const llmOnline = data?.llm === 'online'

  return (
    <header className={styles.header}>
      <span className={styles.title}>⚔ DungeonCrawler 5000</span>
      <div className={styles.spacer} />
      <div className={styles.pills}>
        <span className={`${styles.pill} ${llmOnline ? styles.green : styles.red}`}>
          {data ? (llmOnline ? 'LLM Online' : 'LLM Offline') : 'Checking...'}
        </span>
        <span className={`${styles.pill} ${styles.gold}`}>
          {data?.books ?? '--'} Tome{data?.books !== 1 ? 's' : ''}
        </span>
        <span className={`${styles.pill} ${styles.dim}`}>
          {data?.chunks?.toLocaleString() ?? '--'} Passages
        </span>
        <span className={`${styles.pill} ${styles.dim}`}>
          {data?.training_items?.toLocaleString() ?? '--'} Source Notes
        </span>
      </div>
    </header>
  )
}
