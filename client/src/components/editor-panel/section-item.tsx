import { useState } from 'react'
import GeneratedTextArea from './generated-textarea'
import ItemTextArea from './item-textarea'
import type { Item } from '../../types/editor-panel/item'
import { generateSectionData, type SectionType } from '../../lib/api'
import { useSortable } from '@dnd-kit/sortable'
import { Trash2, GripHorizontal, Plus, Minus } from 'lucide-react'

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

  const [lastGeneratedDesc, setLastGeneratedDesc] = useState('')

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

    // Uncomment below lines to check if generated text appears
    // onTextGenerated(item.id, "Hello")
    // setLastGeneratedDesc(textVal)
    // setGenerateStatus('success')

    try {
      const data = await generateSectionData(sectionType, textVal)

      // TODO: Update this mapping when the backend response schema is finalized.
      const apiText =
        typeof data === 'string' ? data : JSON.stringify(data, null, 2)

      onTextGenerated(item.id, apiText)
      setLastGeneratedDesc(textVal)
      setGenerateStatus('success')
    } catch (error) {
      console.error('Error generating text:', error)
      setGenerateStatus('error')
    }
  }

  const handleUpdateGeneratedDesc = (updatedText: string) => {
    onUpdateGeneratedText(item.id, updatedText)
  }

  const normalizeText = (text: string) => text.replace(/\s+/g, ' ').trim()

  const lastGeneratedNormalized = normalizeText(lastGeneratedDesc)

  const generateButtonLabel =
    generateStatus === 'loading'
      ? 'Generating...'
      : generateStatus === 'error'
        ? 'Retry'
        : 'Generate'

  return (
    <div
      className={`section-item-card ${isCollapsed ? 'collapsed' : 'expanded'}`}
      ref={setNodeRef}
      style={{
        transform: transform
          ? `translate3d(0px, ${transform.y}px, 0px)`
          : undefined,
        transition,
      }}
    >
      <div className="section-item-header">
        <div
          className="reorder-drag-button"
          style={{
            display: isReorderEnabled ? 'flex' : 'none',
            alignItems: 'center',
          }}
        >
          <button className="item-drag-button" {...attributes} {...listeners}>
            <GripHorizontal className="lucide-icon drag-icon" />
          </button>
        </div>

        <div className="section-item-title">
          {label} {displayIndex + 1}
        </div>

        <div
          className="section-item-controls"
          data-mode={isReorderEnabled ? 'reorder' : 'normal'}
        >
          <button
            className="delete-item-button"
            style={{
              display: isReorderEnabled ? 'flex' : 'none',
              alignItems: 'center',
            }}
            onClick={() => {
              onItemDelete(item.id)
            }}
          >
            <Trash2 className="lucide-icon delete-icon" />
          </button>

          <button
            style={{
              display: isReorderEnabled ? 'none' : 'flex',
            }}
            className="collapse-item-button"
            onClick={() => {
              const lastDrag = window.LAST_DND_TIME ?? 0

              if (Date.now() - lastDrag < 180) {
                return
              }

              onToggleCollapse(item.id)
            }}
          >
            {isCollapsed ? (
              <Plus className="lucide-icon" />
            ) : (
              <Minus className="lucide-icon collapse-icon" />
            )}
          </button>
        </div>
      </div>

      <div
        className={`item-content-wrapper ${
          item.isCollapsed ? 'collapsed' : 'expanded'
        }`}
      >
        <div className="section-item-inner-card">
          <div>
            <ItemTextArea
              desc={item.desc}
              updateDesc={handleUpdateDesc}
              onGenerateClicked={handleGenerateText}
              generateStatus={generateStatus}
              generateButtonLabel={generateButtonLabel}
              lastGeneratedNormalized={lastGeneratedNormalized}
            />
          </div>
          {generateStatus === 'error' && (
            <div className="error-message">
              An error occurred. Please try again.
            </div>
          )}
        </div>

        {!!item.generatedText?.trim() && !item.isCollapsed && (
          <GeneratedTextArea
            generatedText={item.generatedText}
            updateGeneratedText={handleUpdateGeneratedDesc}
          />
        )}
      </div>
    </div>
  )
}
export default SectionItem
