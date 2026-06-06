import { useState, useEffect } from 'react'
import styled from 'styled-components'
import PdfCanvas from './PdfCanvas'
import PdfToolbar from './PdfToolbar'
import { generateResumeAssets } from '../../lib/api'

// --- Styled Components ---
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

<<<<<<< HEAD
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
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [latexCode, setLatexCode] = useState<string | null>(null)

  // Viewer State
  const [fitMode, setFitMode] = useState<'width' | 'height'>('width')
  const [zoom, setZoom] = useState<number | null>(null)

  // Zoom Handlers
  const handleZoomIn = () => setZoom((prev) => (prev ? prev + 25 : 125))
  const handleZoomOut = () => setZoom((prev) => (prev ? Math.max(25, prev - 25) : 75))
  const handleFitModeChange = (mode: 'width' | 'height') => {
    setFitMode(mode)
    setZoom(null)
  }

  // Memory Cleanup
  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl)
    }
  }, [pdfUrl])

  // Live Preview Auto-Generator
  useEffect(() => {
    const autoGeneratePdf = async () => {
      // 1. Safely convert the incoming data to a string
      const dataString = JSON.stringify(aggregatedData);
      
      // 2. Ignore empty objects
      if (!aggregatedData || dataString === '{}') return;

      // 3. Deep check: If the editor passes a skeleton template with empty arrays/objects 
      // (e.g., {"education": [], "experience": {}}), ignore it until real data is typed.
      const hasRealData = Object.values(aggregatedData).some(val => {
        if (Array.isArray(val)) return val.length > 0;
        if (typeof val === 'object' && val !== null) return Object.keys(val).length > 0;
        return Boolean(val);
      });

      if (!hasRealData) return; // Stop the animation from running on empty templates

      setStatus('loading');

      try {
        const { pdfUrl: newPdfUrl, latexCode: newLatexCode } = await generateResumeAssets(aggregatedData);
        
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(newPdfUrl);
        setLatexCode(newLatexCode);
        
        setStatus('success');
      } catch (error) {
        console.error(error);
        setStatus('error');
      }
    };

    autoGeneratePdf();
    
  // 4. CRITICAL FIX: Use JSON.stringify in the dependency array to prevent infinite rendering loops!
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(aggregatedData)]);

  // --- Action Handlers ---
  const handleDownloadPdf = () => {
    if (!pdfUrl) return alert("Generate PDF first!")
    const link = document.createElement('a')
    link.href = pdfUrl
    link.download = 'Resume.pdf'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleCopyLatex = async () => {
    if (!latexCode) return alert("Generate PDF first!")
    try {
      await navigator.clipboard.writeText(latexCode)
      alert('LaTeX copied to clipboard!')
    } catch (err) {
      console.error('Failed to copy text: ', err)
      alert('Failed to copy LaTeX to clipboard.')
    }
  }

  const handleDownloadLatex = () => {
    if (!latexCode) return alert("Generate PDF first!")
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

      {status === 'error' && <ErrorMessage>Error generating PDF.</ErrorMessage>}

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
=======
const GenerateButton = styled.button`
    padding: 12px 24px;
    background-color: #4f46e5;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    width: 100%;
    cursor: pointer;
    /* Keeps label and spinner aligned on one line. */
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: background-color 0.2s ease-in-out;

    /* Automatically applies when disabled={true} is passed */
    &:disabled {
        background-color: #9ca3af;
        cursor: not-allowed;
    }

    /* Optional: A nice hover effect only when it's NOT disabled */
    &:hover:not(:disabled) {
        background-color: #4338ca;
    }
`

const spin = keyframes`
  to {
    transform: rotate(360deg);
  }
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
}

// --- Component ---
export default function ResumeViewer({ aggregatedData }: ResumeViewerProps) {
    const [status, setStatus] = useState<
        'idle' | 'loading' | 'success' | 'error'
    >('idle')
    const [pdfUrl, setPdfUrl] = useState<string | null>(null)

    // Memory Cleanup: Deletes the old PDF from RAM when unmounting
    useEffect(() => {
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl)
        }
    }, [pdfUrl])

    // Generation Logic
    const handleGeneratePdf = async () => {
        // Prevent empty API calls
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

    return (
        <ViewerContainer>
            <GenerateButton
                onClick={handleGeneratePdf}
                disabled={status === 'loading'}
            >
                {status === 'loading'
                    ? 'Compiling LaTeX...'
                    : 'Generate Final PDF'}
                {status === 'loading' && <ButtonSpinner aria-hidden="true" />}
            </GenerateButton>

            {status === 'error' && (
                <ErrorMessage>Error generating PDF.</ErrorMessage>
            )}

            {/* 
        Pass the status down as a boolean to the dumb component 
        so it knows when to show the Skeleton pulse animation
      */}
            <PdfCanvas url={pdfUrl} isLoading={status === 'loading'} />
        </ViewerContainer>
    )
>>>>>>> d7023ba8c218e1cd73ebb7dc60445162981668d8
}
