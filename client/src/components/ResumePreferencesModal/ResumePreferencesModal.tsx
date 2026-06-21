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
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    animation: ${fadeIn} 0.2s ease;
`

const Modal = styled.div`
    background: #fff;
    border-radius: 12px;
    padding: 20px;
    width: 520px;
    max-width: calc(100vw - 32px);
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.3);
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    animation: ${slideUp} 0.22s ease;
`

// ── Form Section ─────────────────────────────────────────────────────────────

const FormSection = styled.div`
    flex: 1 1 200px;
    display: flex;
    flex-direction: column;
    gap: 14px;
`

const FieldGroup = styled.div`
    display: flex;
    flex-direction: column;
    gap: 5px;
`

const Label = styled.label`
    font-size: 11px;
    font-weight: 600;
    color: #374151;
    letter-spacing: 0.01em;
`

const TextInput = styled.input`
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    color: #111827;
    outline: none;
    width: 100%;
    font-family: inherit;
    transition: border-color 0.15s;

    &:focus {
        border-color: #2563eb;
    }
    &::placeholder {
        color: #9ca3af;
    }
`

// ── Footer ───────────────────────────────────────────────────────────────────

const Footer = styled.div`
    width: 100%;
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid #f1f5f9;
`

const CancelButton = styled.button`
    padding: 7px 18px;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    background: #fff;
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
    padding: 7px 22px;
    border: none;
    border-radius: 7px;
    background: #2563eb;
    color: #fff;
    font-size: 13px;
    font-weight: 500;
    font-family: inherit;
    cursor: ${({ disabled }) => (disabled ? 'not-allowed' : 'pointer')};
    opacity: ${({ disabled }) => (disabled ? 0.45 : 1)};
    transition:
        opacity 0.15s,
        background 0.15s;

    &:hover:not(:disabled) {
        background: #1d4ed8;
    }
`

// ── Main Component ───────────────────────────────────────────────────────────

interface Props {
    isOpen: boolean
    onClose: () => void
    isSubmitting?: boolean
    onCreate: (prefs: {
        fileName: string
        resumeType: string
        header: string
        pages: number
    }) => void | Promise<void>
}

export default function ResumePreferencesModal({
    isOpen,
    onClose,
    onCreate,
    isSubmitting = false,
}: Props) {
    const [fileName, setFileName] = useState('')
    const [resumeType, setResumeType] = useState('iitb')
    const [header, setHeader] = useState('long')
    const [pages, setPages] = useState(2)

    const reset = () => {
        setFileName('')
        setResumeType('iitb')
        setHeader('long')
        setPages(2)
    }

    const handleClose = () => {
        onClose()
        reset()
    }

    const handleCreate = async () => {
        if (!fileName.trim() || isSubmitting) return
        await onCreate({
            fileName: fileName.trim(),
            resumeType,
            header,
            pages,
        })
        handleClose()
    }

    const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
        if (e.target === e.currentTarget) handleClose()
    }

    if (!isOpen) return null

    return (
        <Overlay onClick={handleOverlayClick}>
            <Modal
                role="dialog"
                aria-modal="true"
                aria-label="Resume preferences"
            >
                <FormSection>
                    <FieldGroup>
                        <Label htmlFor="resume-file-name">File Name</Label>
                        <TextInput
                            id="resume-file-name"
                            type="text"
                            placeholder="Type here"
                            value={fileName}
                            onChange={(e) => setFileName(e.target.value)}
                            autoFocus
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

                <Footer>
                    <CancelButton onClick={handleClose}>Cancel</CancelButton>
                    <CreateButton
                        onClick={handleCreate}
                        disabled={!fileName.trim() || isSubmitting}
                    >
                        {isSubmitting ? 'Creating…' : 'Create'}
                    </CreateButton>
                </Footer>
            </Modal>
        </Overlay>
    )
}
