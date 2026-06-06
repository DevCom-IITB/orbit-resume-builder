import type { Item } from './item'
import type { SectionType } from '../../lib/api'

export type Section = {
    id: number
    title: string
    label: string
    // TODO: Keep this aligned with backend section routing keys.
    sectionType: SectionType
    isCollapsed: boolean
    items: Item[]
}
