import React, { useState } from 'react'
import styled, { keyframes } from 'styled-components'
import ToggleGroup from './ToggleGroup'
import ResumePreview from './ResumePreview'

// ── Animations ──────────────────────────────────────────────────────────────

const fadeIn = keyframes`from { opacity: 0; } to { opacity: 1; }`
const slideUp = keyframes`
  from { opacity: 0; transform: scale(0.96) translateY(10px); }
  to   { opacity: 1; transform: scale(1)    translateY(0);    }
`

// ── Overlay & Modal ──────────────────────────────────────────────────────────

const Overlay = styled.div`
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(2px);
    animation: ${fadeIn} 0.18s ease-out;
`

const Modal = styled.div`
    background: #ffffff;
    border-radius: 14px;
    padding: 22px 24px;
    width: 600px;
    max-width: calc(100vw - 32px);
    border: 1px solid #e2e8f0;
    box-shadow: 0 20px 48px -12px rgba(0, 0, 0, 0.22);
    display: flex;
    flex-direction: column;
    gap: 16px;
    animation: ${slideUp} 0.22s ease;
    font-family: 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-height: calc(100vh - 48px);
    overflow-y: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
    &::-webkit-scrollbar {
        display: none;
        width: 0 !important;
        height: 0 !important;
    }
`

const ModalHeader = styled.div`
    display: flex;
    flex-direction: column;
    gap: 3px;
`

const ModalHeaderTitle = styled.h2`
    font-size: 1.25rem;
    font-weight: 700;
    color: #111827;
    margin: 0;
    font-family: 'Lato', sans-serif;
`


// ── Creation Mode Selector ───────────────────────────────────────────────────

const ModeSelector = styled.div`
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
`

const ModeCard = styled.button<{ $active: boolean }>`
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1.5px solid ${({ $active }) => ($active ? '#2646f2' : '#e2e8f0')};
    background: ${({ $active }) => ($active ? '#f0f4ff' : '#ffffff')};
    cursor: pointer;
    text-align: left;
    font-family: 'Lato', sans-serif;
    transition: all 0.16s ease;

    &:hover {
        border-color: ${({ $active }) => ($active ? '#2646f2' : '#cbd5e1')};
        background: ${({ $active }) => ($active ? '#f0f4ff' : '#f8fafc')};
    }
`

const ModeTitle = styled.div<{ $active: boolean }>`
    font-size: 13.5px;
    font-weight: 700;
    color: ${({ $active }) => ($active ? '#2646f2' : '#111827')};
    margin-bottom: 4px;
`

const ModeDescription = styled.div`
    font-size: 11.5px;
    color: #64748b;
    line-height: 1.45;
`

// ── Content Layout ───────────────────────────────────────────────────────────

const ContentLayout = styled.div`
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
`

const FormSection = styled.div`
    flex: 1 1 240px;
    display: flex;
    flex-direction: column;
    gap: 12px;
`

const FieldGroup = styled.div`
    display: flex;
    flex-direction: column;
    gap: 5px;
`

const Label = styled.label`
    font-size: 12px;
    font-weight: 600;
    color: #374151;
    letter-spacing: 0.01em;
`

const TextInput = styled.input`
    border: 1px solid #d1d5db;
    border-radius: 7px;
    padding: 8px 11px;
    font-size: 13px;
    color: #111827;
    outline: none;
    width: 100%;
    font-family: inherit;
    transition: border-color 0.15s;

    &:focus {
        border-color: #2646f2;
    }
    &::placeholder {
        color: #9ca3af;
    }
`

const TextArea = styled.textarea`
    border: 1px solid #d1d5db;
    border-radius: 7px;
    padding: 9px 11px;
    font-size: 12.5px;
    color: #111827;
    outline: none;
    width: 100%;
    min-height: 130px;
    max-height: 240px;
    resize: vertical;
    font-family: 'Fira Code', Menlo, Consolas, Monaco, monospace;
    line-height: 1.5;
    transition: border-color 0.15s;

    scrollbar-width: none;
    -ms-overflow-style: none;
    &::-webkit-scrollbar {
        display: none;
        width: 0 !important;
        height: 0 !important;
    }

    &:focus {
        border-color: #2646f2;
    }
    &::placeholder {
        color: #9ca3af;
        font-family: 'Lato', sans-serif;
    }
`


const ErrorAlert = styled.div`
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
    border-radius: 7px;
    padding: 8px 12px;
    font-size: 12.5px;
    line-height: 1.4;
`

// ── Footer ───────────────────────────────────────────────────────────────────

const Footer = styled.div`
    width: 100%;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 14px;
    border-top: 1px solid #f1f5f9;
`

const CancelButton = styled.button`
    padding: 8px 20px;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    background: #ffffff;
    color: #374151;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s;

    &:hover {
        background: #f9fafb;
    }
`

const CreateButton = styled.button<{ disabled: boolean }>`
    padding: 8px 24px;
    border: none;
    border-radius: 7px;
    background: #2646f2;
    color: #ffffff;
    font-size: 13.5px;
    font-weight: 600;
    font-family: inherit;
    cursor: ${({ disabled }) => (disabled ? 'not-allowed' : 'pointer')};
    opacity: ${({ disabled }) => (disabled ? 0.5 : 1)};
    transition:
        opacity 0.15s,
        background 0.15s;

    &:hover:not(:disabled) {
        background: #1d38cb;
    }
`

// ── Main Component ───────────────────────────────────────────────────────────

interface Props {
    isOpen: boolean
    onClose: () => void
    isSubmitting?: boolean
    onCreate: (prefs: {
        fileName: string
        templateKey: string
        visualThemeKey: string
        pages: number
        configOverride: Record<string, unknown>
        importContent?: string
    }) => void | Promise<void>
}

export default function ResumePreferencesModal({
    isOpen,
    onClose,
    onCreate,
    isSubmitting = false,
}: Props) {
    const [creationMode, setCreationMode] = useState<'blank' | 'import'>('blank')
    const [fileName, setFileName] = useState('')
    const [importContent, setImportContent] = useState('')
    const [resumeType, setResumeType] = useState('iitb')
    const [header, setHeader] = useState('long')
    const [pages, setPages] = useState(2)
    const [localError, setLocalError] = useState<string | null>(null)

    const reset = () => {
        setCreationMode('blank')
        setFileName('')
        setImportContent('')
        setResumeType('iitb')
        setHeader('long')
        setPages(2)
        setLocalError(null)
    }

    const handleClose = () => {
        onClose()
        reset()
    }

    const handleCreate = async () => {
        if (!fileName.trim() || isSubmitting) return
        if (creationMode === 'import' && !importContent.trim()) {
            setLocalError('Please paste your existing resume content before importing.')
            return
        }

        setLocalError(null)
        const templateKey =
            resumeType === 'iitb' ? 'iitb-general' : 'external-standard'
        const visualThemeKey =
            resumeType === 'iitb' ? 'iitb-classic' : 'external-standard'
        const configOverride: Record<string, unknown> =
            resumeType === 'iitb' ? { header_style: header } : {}

        try {
            await onCreate({
                fileName: fileName.trim(),
                templateKey,
                visualThemeKey,
                pages,
                configOverride,
                importContent: creationMode === 'import' ? importContent.trim() : undefined,
            })
            handleClose()
        } catch (err: any) {
            console.error('[ResumePreferencesModal] Error creating resume:', err)
            if (err?.response?.data) {
                console.error('[ResumePreferencesModal] Actual backend error:', err.response.data)
            }
            const data = err?.response?.data
            let msg = ''
            if (typeof data === 'string') {
                msg = data
            } else if (data && typeof data === 'object') {
                msg =
                    data.message ||
                    data.detail ||
                    (typeof data.error === 'string' ? data.error : '') ||
                    Object.values(data).flat().join(' ') ||
                    ''
            }
            if (!msg) {
                msg = err?.message || 'Could not create resume.'
            }
            setLocalError(msg)
        }
    }

    const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
        if (e.target === e.currentTarget && !isSubmitting) handleClose()
    }

    if (!isOpen) return null

    return (
        <Overlay onClick={handleOverlayClick}>
            <Modal
                role="dialog"
                aria-modal="true"
                aria-label="Resume preferences"
            >
                <ModalHeader>
                    <ModalHeaderTitle>Create Resume</ModalHeaderTitle>
                </ModalHeader>

                <ModeSelector>
                    <ModeCard
                        type="button"
                        $active={creationMode === 'blank'}
                        onClick={() => {
                            setCreationMode('blank')
                            setLocalError(null)
                        }}
                        disabled={isSubmitting}
                    >
                        <ModeTitle $active={creationMode === 'blank'}>
                            Start with an Empty Resume
                        </ModeTitle>
                        <ModeDescription>
                            Initialize with blank sections and build your resume manually.
                        </ModeDescription>
                    </ModeCard>

                    <ModeCard
                        type="button"
                        $active={creationMode === 'import'}
                        onClick={() => {
                            setCreationMode('import')
                            setLocalError(null)
                        }}
                        disabled={isSubmitting}
                    >
                        <ModeTitle $active={creationMode === 'import'}>
                            Import Existing Content
                        </ModeTitle>
                        <ModeDescription>
                            Paste existing plain text or LaTeX. AI parser will extract and autopopulate sections.
                        </ModeDescription>
                    </ModeCard>
                </ModeSelector>

                <ContentLayout>
                    <FormSection>
                        <FieldGroup>
                            <Label htmlFor="resume-file-name">File Name</Label>
                            <TextInput
                                id="resume-file-name"
                                type="text"
                                placeholder="e.g. SDE_Resume_2024"
                                value={fileName}
                                onChange={(e) => {
                                    setFileName(e.target.value)
                                    if (localError) setLocalError(null)
                                }}
                                autoFocus
                                disabled={isSubmitting}
                            />
                        </FieldGroup>

                        <FieldGroup>
                            <Label>Type of Resume</Label>
                            <ToggleGroup
                                options={[
                                    { label: 'IITB Template', value: 'iitb' },
                                    { label: 'External', value: 'external' },
                                ]}
                                value={resumeType}
                                onChange={setResumeType}
                            />
                        </FieldGroup>

                        {resumeType === 'iitb' && (
                            <FieldGroup>
                                <Label>Header</Label>
                                <ToggleGroup
                                    options={[
                                        { label: 'Short Header', value: 'short' },
                                        { label: 'Long Header', value: 'long' },
                                    ]}
                                    value={header}
                                    onChange={setHeader}
                                />
                            </FieldGroup>
                        )}

                        <FieldGroup>
                            <Label>No. of pages</Label>
                            <ToggleGroup
                                options={[
                                    { label: '1 Page', value: 1 },
                                    { label: '2 Pages', value: 2 },
                                ]}
                                value={pages}
                                onChange={setPages}
                            />
                        </FieldGroup>
                    </FormSection>

                    <ResumePreview
                        resumeType={resumeType}
                        header={header}
                        pages={pages}
                    />
                </ContentLayout>

                {creationMode === 'import' && (
                    <FieldGroup>
                        <Label htmlFor="resume-import-content">
                            Paste Resume Content (Plain Text or LaTeX)
                        </Label>
                        <TextArea
                            id="resume-import-content"
                            placeholder="Paste your plain text or LaTeX resume here... e.g. \begin{itemize} ... or plain text sections"
                            value={importContent}
                            onChange={(e) => {
                                setImportContent(e.target.value)
                                if (localError) setLocalError(null)
                            }}
                            disabled={isSubmitting}
                        />
                    </FieldGroup>
                )}

                {localError && <ErrorAlert>{localError}</ErrorAlert>}

                <Footer>
                    <CancelButton onClick={handleClose} disabled={isSubmitting}>
                        Cancel
                    </CancelButton>
                    <CreateButton
                        onClick={handleCreate}
                        disabled={
                            !fileName.trim() ||
                            (creationMode === 'import' && !importContent.trim()) ||
                            isSubmitting
                        }
                    >
                        {isSubmitting
                            ? creationMode === 'import'
                                ? 'Importing & Parsing…'
                                : 'Creating…'
                            : creationMode === 'import'
                              ? 'Import & Create Resume'
                              : 'Create Resume'}
                    </CreateButton>
                </Footer>
            </Modal>
        </Overlay>
    )
}

