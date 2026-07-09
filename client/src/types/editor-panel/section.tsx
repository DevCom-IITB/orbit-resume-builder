import type { Item } from './item'

export type Section = {
    id: number
    title: string
    label: string
    sectionType: string
    isCollapsed: boolean
    items: Item[]
}
