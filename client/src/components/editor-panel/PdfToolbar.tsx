import { useState, useEffect, useRef } from 'react'
import styled from 'styled-components'

const ToolbarContainer = styled.div`
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    width: 100%;
    box-sizing: border-box;
`

const ToolbarGroup = styled.div`
    display: flex;
    gap: 12px;
    align-items: center;
`

const DropdownContainer = styled.div`
    position: relative;
`

const ButtonGroup = styled.div`
    display: flex;
    align-items: center;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    background-color: #ffffff;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
`

const ActionButton = styled.button`
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: transparent;
    border: none;
    color: #3b82f6;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s;
    &:hover {
        background-color: #eff6ff;
    }
`

const Divider = styled.div`
    width: 1px;
    height: 18px;
    background-color: #bfdbfe;
`

const ChevronButton = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 6px 8px;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: background-color 0.15s;
    &:hover {
        background-color: #eff6ff;
    }
`

// Added a transient prop `$alignRight` to control menu pop-out direction
const DropdownMenu = styled.div<{ $alignRight?: boolean }>`
    position: absolute;
    top: calc(100% + 4px);
    ${(props) => (props.$alignRight ? 'right: 0;' : 'left: 0;')}
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    min-width: 180px;
    display: flex;
    flex-direction: column;
    padding: 4px 0;
    z-index: 20;
`

const MenuItem = styled.button`
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    width: 100%;
    border: none;
    background: transparent;
    color: #0f172a;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    text-align: left;
    transition: background-color 0.15s;
    &:hover {
        background-color: #f8fafc;
    }
`

const IconButton = styled.button`
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    cursor: pointer;
    color: #3b82f6; /* Blue icons for zoom bar */
    padding: 6px;
    border-radius: 4px;
    transition:
        color 0.15s,
        background-color 0.15s;
    &:hover {
        background-color: #eff6ff;
    }
`

interface PdfToolbarProps {
    fitMode: 'width' | 'height'
    onFitModeChange: (mode: 'width' | 'height') => void
    //   zoom: number | null;
    onZoomIn: () => void
    onZoomOut: () => void
    onCopyLatex?: () => void
    onDownloadPdf?: () => void
    onDownloadLatex?: () => void
}

export default function PdfToolbar({
    fitMode,
    onFitModeChange,
    onZoomIn,
    onZoomOut,
    onCopyLatex,
    onDownloadPdf,
    onDownloadLatex,
}: PdfToolbarProps) {
    const [isFitOpen, setIsFitOpen] = useState(false)
    const [isCopyOpen, setIsCopyOpen] = useState(false)
    const [isDownloadOpen, setIsDownloadOpen] = useState(false)

    const fitRef = useRef<HTMLDivElement>(null)
    const copyRef = useRef<HTMLDivElement>(null)
    const downloadRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as Node
            if (fitRef.current && !fitRef.current.contains(target))
                setIsFitOpen(false)
            if (copyRef.current && !copyRef.current.contains(target))
                setIsCopyOpen(false)
            if (downloadRef.current && !downloadRef.current.contains(target))
                setIsDownloadOpen(false)
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () =>
            document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    return (
        <ToolbarContainer>
            {/* LEFT SIDE: Fit Mode Controls */}
            <ToolbarGroup>
                <DropdownContainer ref={fitRef}>
                    <ButtonGroup>
                        <ActionButton onClick={() => setIsFitOpen(!isFitOpen)}>
                            {fitMode === 'width' ? (
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#3b82f6',
                                        strokeWidth: '2.5px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <path d="M4 4v16M20 4v16M8 12h8M8 12l2-2M8 12l2 2M16 12l-2-2M16 12l-2 2" />
                                </svg>
                            ) : (
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#3b82f6',
                                        strokeWidth: '2.5px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                                </svg>
                            )}
                            <span>
                                {fitMode === 'width'
                                    ? 'Fit to width'
                                    : 'Full Screen'}
                            </span>
                        </ActionButton>
                        <Divider />
                        <ChevronButton onClick={() => setIsFitOpen(!isFitOpen)}>
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                style={{
                                    fill: 'none',
                                    stroke: '#3b82f6',
                                    strokeWidth: '2.5px',
                                    strokeLinecap: 'round',
                                    strokeLinejoin: 'round',
                                }}
                            >
                                <path d="M6 9l6 6 6-6" />
                            </svg>
                        </ChevronButton>
                    </ButtonGroup>

                    {isFitOpen && (
                        <DropdownMenu>
                            <MenuItem
                                onClick={() => {
                                    onFitModeChange('width')
                                    setIsFitOpen(false)
                                }}
                            >
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#475569',
                                        strokeWidth: '2px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <path d="M4 4v16M20 4v16M8 12h8M8 12l2-2M8 12l2 2M16 12l-2-2M16 12l-2 2" />
                                </svg>
                                Fit to Width
                            </MenuItem>
                            <MenuItem
                                onClick={() => {
                                    onFitModeChange('height')
                                    setIsFitOpen(false)
                                }}
                            >
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#475569',
                                        strokeWidth: '2px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                                </svg>
                                Full Screen (to height)
                            </MenuItem>
                        </DropdownMenu>
                    )}
                </DropdownContainer>
            </ToolbarGroup>

            {/* CENTER: New Minimalist Zoom Bar */}
            <ToolbarGroup style={{ flex: 1, justifyContent: 'center' }}>
                <ButtonGroup style={{ padding: '0 4px', gap: '12px' }}>
                    <IconButton onClick={onZoomOut} title="Zoom Out">
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                    </IconButton>

                    <div
                        style={{
                            color: '#3b82f6',
                            display: 'flex',
                            alignItems: 'center',
                        }}
                    >
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                    </div>

                    <IconButton onClick={onZoomIn} title="Zoom In">
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                    </IconButton>
                </ButtonGroup>
            </ToolbarGroup>

            {/* RIGHT SIDE: Action Controls */}
            <ToolbarGroup>
                {/* Copy Dropdown */}
                <DropdownContainer ref={copyRef}>
                    <ButtonGroup>
                        <ActionButton onClick={onCopyLatex}>
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                style={{
                                    fill: 'none',
                                    stroke: 'currentColor',
                                    strokeWidth: '2.5px',
                                    strokeLinecap: 'round',
                                    strokeLinejoin: 'round',
                                }}
                            >
                                <rect
                                    x="9"
                                    y="9"
                                    width="13"
                                    height="13"
                                    rx="2"
                                    ry="2"
                                />
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                            </svg>
                            Copy
                        </ActionButton>
                        <Divider />
                        <ChevronButton
                            onClick={() => setIsCopyOpen(!isCopyOpen)}
                        >
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                style={{
                                    fill: 'none',
                                    stroke: '#3b82f6',
                                    strokeWidth: '2.5px',
                                    strokeLinecap: 'round',
                                    strokeLinejoin: 'round',
                                }}
                            >
                                <path d="M6 9l6 6 6-6" />
                            </svg>
                        </ChevronButton>
                    </ButtonGroup>

                    {isCopyOpen && (
                        <DropdownMenu $alignRight>
                            <MenuItem
                                onClick={() => {
                                    onCopyLatex?.()
                                    setIsCopyOpen(false)
                                }}
                            >
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#475569',
                                        strokeWidth: '2px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <rect
                                        x="9"
                                        y="9"
                                        width="13"
                                        height="13"
                                        rx="2"
                                        ry="2"
                                    />
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                </svg>
                                Copy as LaTex
                            </MenuItem>
                        </DropdownMenu>
                    )}
                </DropdownContainer>

                {/* Download Dropdown */}
                <DropdownContainer ref={downloadRef}>
                    <ButtonGroup>
                        <ActionButton onClick={onDownloadPdf}>
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                style={{
                                    fill: 'none',
                                    stroke: 'currentColor',
                                    strokeWidth: '2.5px',
                                    strokeLinecap: 'round',
                                    strokeLinejoin: 'round',
                                }}
                            >
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="7 10 12 15 17 10" />
                                <line x1="12" y1="15" x2="12" y2="3" />
                            </svg>
                            Download
                        </ActionButton>
                        <Divider />
                        <ChevronButton
                            onClick={() => setIsDownloadOpen(!isDownloadOpen)}
                        >
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                style={{
                                    fill: 'none',
                                    stroke: '#3b82f6',
                                    strokeWidth: '2.5px',
                                    strokeLinecap: 'round',
                                    strokeLinejoin: 'round',
                                }}
                            >
                                <path d="M6 9l6 6 6-6" />
                            </svg>
                        </ChevronButton>
                    </ButtonGroup>

                    {isDownloadOpen && (
                        <DropdownMenu $alignRight>
                            <MenuItem
                                onClick={() => {
                                    onDownloadPdf?.()
                                    setIsDownloadOpen(false)
                                }}
                            >
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#475569',
                                        strokeWidth: '2px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                    <polyline points="7 10 12 15 17 10" />
                                    <line x1="12" y1="15" x2="12" y2="3" />
                                </svg>
                                Download as PDF
                            </MenuItem>
                            <MenuItem
                                onClick={() => {
                                    onDownloadLatex?.()
                                    setIsDownloadOpen(false)
                                }}
                            >
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    style={{
                                        fill: 'none',
                                        stroke: '#475569',
                                        strokeWidth: '2px',
                                        strokeLinecap: 'round',
                                        strokeLinejoin: 'round',
                                    }}
                                >
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                    <polyline points="7 10 12 15 17 10" />
                                    <line x1="12" y1="15" x2="12" y2="3" />
                                </svg>
                                Download as LaTex
                            </MenuItem>
                        </DropdownMenu>
                    )}
                </DropdownContainer>
            </ToolbarGroup>
        </ToolbarContainer>
    )
}
