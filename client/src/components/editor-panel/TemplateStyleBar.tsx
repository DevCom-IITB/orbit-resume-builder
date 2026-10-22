import React, { useEffect, useRef, useState } from 'react'
import styled, { keyframes } from 'styled-components'
import { createPortal } from 'react-dom'
import { AlertCircle, Check, Loader2, X } from 'lucide-react'
import axios from 'axios'
import type {
    FontOption,
    Resume,
    ResumeSection,
    ResumeTemplate,
    StyleOptions,
    SwitchPlan,
} from '../../types/resume'
import {
    base64ToPdfBlobUrl,
    getResume,
    getStyle,
    listTemplates,
    patchStyle,
    switchTemplate,
} from '../../lib/api'
import SpacingControl from './SpacingControl'

// ── Animations ──────────────────────────────────────────────────────────────

const fadeIn = keyframes`from { opacity: 0; } to { opacity: 1; }`
const slideUp = keyframes`
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to   { opacity: 1; transform: scale(1) translateY(0); }
`

// ── Styled Components ────────────────────────────────────────────────────────

const BarContainer = styled.div<{ $disabled?: boolean }>`
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    opacity: ${({ $disabled }) => ($disabled ? 0.6 : 1)};
    pointer-events: ${({ $disabled }) => ($disabled ? 'none' : 'auto')};
    transition: opacity 0.15s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
`

const Row = styled.div`
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
`

const ControlGroup = styled.div`
    flex: 1 1 120px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
`

const Label = styled.label`
    font-size: 11px;
    font-weight: 700;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    gap: 4px;
`

const Select = styled.select`
    height: 32px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0 8px;
    font-size: 13px;
    color: #111827;
    background-color: #ffffff;
    font-family: inherit;
    outline: none;
    cursor: pointer;
    width: 100%;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;

    &:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
    }
    &:disabled {
        cursor: not-allowed;
        background-color: #f9fafb;
    }
`

const AccentRow = styled.div`
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 2px;
`

const SwatchButton = styled.button<{ $color: string; $selected: boolean }>`
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background-color: ${({ $color }) => $color};
    border: 2px solid ${({ $selected }) => ($selected ? '#2563eb' : '#ffffff')};
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.2);
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    transition: transform 0.12s ease, box-shadow 0.12s ease;

    &:hover {
        transform: scale(1.15);
    }
    &:focus-visible {
        outline: 2px solid #2563eb;
        outline-offset: 2px;
    }
`

const NoticeBanner = styled.div<{ $type: 'warning' | 'error' | 'info' }>`
    background-color: ${({ $type }) =>
        $type === 'error' ? '#fef2f2' : $type === 'warning' ? '#fffbeb' : '#f0fdf4'};
    border: 1px solid
        ${({ $type }) =>
            $type === 'error' ? '#fecaca' : $type === 'warning' ? '#fde68a' : '#bbf7d0'};
    color: ${({ $type }) =>
        $type === 'error' ? '#991b1b' : $type === 'warning' ? '#92400e' : '#166534'};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    animation: ${fadeIn} 0.2s ease;
`

const ModalOverlay = styled.div`
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
`

const ModalCard = styled.div`
    background: #ffffff;
    border-radius: 12px;
    padding: 22px;
    width: 440px;
    max-width: calc(100vw - 32px);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
    animation: ${slideUp} 0.2s ease;
    display: flex;
    flex-direction: column;
    gap: 14px;
`

const ModalTitle = styled.h3`
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #111827;
`

const ModalText = styled.p`
    margin: 0;
    font-size: 13px;
    color: #4b5563;
    line-height: 1.45;
`

const WarningList = styled.ul`
    margin: 6px 0 0 0;
    padding-left: 20px;
    font-size: 12px;
    color: #92400e;
    line-height: 1.4;
`

const ModalFooter = styled.div`
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 8px;
    padding-top: 12px;
    border-top: 1px solid #f3f4f6;
`

const SecondaryButton = styled.button`
    padding: 7px 16px;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    background: #ffffff;
    color: #374151;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s ease;

    &:hover {
        background: #f9fafb;
    }
`

const PrimaryButton = styled.button`
    padding: 7px 18px;
    border: none;
    border-radius: 7px;
    background: #2563eb;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.15s ease;

    &:hover {
        background: #1d4ed8;
    }
`

function getErrorMessage(err: unknown, fallback: string): string {
    if (axios.isAxiosError(err) && err.response?.data) {
        const d = err.response.data
        if (typeof d === 'string') return d
        if (d.error && typeof d.error === 'string') return d.error
        if (d.font && typeof d.font === 'string') return d.font
        if (d.accent && typeof d.accent === 'string') return d.accent
        return JSON.stringify(d)
    }
    if (err instanceof Error) return err.message
    return fallback
}

// ── Props Interface ──────────────────────────────────────────────────────────

const TEMPLATE_DEFAULTS: Record<
    string,
    { font: string; accent: string; lineSpacing: string; wordSpacing: string }
> = {
    'iitb-general': { font: 'lmodern', accent: '#4B41C8', lineSpacing: '1.00', wordSpacing: '1.00' },
    'external-standard': { font: 'lmodern', accent: '#4B41C8', lineSpacing: '1.00', wordSpacing: '1.00' },
    'awesome-cv-general': { font: 'sourcesans', accent: '#DC3522', lineSpacing: '1.00', wordSpacing: '1.00' },
    'jake-general': { font: 'lmodern', accent: '#000000', lineSpacing: '1.00', wordSpacing: '1.00' },
}

const DEFAULT_SPACING_OPTIONS = ['0.90', '0.95', '1.00', '1.05', '1.10', '1.15', '1.20']

export interface TemplateStyleBarProps {
    resume: Resume
    onPdfUpdate: (pdfBlobUrl: string, latex: string) => void
    onResumeUpdate: (updatedResume: Resume) => void
    onSectionsChange: (newSections: ResumeSection[]) => void
    onRenderStatusChange: (status: 'idle' | 'loading' | 'success' | 'error') => void
}

export default function TemplateStyleBar({
    resume,
    onPdfUpdate,
    onResumeUpdate,
    onSectionsChange,
    onRenderStatusChange,
}: TemplateStyleBarProps) {
    const isMountedRef = useRef(true)
    useEffect(() => {
        isMountedRef.current = true
        return () => {
            isMountedRef.current = false
        }
    }, [])

    const [templates, setTemplates] = useState<ResumeTemplate[]>([])
    const [initialLoading, setInitialLoading] = useState(true)
    const [loadError, setLoadError] = useState<string | null>(null)

    const initialTmplKey =
        resume.template?.key === 'external-standard'
            ? 'iitb-general'
            : resume.template?.key || 'iitb-general'
    const initialDefaults = TEMPLATE_DEFAULTS[initialTmplKey] || {
        font: 'lmodern',
        accent: '#4B41C8',
        lineSpacing: '1.00',
        wordSpacing: '1.00',
    }

    const [currentTemplateKey, setCurrentTemplateKey] = useState(initialTmplKey)
    const [currentFont, setCurrentFont] = useState(
        resume.template?.fontDefault || initialDefaults.font
    )
    const [currentAccent, setCurrentAccent] = useState(
        resume.template?.accentDefault || initialDefaults.accent
    )
    const [currentLineSpacing, setCurrentLineSpacing] = useState(
        resume.template?.lineSpacingDefault || initialDefaults.lineSpacing
    )
    const [currentWordSpacing, setCurrentWordSpacing] = useState(
        resume.template?.wordSpacingDefault || initialDefaults.wordSpacing
    )
    const prevPageCountRef = useRef<number>(resume.pages || 1)

    const [styleOptions, setStyleOptions] = useState<StyleOptions>({
        fonts: [],
        fontDefault: resume.template?.fontDefault || initialDefaults.font,
        accents: [],
        accentDefault: resume.template?.accentDefault || initialDefaults.accent,
        lineSpacings: DEFAULT_SPACING_OPTIONS,
        lineSpacingDefault: '1.00',
        wordSpacings: DEFAULT_SPACING_OPTIONS,
        wordSpacingDefault: '1.00',
    })

    const [isSwitching, setIsSwitching] = useState(false)
    const [bannerNotice, setBannerNotice] = useState<{
        type: 'warning' | 'error' | 'info'
        text: string
    } | null>(null)

    const [confirmModal, setConfirmModal] = useState<{
        pendingTemplateKey: string
        prevTemplateKey: string
        prevFont: string
        prevAccent: string
        prevLineSpacing: string
        prevWordSpacing: string
        plan: SwitchPlan
    } | null>(null)

    // Debounce, cancel, sequence refs
    const debounceTimerRef = useRef<number | null>(null)
    const abortControllerRef = useRef<AbortController | null>(null)
    const requestSeqRef = useRef<number>(0)

    // Load templates and initial style
    useEffect(() => {
        let active = true
        setInitialLoading(true)
        setLoadError(null)

        Promise.all([listTemplates(), getStyle(resume.id)])
            .then(([tmpls, styleData]) => {
                if (!active) return
                // Filter out 'external-standard' as it is identical to IITB and redundant in the toggle
                const filteredTemplates = tmpls.filter(
                    (t) => t.key !== 'external-standard' && t.displayName.toLowerCase() !== 'external'
                )
                setTemplates(filteredTemplates)

                const effectiveKey =
                    resume.template.key === 'external-standard'
                        ? 'iitb-general'
                        : resume.template.key
                setCurrentTemplateKey(effectiveKey)

                const activeTmpl = filteredTemplates.find((t) => t.key === effectiveKey)
                const activeDefaults =
                    TEMPLATE_DEFAULTS[effectiveKey] || {
                        font: 'lmodern',
                        accent: '#4B41C8',
                        lineSpacing: '1.00',
                        wordSpacing: '1.00',
                    }
                setCurrentFont(
                    styleData.style?.font ||
                    activeTmpl?.fontDefault ||
                    activeDefaults.font
                )
                setCurrentAccent(
                    styleData.style?.accent ||
                    activeTmpl?.accentDefault ||
                    activeDefaults.accent
                )
                setCurrentLineSpacing(
                    styleData.style?.lineSpacing ||
                    styleData.style?.line_spacing ||
                    activeTmpl?.lineSpacingDefault ||
                    activeDefaults.lineSpacing
                )
                setCurrentWordSpacing(
                    styleData.style?.wordSpacing ||
                    styleData.style?.word_spacing ||
                    activeTmpl?.wordSpacingDefault ||
                    activeDefaults.wordSpacing
                )
                setStyleOptions(styleData.options)
                setInitialLoading(false)
            })
            .catch((err) => {
                if (!active) return
                console.error('[TemplateStyleBar] Failed to load template/style options:', err)
                setLoadError('Unable to load styling options.')
                setInitialLoading(false)
            })

        return () => {
            active = false
        }
    }, [resume.id, resume.template.key])

    // Cleanup timers and abort controllers on unmount
    useEffect(() => {
        return () => {
            if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
            if (abortControllerRef.current) abortControllerRef.current.abort()
        }
    }, [])

    // Find current active template definition
    const activeTemplate = templates.find((t) => t.key === currentTemplateKey)

    const availableFonts: FontOption[] =
        activeTemplate?.fonts && activeTemplate.fonts.length > 0
            ? activeTemplate.fonts
            : styleOptions.fonts

    const availableAccents: string[] =
        activeTemplate?.accents && activeTemplate.accents.length > 0
            ? activeTemplate.accents
            : styleOptions.accents

    const availableLineSpacings: string[] =
        activeTemplate?.lineSpacings && activeTemplate.lineSpacings.length > 0
            ? activeTemplate.lineSpacings
            : styleOptions.lineSpacings && styleOptions.lineSpacings.length > 0
            ? styleOptions.lineSpacings
            : DEFAULT_SPACING_OPTIONS

    const lineSpacingDefault: string =
        activeTemplate?.lineSpacingDefault ||
        styleOptions.lineSpacingDefault ||
        '1.00'

    const availableWordSpacings: string[] =
        activeTemplate?.wordSpacings && activeTemplate.wordSpacings.length > 0
            ? activeTemplate.wordSpacings
            : styleOptions.wordSpacings && styleOptions.wordSpacings.length > 0
            ? styleOptions.wordSpacings
            : DEFAULT_SPACING_OPTIONS

    const wordSpacingDefault: string =
        activeTemplate?.wordSpacingDefault ||
        styleOptions.wordSpacingDefault ||
        '1.00'

    // ── Style Change Dispatcher (Debounced 300ms + AbortController + Seq) ──────

    const triggerStylePatch = (
        newFont: string,
        newAccent: string,
        newLineSpacing: string,
        newWordSpacing: string
    ) => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current)
        }

        const prevFont = currentFont
        const prevAccent = currentAccent
        const prevLineSpacing = currentLineSpacing
        const prevWordSpacing = currentWordSpacing

        debounceTimerRef.current = window.setTimeout(async () => {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort()
            }
            const controller = new AbortController()
            abortControllerRef.current = controller
            const seq = ++requestSeqRef.current

            onRenderStatusChange('loading')
            try {
                const res = await patchStyle(
                    resume.id,
                    {
                        font: newFont,
                        accent: newAccent,
                        lineSpacing: newLineSpacing,
                        wordSpacing: newWordSpacing,
                    },
                    controller.signal
                )
                if (!isMountedRef.current || seq !== requestSeqRef.current) return

                if (res.pdf) {
                    const blobUrl = base64ToPdfBlobUrl(res.pdf)
                    onPdfUpdate(blobUrl, res.latex ?? '')
                    onRenderStatusChange('success')
                } else {
                    onRenderStatusChange('idle')
                }

                if (res.style) {
                    if (res.style.font) setCurrentFont(res.style.font)
                    if (res.style.accent) setCurrentAccent(res.style.accent)
                    if (res.style.lineSpacing || res.style.line_spacing) {
                        setCurrentLineSpacing(res.style.lineSpacing || res.style.line_spacing || '1.00')
                    }
                    if (res.style.wordSpacing || res.style.word_spacing) {
                        setCurrentWordSpacing(res.style.wordSpacing || res.style.word_spacing || '1.00')
                    }
                }

                if (res.pages && prevPageCountRef.current && res.pages > prevPageCountRef.current) {
                    setBannerNotice({
                        type: 'info',
                        text: `Resume is now ${res.pages} pages.`,
                    })
                }
                if (res.pages) {
                    prevPageCountRef.current = res.pages
                }
            } catch (err: unknown) {
                if (
                    (err as { name?: string })?.name === 'CanceledError' ||
                    (err as { name?: string })?.name === 'AbortError' ||
                    axios.isCancel(err)
                ) {
                    return
                }
                if (!isMountedRef.current || seq !== requestSeqRef.current) return

                // Revert control values on error
                setCurrentFont(prevFont)
                setCurrentAccent(prevAccent)
                setCurrentLineSpacing(prevLineSpacing)
                setCurrentWordSpacing(prevWordSpacing)
                onRenderStatusChange('idle')

                const msg = getErrorMessage(err, 'Failed to apply style changes.')
                setBannerNotice({
                    type: 'error',
                    text: msg,
                })
            }
        }, 300)
    }

    const handleFontChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        if (isSwitching) return
        const nextFont = e.target.value
        if (nextFont === currentFont) return
        setCurrentFont(nextFont)
        triggerStylePatch(nextFont, currentAccent, currentLineSpacing, currentWordSpacing)
    }

    const handleAccentSelect = (hex: string) => {
        if (isSwitching) return
        const upperHex = hex.toUpperCase()
        if (upperHex === currentAccent.toUpperCase()) return
        setCurrentAccent(upperHex)
        triggerStylePatch(currentFont, upperHex, currentLineSpacing, currentWordSpacing)
    }

    const handleLineSpacingChange = (val: string) => {
        if (isSwitching || val === currentLineSpacing) return
        setCurrentLineSpacing(val)
        triggerStylePatch(currentFont, currentAccent, val, currentWordSpacing)
    }

    const handleWordSpacingChange = (val: string) => {
        if (isSwitching || val === currentWordSpacing) return
        setCurrentWordSpacing(val)
        triggerStylePatch(currentFont, currentAccent, currentLineSpacing, val)
    }

    // ── Template Switch Logic ──────────────────────────────────────────────────

    const executeRealSwitch = async (
        targetTemplateKey: string,
        rollbackFont?: string,
        rollbackAccent?: string,
        rollbackLineSpacing?: string,
        rollbackWordSpacing?: string
    ) => {
        setIsSwitching(true)
        onRenderStatusChange('loading')

        try {
            const res = await switchTemplate(resume.id, {
                templateKey: targetTemplateKey,
                dryRun: false,
            })

            if (!isMountedRef.current) return

            if ('changed' in res) {
                setCurrentTemplateKey(res.template.key)
                setCurrentFont(res.style.font)
                setCurrentAccent(res.style.accent)
                setCurrentLineSpacing(res.style.lineSpacing || res.style.line_spacing || '1.00')
                setCurrentWordSpacing(res.style.wordSpacing || res.style.word_spacing || '1.00')
                setStyleOptions(res.options)

                // Fetch full resume state to ensure database UUIDs, entries, and options align
                const freshResume = await getResume(resume.id)
                onResumeUpdate(freshResume)
                onSectionsChange(freshResume.sections)

                if (res.pdf) {
                    const blobUrl = base64ToPdfBlobUrl(res.pdf)
                    onPdfUpdate(blobUrl, res.latex ?? '')
                    onRenderStatusChange('success')
                } else {
                    onRenderStatusChange('idle')
                }

                if (res.pages && prevPageCountRef.current && res.pages > prevPageCountRef.current) {
                    setBannerNotice({
                        type: 'info',
                        text: `Resume is now ${res.pages} pages.`,
                    })
                } else if (res.warnings && res.warnings.length > 0) {
                    setBannerNotice({
                        type: 'warning',
                        text: res.warnings.join(' • '),
                    })
                } else {
                    setBannerNotice(null)
                }

                if (res.pages) {
                    prevPageCountRef.current = res.pages
                }
            }
        } catch (err: unknown) {
            if (!isMountedRef.current) return
            onRenderStatusChange('idle')
            setCurrentTemplateKey(resume.template.key)
            if (rollbackFont) setCurrentFont(rollbackFont)
            if (rollbackAccent) setCurrentAccent(rollbackAccent)
            if (rollbackLineSpacing) setCurrentLineSpacing(rollbackLineSpacing)
            if (rollbackWordSpacing) setCurrentWordSpacing(rollbackWordSpacing)
            const msg = getErrorMessage(
                err,
                'LaTeX compilation or template switch failed. Reverted to previous template.'
            )
            setBannerNotice({
                type: 'error',
                text: msg,
            })
        } finally {
            if (isMountedRef.current) {
                setIsSwitching(false)
            }
        }
    }

    const handleTemplateSelectChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
        if (isSwitching) return
        const targetTemplateKey = e.target.value
        if (targetTemplateKey === currentTemplateKey) return

        const prevTemplateKey = currentTemplateKey
        const prevFont = currentFont
        const prevAccent = currentAccent
        const prevLineSpacing = currentLineSpacing
        const prevWordSpacing = currentWordSpacing

        const targetTmpl = templates.find((t) => t.key === targetTemplateKey)
        const targetDefaults = TEMPLATE_DEFAULTS[targetTemplateKey] || {
            font: 'lmodern',
            accent: '#4B41C8',
            lineSpacing: '1.00',
            wordSpacing: '1.00',
        }
        const targetDefaultFont = targetTmpl?.fontDefault || targetDefaults.font
        const targetDefaultAccent = targetTmpl?.accentDefault || targetDefaults.accent
        const targetDefaultLineSpacing = targetTmpl?.lineSpacingDefault || targetDefaults.lineSpacing
        const targetDefaultWordSpacing = targetTmpl?.wordSpacingDefault || targetDefaults.wordSpacing

        setCurrentTemplateKey(targetTemplateKey)
        setCurrentFont(targetDefaultFont)
        setCurrentAccent(targetDefaultAccent)
        setCurrentLineSpacing(targetDefaultLineSpacing)
        setCurrentWordSpacing(targetDefaultWordSpacing)
        setIsSwitching(true)

        try {
            const dryRes = await switchTemplate(resume.id, {
                templateKey: targetTemplateKey,
                dryRun: true,
            })

            if (!isMountedRef.current) return

            if ('dryRun' in dryRes) {
                const hasHiddenData = dryRes.plan.willHide.length > 0
                const hasStyleReset = dryRes.plan.styleReset.length > 0

                if (hasHiddenData || hasStyleReset) {
                    setIsSwitching(false)
                    setConfirmModal({
                        pendingTemplateKey: targetTemplateKey,
                        prevTemplateKey: prevTemplateKey,
                        prevFont: prevFont,
                        prevAccent: prevAccent,
                        prevLineSpacing: prevLineSpacing,
                        prevWordSpacing: prevWordSpacing,
                        plan: dryRes.plan,
                    })
                    return
                }
            }

            // Nothing lost or reset, proceed directly
            await executeRealSwitch(targetTemplateKey, prevFont, prevAccent, prevLineSpacing, prevWordSpacing)
        } catch (err: unknown) {
            if (!isMountedRef.current) return
            setIsSwitching(false)
            setCurrentTemplateKey(prevTemplateKey)
            setCurrentFont(prevFont)
            setCurrentAccent(prevAccent)
            setCurrentLineSpacing(prevLineSpacing)
            setCurrentWordSpacing(prevWordSpacing)
            const msg = getErrorMessage(err, 'Failed to inspect template switch.')
            setBannerNotice({
                type: 'error',
                text: msg,
            })
        }
    }

    const handleCancelModal = () => {
        if (confirmModal) {
            setCurrentTemplateKey(confirmModal.prevTemplateKey)
            setCurrentFont(confirmModal.prevFont)
            setCurrentAccent(confirmModal.prevAccent)
            setCurrentLineSpacing(confirmModal.prevLineSpacing)
            setCurrentWordSpacing(confirmModal.prevWordSpacing)
        }
        setConfirmModal(null)
    }

    const handleConfirmModal = () => {
        if (confirmModal) {
            const keyToSwitch = confirmModal.pendingTemplateKey
            const prevFont = confirmModal.prevFont
            const prevAccent = confirmModal.prevAccent
            const prevLineSpacing = confirmModal.prevLineSpacing
            const prevWordSpacing = confirmModal.prevWordSpacing
            setConfirmModal(null)
            executeRealSwitch(keyToSwitch, prevFont, prevAccent, prevLineSpacing, prevWordSpacing)
        }
    }

    if (loadError) {
        return (
            <BarContainer>
                <NoticeBanner $type="error">
                    <span>{loadError}</span>
                </NoticeBanner>
            </BarContainer>
        )
    }

    return (
        <BarContainer $disabled={initialLoading}>
            {bannerNotice && (
                <NoticeBanner $type={bannerNotice.type}>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <AlertCircle size={14} style={{ flexShrink: 0 }} />
                        <span>{bannerNotice.text}</span>
                    </div>
                    <button
                        onClick={() => setBannerNotice(null)}
                        style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            padding: 0,
                            color: 'inherit',
                        }}
                        aria-label="Dismiss notice"
                    >
                        <X size={13} />
                    </button>
                </NoticeBanner>
            )}

            <Row>
                <ControlGroup>
                    <Label htmlFor="template-selector">
                        Template
                        {isSwitching && <Loader2 size={12} className="lucide-button-icon" style={{ animation: 'spin 1s linear infinite' }} />}
                    </Label>
                    <Select
                        id="template-selector"
                        value={currentTemplateKey}
                        onChange={handleTemplateSelectChange}
                        disabled={initialLoading || isSwitching}
                        aria-label="Template selection"
                    >
                        {templates.map((t) => (
                            <option key={t.key} value={t.key}>
                                {t.displayName}
                            </option>
                        ))}
                    </Select>
                </ControlGroup>

                <ControlGroup>
                    <Label htmlFor="font-selector">Font</Label>
                    <Select
                        id="font-selector"
                        value={currentFont}
                        onChange={handleFontChange}
                        disabled={initialLoading || isSwitching}
                        aria-label="Font selection"
                    >
                        {availableFonts.map((f) => (
                            <option key={f.key} value={f.key}>
                                {f.label}
                            </option>
                        ))}
                    </Select>
                </ControlGroup>
            </Row>

            <div>
                <Label style={{ marginBottom: '4px' }}>Accent Color</Label>
                <AccentRow role="radiogroup" aria-label="Accent color selection">
                    {availableAccents.map((accentHex) => {
                        const isSelected =
                            currentAccent.toUpperCase() === accentHex.toUpperCase()
                        return (
                            <SwatchButton
                                key={accentHex}
                                $color={accentHex}
                                $selected={isSelected}
                                onClick={() => handleAccentSelect(accentHex)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault()
                                        handleAccentSelect(accentHex)
                                    }
                                }}
                                role="radio"
                                aria-checked={isSelected}
                                aria-label={accentHex}
                                title={accentHex}
                                tabIndex={0}
                                disabled={initialLoading || isSwitching}
                            >
                                {isSelected && (
                                    <Check
                                        size={12}
                                        color="#ffffff"
                                        strokeWidth={3}
                                        style={{ filter: 'drop-shadow(0 1px 1px rgba(0,0,0,0.5))' }}
                                    />
                                )}
                            </SwatchButton>
                        )
                    })}
                </AccentRow>
            </div>

            <Row>
                <SpacingControl
                    label="Line Spacing"
                    value={currentLineSpacing}
                    options={availableLineSpacings}
                    defaultValue={lineSpacingDefault}
                    onChange={handleLineSpacingChange}
                    disabled={initialLoading || isSwitching}
                />
                <SpacingControl
                    label="Word Spacing"
                    value={currentWordSpacing}
                    options={availableWordSpacings}
                    defaultValue={wordSpacingDefault}
                    onChange={handleWordSpacingChange}
                    disabled={initialLoading || isSwitching}
                />
            </Row>

            {confirmModal &&
                createPortal(
                    <ModalOverlay
                        onClick={(e) => {
                            if (e.target === e.currentTarget) handleCancelModal()
                        }}
                    >
                        <ModalCard role="dialog" aria-modal="true" aria-labelledby="confirm-switch-title">
                            <ModalTitle id="confirm-switch-title">Confirm Template Switch</ModalTitle>
                            <ModalText>
                                Switching to this template will adjust your resume sections and layout:
                            </ModalText>

                            {confirmModal.plan.willHide.length > 0 && (
                                <div>
                                    <ModalText style={{ fontWeight: 600, color: '#92400e' }}>
                                        The following sections have content that is not displayed in the new template and will be hidden:
                                    </ModalText>
                                    <WarningList>
                                        {confirmModal.plan.willHide.map((secKey) => (
                                            <li key={secKey}>
                                                <strong>{secKey.replace(/_/g, ' ')}</strong>
                                            </li>
                                        ))}
                                    </WarningList>
                                    <ModalText style={{ fontSize: '11px', marginTop: '4px', color: '#6b7280' }}>
                                        Your content is safe and will be restored if you switch back.
                                    </ModalText>
                                </div>
                            )}

                            {confirmModal.plan.styleReset.length > 0 && (
                                <div style={{ marginTop: '4px' }}>
                                    <ModalText style={{ fontWeight: 600, color: '#374151' }}>
                                        Style resets:
                                    </ModalText>
                                    <WarningList>
                                        {confirmModal.plan.styleReset.map((prop) => (
                                            <li key={prop}>
                                                {prop === 'font'
                                                    ? 'Font will reset to the template default'
                                                    : prop === 'accent'
                                                    ? 'Accent colour will reset to the template default'
                                                    : prop === 'line_spacing'
                                                    ? 'Line spacing will reset to the template default'
                                                    : prop === 'word_spacing'
                                                    ? 'Word spacing will reset to the template default'
                                                    : `${prop} will reset to the template default`}
                                            </li>
                                        ))}
                                    </WarningList>
                                </div>
                            )}

                            <ModalFooter>
                                <SecondaryButton onClick={handleCancelModal}>
                                    Cancel
                                </SecondaryButton>
                                <PrimaryButton onClick={handleConfirmModal}>
                                    Switch Template
                                </PrimaryButton>
                            </ModalFooter>
                        </ModalCard>
                    </ModalOverlay>,
                    document.body
                )}
        </BarContainer>
    )
}
