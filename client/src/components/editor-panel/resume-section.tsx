import { useState } from 'react'
import SectionItem from './section-item'
import type { Section } from '../../types/editor-panel/section'
import { DndContext, type DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
  useSortable,
} from '@dnd-kit/sortable'
import dragIcon from '../../assets/editor-panel/drag.png'
import collapseIcon from '../../assets/editor-panel/collapse.png'
import expandIcon from '../../assets/editor-panel/expand.png'
import type { Item } from '../../types/editor-panel/item'

interface ResumeSectionProps {
  section: Section
  isSectionReorderEnabled: boolean
  onItemCollapse: (sectionId: number, itemId: number) => void
  onItemAdd: (sectionId: number) => void
  onItemDelete: (sectionId: number, itemId: number) => void
  onItemDescChange: (
    sectionId: number,
    itemId: number,
    updatedText: string
  ) => void
  onItemTextGenerated: (
    sectionId: number,
    itemId: number,
    generatedText: string
  ) => void
  onUpdateItemGeneratedText: (
    sectionId: number,
    itemId: number,
    updatedText: string
  ) => void
  onItemReorder: (sectionId: number, reorderedItems: Item[]) => void
  onSectionCollapse: (sectionId: number) => void
}

const ResumeSection = ({
  section,
  isSectionReorderEnabled,
  onItemCollapse,
  onItemAdd,
  onItemDelete,
  onItemDescChange,
  onItemTextGenerated,
  onUpdateItemGeneratedText,
  onItemReorder,
  onSectionCollapse,
}: ResumeSectionProps) => {
  const [isReorderEnabled, setReorderEnabled] = useState(false)

  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({
      id: `section-${section.id}`,
      disabled: !isSectionReorderEnabled,
    })

  const handleItemCollapse = (itemId: number) => {
    onItemCollapse(section.id, itemId)
  }

  const handleItemDelete = (itemId: number) => {
    onItemDelete(section.id, itemId)
  }

  const handleItemDescChange = (itemId: number, updatedText: string) => {
    onItemDescChange(section.id, itemId, updatedText)
  }

  const handleItemTextGenerated = (itemId: number, generatedText: string) => {
    onItemTextGenerated(section.id, itemId, generatedText)
  }

  const handleUpdateItemGeneratedText = (
    itemId: number,
    generatedText: string
  ) => {
    onUpdateItemGeneratedText(section.id, itemId, generatedText)
  }

  const handleSectionCollapse = (sectionId: number) => {
    onSectionCollapse(sectionId)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    window.LAST_DND_TIME = Date.now()

    const { active, over } = event

    if (!over) return

    if (active.id === over.id) return

    const oldIndex = section.items.findIndex(
      (item) => `${section.id}-${item.id}` === active.id
    )

    const newIndex = section.items.findIndex(
      (item) => `${section.id}-${item.id}` === over.id
    )

    const reorderedItems = arrayMove(section.items, oldIndex, newIndex)

    onItemReorder(section.id, reorderedItems)
  }

  return (
    <div
      className="resume-section-card"
      ref={setNodeRef}
      style={{
        transform: transform
          ? `translate3d(0px, ${transform.y}px, 0px)`
          : undefined,
        transition,
      }}
    >
      <div className="resume-section-topbar">
        <h1>{section.title}</h1>

        <div className="resume-section-topbar-controls">
          <div
            className="section-item-toolbar"
            style={{
              display: isSectionReorderEnabled
                ? 'none'
                : section.isCollapsed
                  ? 'none'
                  : 'flex',
            }}
          >
            <button
              className="item-reorder-toggle-button"
              onClick={() => {
                if (!isReorderEnabled) {
                  handleItemCollapse(-1)
                }

                setReorderEnabled((prev) => !prev)
              }}
            >
              {isReorderEnabled ? 'Disable Reordering' : 'Enable Reordering'}
            </button>
          </div>

          <div
            className="section-collapse-container"
            style={{
              display: isSectionReorderEnabled ? 'none' : 'flex',
            }}
          >
            <button
              className="section-collapse-button"
              onClick={() => {
                const lastDrag = window.LAST_DND_TIME ?? 0

                if (Date.now() - lastDrag < 180) {
                  return
                }

                handleSectionCollapse(section.id)
              }}
            >
              <img
                className="icon-button"
                src={section.isCollapsed ? expandIcon : collapseIcon}
                alt={section.isCollapsed ? '+' : '-'}
              />
            </button>
          </div>
        </div>

        {isSectionReorderEnabled && (
          <div
            className="section-drag-container"
            style={{
              visibility: isSectionReorderEnabled ? 'visible' : 'hidden',
              pointerEvents: isSectionReorderEnabled ? 'auto' : 'none',
            }}
          >
            <button
              className="section-drag-button"
              {...attributes}
              {...listeners}
            >
              <img className="icon-button" src={dragIcon} />
            </button>
          </div>
        )}
      </div>
      <div
        className={`section-item-container ${
          section.isCollapsed ? 'collapsed' : 'expanded'
        }`}
      >
        <div className="section-content-wrapper">
          <DndContext onDragEnd={handleDragEnd}>
            <SortableContext
              items={section.items.map((item) => `${section.id}-${item.id}`)}
              strategy={verticalListSortingStrategy}
            >
              <div
                className="item-data-container"
                style={{
                  width: '100%',
                  minWidth: 0,
                }}
              >
                {section.items.map((item, index) => (
                  <SectionItem
                    key={`${section.id}-${item.id}`}
                    item={item}
                    label={section.label}
                    sectionType={section.sectionType}
                    sectionId={section.id}
                    displayIndex={index}
                    isReorderEnabled={isReorderEnabled}
                    onToggleCollapse={handleItemCollapse}
                    onItemDelete={handleItemDelete}
                    onDescChange={handleItemDescChange}
                    onTextGenerated={handleItemTextGenerated}
                    onUpdateGeneratedText={handleUpdateItemGeneratedText}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>

          <div className="section-item-add">
            <button
              className="add-section-item-button"
              onClick={() => {
                onItemAdd(section.id)
              }}
            >
              + Add {section.label}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
export default ResumeSection
