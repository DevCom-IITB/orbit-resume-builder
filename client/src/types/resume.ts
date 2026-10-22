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

export interface FontOption {
  key: string
  label: string
}

export interface TemplateSectionManifest {
  key: string
  displayName: string
  isDefault: boolean
  isRequired: boolean
  defaultOrder: number
}

export interface ResumeTemplate {
  key: string
  displayName: string
  family: string
  domain: string
  maxPages: number | null
  templateConfig: Record<string, any>
  availableThemes: VisualTheme[]
  defaultThemeKey?: string
  fonts?: FontOption[]
  fontDefault?: string
  accents?: string[]
  accentDefault?: string
  lineSpacings?: string[]
  lineSpacingDefault?: string
  wordSpacings?: string[]
  wordSpacingDefault?: string
  sections?: TemplateSectionManifest[]
}

export interface StyleState {
  font: string
  accent: string
  lineSpacing?: string
  wordSpacing?: string
  line_spacing?: string
  word_spacing?: string
}

export interface StyleOptions {
  fonts: FontOption[]
  fontDefault: string
  accents: string[]
  accentDefault: string
  lineSpacings?: string[]
  lineSpacingDefault?: string
  wordSpacings?: string[]
  wordSpacingDefault?: string
}

export interface GetStyleResponse {
  style: StyleState
  options: StyleOptions
}

export interface PatchStyleResponse {
  changed: boolean
  style: StyleState
  pdf?: string
  latex?: string
  pages?: number
  pageCount?: number
}

export interface SwitchPlan {
  willHide: string[]
  willAddEmpty: string[]
  willRestore: string[]
  styleReset: string[]
  unchanged: string[]
}

export interface SwitchPlanResponse {
  dryRun: true
  plan: SwitchPlan
}

export interface SwitchTemplateSuccessResponse {
  changed: boolean
  template: { key: string; displayName: string }
  themeKey: string
  sections: Array<{
    key: string
    displayName: string
    order: number
    isVisible: boolean
    hasData: boolean
  }>
  style: StyleState
  options: StyleOptions
  warnings: string[]
  pdf?: string
  latex?: string
  pages?: number
  pageCount?: number
}

export interface Resume {
  id: string
  title: string
  template: {
    key: string
    displayName: string
    fontDefault?: string
    accentDefault?: string
    lineSpacingDefault?: string
    wordSpacingDefault?: string
  }
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
