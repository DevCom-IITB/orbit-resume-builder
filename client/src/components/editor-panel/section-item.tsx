import { useState } from 'react'
import GeneratedTextArea from './generated-textarea'
import ItemTextArea from './item-textarea'
import type { Item } from '../../types/editor-panel/item'
import { generateSectionData, type SectionType } from '../../lib/api'
import { useSortable } from '@dnd-kit/sortable'

import deleteIcon from '../../assets/editor-panel/delete.png'
import dragIcon from '../../assets/editor-panel/drag.png'
import collapseIcon from '../../assets/editor-panel/collapse.png'
import expandIcon from '../../assets/editor-panel/expand.png'
// import { useEffect, useState } from "react";
// import { CSS } from "@dnd-kit/utilities";

interface SectionItemProps {
  item: Item
  label: string
  displayIndex: number
  sectionType: SectionType
  sectionId?: number
  isReorderEnabled: boolean

  onToggleCollapse: (itemId: number) => void
  onItemDelete: (itemId: number) => void
  onDescChange: (itemId: number, updatedText: string) => void
  onTextGenerated: (itemId: number, generatedText: string) => void
  onUpdateGeneratedText: (itemId: number, updatedText: string) => void
}

const SectionItem = ({
  item,
  label,
  displayIndex,
  sectionType,
  sectionId,
  isReorderEnabled,
  onToggleCollapse,
  onItemDelete,
  onDescChange,
  onTextGenerated,
  onUpdateGeneratedText,
}: SectionItemProps) => {
  // TODO: Extend with an explicit "idle" state if the UI needs it later.
  const [generateStatus, setGenerateStatus] = useState<
    'loading' | 'success' | 'error'
  >('success')

  const isCollapsed = item.isCollapsed

  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({
      id: `${sectionId}-${item.id}`,
      disabled: !isReorderEnabled,
    })

  const handleUpdateDesc = (updatedText: string) => {
    onDescChange(item.id, updatedText)
  }
  //=============================================================================
  // API CALL
  //============================================================================
  const handleGenerateText = async (textVal: string) => {
    setGenerateStatus('loading')

    try {
      const data = await generateSectionData(sectionType, textVal)

      // TODO: Update this mapping when the backend response schema is finalized.
      const apiText =
        typeof data === 'string' ? data : JSON.stringify(data, null, 2)

      onTextGenerated(item.id, apiText)
      setGenerateStatus('success')
    } catch (error) {
      console.error('Error generating text:', error)
      // onTextGenerated(item.id, textVal)
      setGenerateStatus('error')
    }
  }

  const handleUpdateGeneratedDesc = (updatedText: string) => {
    onUpdateGeneratedText(item.id, updatedText)
  }

  const generateButtonLabel =
    generateStatus === 'loading'
      ? 'Generating...'
      : generateStatus === 'error'
        ? 'Retry'
        : item.generatedText
          ? 'Regenerate'
          : 'Generate'

  return (
    <div
      className="section-item-card"
      ref={setNodeRef}
      style={{
        transform: transform
          ? `translate3d(0px, ${transform.y}px, 0px)`
          : undefined,
        transition,
      }}
    >
      <div className="section-item-header">
        <p className="section-item-title">
          {label} {displayIndex + 1}
        </p>

        <div
          className="reorder-drag-button"
          style={{
            display: isReorderEnabled ? 'flex' : 'none',
          }}
        >
          <button className="item-drag-button" {...attributes} {...listeners}>
            <img className="icon-button" src={dragIcon} />
          </button>
        </div>

        <div
          className="section-item-controls"
          style={{
            display: isReorderEnabled ? 'none' : 'flex',
          }}
        >
          <button
            className="delete-item-button"
            onClick={() => {
              onItemDelete(item.id)
            }}
          >
            <img className="icon-button" src={deleteIcon} />
          </button>

          <button
            className="collapse-item-button"
            onClick={() => {
              const lastDrag = window.LAST_DND_TIME ?? 0

              if (Date.now() - lastDrag < 180) {
                return
              }

              onToggleCollapse(item.id)
            }}
          >
            <img
              className="icon-button"
              src={isCollapsed ? expandIcon : collapseIcon}
            />
            {/* {isCollapsed ? "+" : "-"} */}
          </button>
        </div>
      </div>

      <div
        className={`item-content-wrapper ${
          item.isCollapsed ? 'collapsed' : 'expanded'
        }`}
      >
        <div>
          <ItemTextArea
            desc={item.desc}
            updateDesc={handleUpdateDesc}
            onGenerateClicked={handleGenerateText}
            generateStatus={generateStatus}
            generateButtonLabel={generateButtonLabel}
          />
          {generateStatus === 'error' && (
            <div className="error-message">
              An error occurred. Please try again.
            </div>
          )}
          <GeneratedTextArea
            generatedText={item.generatedText}
            updateGeneratedText={handleUpdateGeneratedDesc}
          />
          {/* Text areas here */}
        </div>
      </div>
    </div>
  )
}
export default SectionItem
