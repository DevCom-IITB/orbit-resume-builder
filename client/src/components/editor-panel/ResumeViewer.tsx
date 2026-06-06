import { useState, useEffect } from 'react'
import styled, { keyframes } from 'styled-components'

import PdfCanvas from './PdfCanvas'
import { generatePdfData } from '../../lib/api'

// --- Styled Components ---
const ViewerContainer = styled.div`
    display: flex;
    flex-direction: column;
    gap: 16px;
    height: 100%;
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
}
