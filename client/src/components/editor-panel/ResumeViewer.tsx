import { useEffect, useState } from 'react'
import styled from 'styled-components'
import PdfCanvas from './PdfCanvas'
import PdfToolbar from './PdfToolbar'

const ViewerContainer = styled.div`
    display: flex;
    flex-direction: column;
    gap: 16px;
    height: 100%;
`

const CanvasContainer = styled.div`
    position: relative;
    flex-grow: 1;
    width: 100%;
    display: flex;
    min-height: 0;
`

const ExpandButton = styled.button`
    position: absolute;
    top: 20px;
    left: 12px;
    z-index: 10;
    width: 34px;
    height: 34px;
    background-color: #2563eb;
    border: none;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
    transition:
        transform 0.2s ease,
        background-color 0.2s ease;
    &:hover {
        background-color: #1d4ed8;
        transform: scale(1.05);
    }
    &:active {
        transform: scale(0.95);
    }
`

const ErrorMessage = styled.div`
    color: #dc2626;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
`

interface ResumeViewerProps {
    pdfUrl: string | null
    latexCode: string | null
    renderStatus: 'idle' | 'loading' | 'success' | 'error'
    isExpanded: boolean
    onToggleExpand: () => void
}

export default function ResumeViewer({
    pdfUrl,
    latexCode,
    renderStatus,
    isExpanded,
    onToggleExpand,
}: ResumeViewerProps) {
    const [fitMode, setFitMode] = useState<'width' | 'height'>('width')
    const [zoom, setZoom] = useState<number | null>(null)

    const handleZoomIn = () => setZoom((prev) => (prev ? prev + 25 : 125))
    const handleZoomOut = () =>
        setZoom((prev) => (prev ? Math.max(25, prev - 25) : 75))
    const handleFitModeChange = (mode: 'width' | 'height') => {
        setFitMode(mode)
        setZoom(null)
    }

    useEffect(() => {
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl)
        }
    }, [pdfUrl])

    const handleDownloadPdf = () => {
        if (!pdfUrl) return alert('Render the resume first!')
        const link = document.createElement('a')
        link.href = pdfUrl
        link.download = 'Resume.pdf'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    const handleCopyLatex = async () => {
        if (!latexCode) return alert('Render the resume first!')
        try {
            await navigator.clipboard.writeText(latexCode)
            alert('LaTeX copied to clipboard!')
        } catch {
            alert('Failed to copy LaTeX to clipboard.')
        }
    }

    const handleDownloadLatex = () => {
        if (!latexCode) return alert('Render the resume first!')
        const blob = new Blob([latexCode], { type: 'text/plain' })
        const tempUrl = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = tempUrl
        link.download = 'Resume.tex'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(tempUrl)
    }

    return (
        <ViewerContainer>
            <PdfToolbar
                fitMode={fitMode}
                onFitModeChange={handleFitModeChange}
                onZoomIn={handleZoomIn}
                onZoomOut={handleZoomOut}
                onCopyLatex={handleCopyLatex}
                onDownloadPdf={handleDownloadPdf}
                onDownloadLatex={handleDownloadLatex}
            />

            {renderStatus === 'error' && (
                <ErrorMessage>
                    Error rendering PDF. Check the console.
                </ErrorMessage>
            )}

            <CanvasContainer>
                <ExpandButton
                    onClick={onToggleExpand}
                    title={isExpanded ? 'Restore Split View' : 'Full Screen'}
                >
                    {isExpanded ? (
                        <img
                            src="data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2218%22%20height%3D%2218%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22white%22%20stroke-width%3D%222.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Crect%20x%3D%223%22%20y%3D%223%22%20width%3D%228%22%20height%3D%2218%22%20rx%3D%222%22%20%2F%3E%3Crect%20x%3D%2213%22%20y%3D%223%22%20width%3D%228%22%20height%3D%2218%22%20rx%3D%222%22%20%2F%3E%3C%2Fsvg%3E"
                            alt="Restore Split View"
                            width="18"
                            height="18"
                            style={{ display: 'block' }}
                        />
                    ) : (
                        <img
                            src="data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2218%22%20height%3D%2218%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22white%22%20stroke-width%3D%222.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M15%203h6v6M9%2021H3v-6M21%203l-7%207M3%2021l7-7%22%2F%3E%3C%2Fsvg%3E"
                            alt="Full Screen"
                            width="18"
                            height="18"
                            style={{ display: 'block' }}
                        />
                    )}
                </ExpandButton>

                <PdfCanvas
                    url={pdfUrl}
                    isLoading={renderStatus === 'loading'}
                    fitMode={fitMode}
                    zoom={zoom}
                />
            </CanvasContainer>
        </ViewerContainer>
    )
}
