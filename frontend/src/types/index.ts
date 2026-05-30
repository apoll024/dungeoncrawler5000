export interface Status {
  llm: 'online' | 'unconfigured'
  books: number
  chunks: number
  sql_chunks: number
  training_items: number
}

export interface Book {
  source: string
  filename: string
  pages: number
  chunks: number
  ingested_at: string
}

export interface SearchResult {
  source: string
  page: number
  text: string
  score: number | null
  mode: string
}

export interface NpcStatBlock {
  cr: string
  key_abilities: string[]
}

export interface Npc {
  name: string
  ancestry: string
  role: string
  appearance: string
  personality_traits: string[]
  ideal: string
  bond: string
  flaw: string
  backstory: string
  plot_hooks: string[]
  stat_block_suggestions: NpcStatBlock
}

export interface MonsterAbilityScores {
  str: number
  dex: number
  con: number
  int: number
  wis: number
  cha: number
}

export interface MonsterAction {
  name: string
  description: string
}

export interface Monster {
  name: string
  size: string
  type: string
  alignment: string
  challenge_rating: string
  xp: number
  hit_points: string
  armor_class: string
  speed: string
  ability_scores: MonsterAbilityScores
  senses: string
  languages: string
  special_abilities: MonsterAction[]
  actions: MonsterAction[]
  legendary_actions?: MonsterAction[]
  saving_throws?: string[]
  skills?: string[]
  damage_resistances?: string[]
  condition_immunities?: string[]
  description: string
  lore: string
}

export interface Faction {
  name: string
  description: string
}

export interface Setting {
  name: string
  premise: string
  region_type: string
  factions: Faction[]
  key_conflicts: string[]
  adventure_seeds: string[]
  rumors: string[]
}

export interface MapRoom {
  id: number
  name: string
  type: string
  x: number
  y: number
  w: number
  h: number
  description: string
  connections: number[]
}

export interface DungeonMap {
  name: string
  theme: string
  rooms: MapRoom[]
  source_notes?: string
}

export type Tab = 'chat' | 'npc' | 'monster' | 'setting' | 'map'
