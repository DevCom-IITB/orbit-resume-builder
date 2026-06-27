import { useEffect, useRef, useState } from 'react'
import type { PointDensity } from '../../types/editor-panel/pointdensity'
import { createPortal } from 'react-dom'

interface ItemTextAreaProps {
    desc: string
    lastGeneratedNormalized: string
    updateDesc: (updatedDesc: string) => void
    // FIX: Add density to the accepted arguments!
    onGenerateClicked: (
        textVal: string,
        density: PointDensity,
        fitToLine: boolean
    ) => void
    generateStatus: 'loading' | 'success' | 'error'
    generateButtonLabel: string
}

const ItemTextArea = ({
    desc = '',
    lastGeneratedNormalized,
    updateDesc,
    onGenerateClicked,
    generateStatus,
    generateButtonLabel,
}: ItemTextAreaProps) => {
    const [textVal, setTextVal] = useState(desc)

    const normalizeText = (text: string) => text.replace(/\s+/g, ' ').trim()

    const hasMeaningfulChanges =
        normalizeText(textVal) !== lastGeneratedNormalized

    const timeoutRef = useRef<number | null>(null)

    const textareaRef = useRef<HTMLTextAreaElement | null>(null)

    // The density selector slider was removed from the UI; density is fixed.
    const density: PointDensity = 'concise'

    const [isFitToLineEnabled, setFitToLineEnabled] = useState(true)

    const [showFitToLineModal, setShowFitToLineModal] = useState(false)

    useEffect(() => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current)

        timeoutRef.current = setTimeout(() => {
            updateDesc(textVal)
        }, 2000)

        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current)
        }
    }, [textVal, updateDesc])

    useEffect(() => {
        setTextVal(desc)
    }, [desc])

    useEffect(() => {
        const textarea = textareaRef.current

        if (!textarea) return

        textarea.style.height = 'auto'

        textarea.style.height = `${Math.min(
            textarea.scrollHeight,
            parseFloat(getComputedStyle(document.documentElement).fontSize) * 12
        )}px`

        textarea.style.overflowY =
            textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden'
    }, [textVal])

    return (
        <div className="item-textarea-container">
            <div
                className="text-area-div"
                style={{
                    width: '100%',
                    minWidth: 0,
                }}
            >
                <textarea
                    ref={textareaRef}
                    className="item-description-textarea"
                    value={textVal}
                    placeholder="Describe your experience..."
                    onChange={(event) => {
                        setTextVal(event.target.value)
                    }}
                />
            </div>

            <div className="qol-buttons">
                <button
                    className={`fit-to-line-button ${
                        isFitToLineEnabled ? 'enabled' : 'disabled'
                    }`}
                    onClick={() => {
                        if (isFitToLineEnabled) {
                            setShowFitToLineModal(true)
                            return
                        }

                        setFitToLineEnabled(true)
                    }}
                >
                    Fit To Line
                </button>

                <div className="generate-button-div">
                    <button
                        className={`generate-text-button ${
                            !hasMeaningfulChanges &&
                            generateButtonLabel === 'Generate'
                                ? 'generated-state'
                                : ''
                        }`}
                        disabled={
                            generateStatus === 'loading' ||
                            (!hasMeaningfulChanges &&
                                generateButtonLabel === 'Generate')
                        }
                        onClick={() => {
                            const cleanedText = textVal.replace(
                                /\n\s*\n+/g,
                                '\n\n'
                            )
                            onGenerateClicked(
                                cleanedText,
                                density,
                                isFitToLineEnabled
                            )
                        }}
                    >
                        {generateButtonLabel}
                        {generateStatus === 'loading' && (
                            <span
                                className="generate-spinner"
                                aria-hidden="true"
                            />
                        )}
                    </button>
                </div>
            </div>
            {showFitToLineModal &&
                createPortal(
                    <div className="fit-to-line-modal-overlay">
                        <div className="fit-to-line-modal">
                            <div className="fit-to-line-modal-content">
                                <div className="fit-to-line-modal-message">
                                    <h3>
                                        Editing the text would lead to uneven
                                        white spaces
                                    </h3>
                                </div>
                                <div className="fit-to-line-modal-icon" />
                            </div>

                            <div className="fit-to-line-modal-actions">
                                <button
                                    className="fit-to-line-cancel"
                                    onClick={() => {
                                        setShowFitToLineModal(false)
                                    }}
                                >
                                    Cancel
                                </button>

                                <button
                                    className="fit-to-line-confirm"
                                    onClick={() => {
                                        setFitToLineEnabled(false)
                                        setShowFitToLineModal(false)
                                    }}
                                >
                                    Continue anyway
                                </button>
                            </div>
                        </div>
                    </div>,
                    document.body
                )}
        </div>
    )
}
export default ItemTextArea
