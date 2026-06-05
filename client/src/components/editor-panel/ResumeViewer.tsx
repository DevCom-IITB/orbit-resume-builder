import { useState, useEffect } from 'react'
import styled, { keyframes } from 'styled-components'
import PdfCanvas from './PdfCanvas'
import PdfToolbar from './PdfToolbar'
import { generateLatexData, generatePdfData } from '../../lib/api'

// --- Styled Components ---
const ViewerContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  /* REMOVED: position: relative; */
`

// ADD THIS NEW WRAPPER
const CanvasContainer = styled.div`
  position: relative;
  flex-grow: 1;
  width: 100%;
  display: flex;
  min-height: 0; /* Prevents flexbox overflowing issues */
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

const GenerateButton = styled.button`
  padding: 12px 24px;
  background-color: #4f46e5;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  width: 100%;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background-color 0.2s ease-in-out;
  &:disabled {
    background-color: #9ca3af;
    cursor: not-allowed;
  }
  &:hover:not(:disabled) {
    background-color: #4338ca;
  }
`

const spin = keyframes`
  to { transform: rotate(360deg); }
`

const ButtonSpinner = styled.span`
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  animation: ${spin} 0.75s linear infinite;
`

// --- Interfaces ---
interface ResumeViewerProps {
  aggregatedData: Record<string, unknown>
  isExpanded: boolean
  onToggleExpand: () => void
}

// --- Component ---
export default function ResumeViewer({
  aggregatedData,
  isExpanded,
  onToggleExpand,
}: ResumeViewerProps) {
  const [status, setStatus] = useState<
    'idle' | 'loading' | 'success' | 'error'
  >('idle')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [latexCache, setLatexCache] = useState<string | null>(null)

  // Viewer State (Page removed)
  const [fitMode, setFitMode] = useState<'width' | 'height'>('width')
  const [zoom, setZoom] = useState<number | null>(null)

  // Zoom Handlers
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

  const handleGeneratePdf = async () => {
    if (Object.keys(aggregatedData).length === 0) {
      alert('Please save at least one section before generating the PDF.')
      return
    }

    setStatus('loading')

    try {
      const newPdfUrl = await generatePdfData(aggregatedData)
      if (pdfUrl) URL.revokeObjectURL(pdfUrl)
      setPdfUrl(newPdfUrl)
      setStatus('success')
    } catch (error) {
      console.error(error)
      setStatus('error')
    }
  }

  const handleDownloadPdf = async () => {
    if (Object.keys(aggregatedData).length === 0) {
      alert('Please save at least one section before downloading the PDF.')
      return
    }

    try {
      setStatus('loading')
      const nextPdfUrl = pdfUrl ?? (await generatePdfData(aggregatedData))
      if (!pdfUrl) setPdfUrl(nextPdfUrl)

      const link = document.createElement('a')
      link.href = nextPdfUrl
      link.download = 'Resume.pdf'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      setStatus('success')
    } catch (error) {
      console.error(error)
      setStatus('error')
    }
  }

  const resolveLatex = async () => {
    if (Object.keys(aggregatedData).length === 0) {
      alert('Please save at least one section before exporting LaTeX.')
      return null
    }

    if (latexCache) return latexCache

    try {
      setStatus('loading')
      const latex = await generateLatexData(aggregatedData)
      setLatexCache(latex)
      setStatus('success')
      return latex
    } catch (error) {
      console.error(error)
      setStatus('error')
      return null
    }
  }

  const handleCopyLatex = async () => {
    const latex = await resolveLatex()
    if (!latex) return

    if (!navigator.clipboard) {
      alert('Clipboard access is not available in this browser.')
      return
    }

    try {
      await navigator.clipboard.writeText(latex)
      alert('LaTeX copied to clipboard!')
    } catch (error) {
      console.error(error)
      alert('Failed to copy LaTeX to clipboard.')
    }
  }

  const handleDownloadLatex = async () => {
    const latex = await resolveLatex()
    if (!latex) return

    const latexBlob = new Blob([latex], {
      type: 'text/x-tex;charset=utf-8',
    })
    const latexUrl = URL.createObjectURL(latexBlob)
    const link = document.createElement('a')
    link.href = latexUrl
    link.download = 'Resume.tex'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(latexUrl)
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

      <GenerateButton
        onClick={handleGeneratePdf}
        disabled={status === 'loading'}
      >
        {status === 'loading' ? 'Compiling LaTeX...' : 'Generate Final PDF'}
        {status === 'loading' && <ButtonSpinner aria-hidden="true" />}
      </GenerateButton>

      {status === 'error' && <ErrorMessage>Error generating PDF.</ErrorMessage>}

      {/* NEW: Wrap the button and the canvas so they are glued together */}
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
          isLoading={status === 'loading'}
          fitMode={fitMode}
          zoom={zoom}
        />
      </CanvasContainer>
    </ViewerContainer>
  )
}
