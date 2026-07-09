import type { SectionEntry, ResumeSection } from '../resume'

export type LocalEntry = SectionEntry & { isCollapsed: boolean }

export type LocalSection = Omit<ResumeSection, 'entries'> & {
    isCollapsed: boolean
    entries: LocalEntry[]
}

export function toLocalEntry(entry: SectionEntry): LocalEntry {
    return { ...entry, isCollapsed: true }
}

export function toLocalSection(section: ResumeSection): LocalSection {
    return {
        ...section,
        isCollapsed: true,
        entries: section.entries.map(toLocalEntry),
    }
}
