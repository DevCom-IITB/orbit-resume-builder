import { useState } from 'react'
import GeneratedTextArea from './generated-textarea'
import ItemTextArea from './item-textarea'
import type { LocalEntry } from '../../types/editor-panel/local-state'
import { generateEntry as apiGenerateEntry, updateEntry } from '../../lib/api'
import { useSortable } from '@dnd-kit/sortable'
import { Trash2, GripHorizontal, Plus, Minus } from 'lucide-react'

interface SectionItemProps {
    entry: LocalEntry
    label: string
    displayIndex: number
    resumeId: string
    sectionId: string
    isReorderEnabled: boolean
    onToggleCollapse: (entryId: string) => void
    onEntryUpdated: (entry: import('../../types/resume').SectionEntry) => void
    onEntryDelete: (entryId: string) => void
    onRenderRequest: () => void
}

const SectionItem = ({
    entry,
    label,
    displayIndex,
    resumeId,
    sectionId,
    isReorderEnabled,
    onToggleCollapse,
    onEntryUpdated,
    onEntryDelete,
    onRenderRequest,
}: SectionItemProps) => {
    const [isGenerating, setIsGenerating] = useState(false)
    const [generateError, setGenerateError] = useState(false)
    const [lastGeneratedInput, setLastGeneratedInput] = useState(
        entry.generationStatus === 'done' && entry.content != null
            ? entry.rawInput
            : ''
    )

    const { attributes, listeners, setNodeRef, transform, transition } =
        useSortable({
            id: entry.id,
            disabled: !isReorderEnabled,
        })

    const contentAsString =
        entry.content != null ? JSON.stringify(entry.content, null, 2) : ''

    // Debounced raw input save (fire-and-forget; does not update parent state)
    const handleUpdateRawInput = (rawInput: string) => {
        updateEntry(resumeId, sectionId, entry.id, { rawInput }).catch((err) =>
            console.error('[SectionItem] rawInput save failed:', err)
        )
    }

    const handleGenerateClick = async (textVal: string) => {
        setIsGenerating(true)
        setGenerateError(false)
        try {
            // Flush current rawInput to server before generating
            await updateEntry(resumeId, sectionId, entry.id, {
                rawInput: textVal,
            })
            const updated = await apiGenerateEntry(resumeId, sectionId, entry.id)
            setLastGeneratedInput(textVal)
            onEntryUpdated(updated)
            // Generating new content auto-refreshes the PDF preview.
            onRenderRequest()
        } catch (err) {
            console.error('[SectionItem] Generation failed:', err)
            setGenerateError(true)
        } finally {
            setIsGenerating(false)
        }
    }

    const handleUpdateContent = async (jsonText: string) => {
        try {
            const parsed = JSON.parse(jsonText)
            const updated = await updateEntry(resumeId, sectionId, entry.id, {
                content: parsed,
            })
            onEntryUpdated(updated)
            // Manual JSON edits also refresh the PDF preview.
            onRenderRequest()
        } catch (err) {
            console.error('[SectionItem] Content save failed:', err)
        }
    }

    const generateStatus = isGenerating
        ? 'loading'
        : generateError
          ? 'error'
          : 'success'
    const generateButtonLabel = isGenerating
        ? 'Generating...'
        : generateError
          ? 'Retry'
          : 'Generate'

    const normalizeText = (text: string) => text.replace(/\s+/g, ' ').trim()

    return (
        <div
            className={`section-item-card ${entry.isCollapsed ? 'collapsed' : 'expanded'}`}
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
                    <button
                        className="item-drag-button"
                        {...attributes}
                        {...listeners}
                    >
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
                        onClick={() => onEntryDelete(entry.id)}
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
                            if (Date.now() - lastDrag < 180) return
                            onToggleCollapse(entry.id)
                        }}
                    >
                        {entry.isCollapsed ? (
                            <Plus className="lucide-icon" />
                        ) : (
                            <Minus className="lucide-icon collapse-icon" />
                        )}
                    </button>
                </div>
            </div>

            <div
                className={`item-content-wrapper ${
                    entry.isCollapsed ? 'collapsed' : 'expanded'
                }`}
            >
                <div className="section-item-inner-card">
                    <ItemTextArea
                        desc={entry.rawInput}
                        updateDesc={handleUpdateRawInput}
                        onGenerateClicked={(textVal) => {
                            void handleGenerateClick(textVal)
                        }}
                        generateStatus={generateStatus}
                        generateButtonLabel={generateButtonLabel}
                        lastGeneratedNormalized={normalizeText(
                            lastGeneratedInput
                        )}
                    />
                    {generateError && (
                        <div className="error-message">
                            Generation failed. Please try again.
                        </div>
                    )}
                </div>

                {!!contentAsString && !entry.isCollapsed && (
                    <GeneratedTextArea
                        generatedText={contentAsString}
                        updateGeneratedText={handleUpdateContent}
                    />
                )}
            </div>
        </div>
    )
}

export default SectionItem
