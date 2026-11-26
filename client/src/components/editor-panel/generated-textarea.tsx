import { useEffect, useRef, useState } from 'react'
import { Pencil } from 'lucide-react'

interface GeneratedTextProps {
    generatedText?: string
    updateGeneratedText: (updatedText: string) => Promise<void>
}

const GeneratedTextArea = ({
    generatedText = '',
    updateGeneratedText,
}: GeneratedTextProps) => {
    const [genTextVal, setGenTextVal] = useState(generatedText)
    const [isEditAllowed, setEditAllowed] = useState(false)
    const [isSaving, setSaving] = useState(false)
    const [saveError, setSaveError] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement | null>(null)

    // Keep local state in sync with parent props
    useEffect(() => {
        if (!isEditAllowed) setGenTextVal(generatedText)
    }, [generatedText, isEditAllowed])

    // Auto-resize the textarea based on content
    useEffect(() => {
        const textarea = textareaRef.current
        if (!textarea) return

        textarea.style.height = 'auto'
        textarea.style.height = `${Math.min(
            textarea.scrollHeight,
            parseFloat(getComputedStyle(document.documentElement).fontSize) * 16
        )}px`

        textarea.style.overflowY =
            textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden'
    }, [genTextVal])

    return (
        <div className="gentext-container">
            <div className="gentext-header">
                <p className="generated-text-title"> Generated Text </p>

                {!isEditAllowed && (
                    <button
                        className={`generated-text-edit-button ${isEditAllowed ? 'edit-allowed' : 'edit-disabled'}`}
                        onClick={() => {
                            setEditAllowed((prev) => !prev)
                        }}
                    >
                        <>
                            {!isEditAllowed && (
                                <Pencil className="lucide-button-icon edit-text-icon" />
                            )}
                            <span>
                                {isEditAllowed ? 'Save' : 'Edit With JSON'}{' '}
                            </span>
                        </>
                    </button>
                )}
            </div>

            <div className="gentext-output-card">
                {isEditAllowed && (
                    <div className="json-editor-header">
                        <span>JSON Editor</span>

                        <button
                            className="json-save-button"
                            disabled={isSaving}
                            onClick={async () => {
                                setSaving(true)
                                setSaveError('')
                                try {
                                    await updateGeneratedText(genTextVal)
                                    setEditAllowed(false)
                                } catch {
                                    setSaveError(
                                        'Could not save JSON. Check the JSON and try again.'
                                    )
                                } finally {
                                    setSaving(false)
                                }
                            }}
                        >
                            {isSaving ? 'Saving...' : 'Save'}
                        </button>
                    </div>
                )}

                {saveError && <p role="alert">{saveError}</p>}
                <textarea
                    ref={textareaRef}
                    className="generated-textarea"
                    value={genTextVal}
                    placeholder="Generated text will appear here..."
                    onChange={(event) => {
                        setGenTextVal(event.target.value)
                    }}
                    readOnly={!isEditAllowed || isSaving}
                />
            </div>
        </div>
    )
}
export default GeneratedTextArea
