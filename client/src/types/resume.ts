export type GenerationStatus = 'pending' | 'generating' | 'done' | 'failed'

export interface SectionEntry {
  id: string
  order: number
  rawInput: string
  content: any | null
  generationStatus: GenerationStatus
}

export interface SectionType {
  key: string
  displayName: string
  allowMultipleEntries: boolean
  entryHintText: string
}

export interface ResumeSection {
  id: string
  sectionType: SectionType
  order: number
  isVisible: boolean
  entries: SectionEntry[]
}

export interface VisualTheme {
  key: string
  displayName: string
  compatibleFamilies: string[]
}

export interface ResumeTemplate {
  key: string
  displayName: string
  family: string
  domain: string
  maxPages: number | null
  templateConfig: Record<string, any>
  availableThemes: VisualTheme[]
}

export interface Resume {
  id: string
  title: string
  template: { key: string; displayName: string }
  visualTheme: { key: string; displayName: string }
  pages: number
  configOverride: Record<string, any>
  isPinned: boolean
  sections: ResumeSection[]
  createdAt: string
  updatedAt: string
}

export interface ResumeListItem {
  id: string
  title: string
  template: { key: string; displayName: string }
  visualTheme: { key: string; displayName: string }
  isPinned: boolean
  createdAt: string
  updatedAt: string
}
