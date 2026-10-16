import { useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useAuth } from './auth/AuthProvider'
import EditorPanel from './components/editor-panel/editor-layout'
import ResumeViewer from './components/editor-panel/ResumeViewer'
import { getResume, patchResume, renderResume } from './lib/api'
import type { Resume } from './types/resume'

function App() {
    const { token } = useAuth()
    const { resumeId } = useParams()

    const [resume, setResume] = useState<Resume | null>(null)
    const [loading, setLoading] = useState(true)
    const [loadError, setLoadError] = useState<string | null>(null)

    const [isViewerExpanded, setIsViewerExpanded] = useState(false)
    const [renderStatus, setRenderStatus] = useState<
        'idle' | 'loading' | 'success' | 'error'
    >('idle')
    const [pdfUrl, setPdfUrl] = useState<string | null>(null)
    const [latexCode, setLatexCode] = useState<string | null>(null)

    useEffect(() => {
        if (!resumeId) {
            setLoading(false)
            return
        }

        let cancelled = false
        setLoading(true)
        setLoadError(null)
        ;(async () => {
            try {
                const data = await getResume(resumeId)
                if (!cancelled) setResume(data)
            } catch (err) {
                console.error('[Editor] Failed to load resume:', err)
                if (!cancelled) setLoadError('Could not load resume.')
            } finally {
                if (!cancelled) setLoading(false)
            }
        })()

        return () => {
            cancelled = true
        }
    }, [token, resumeId])

    // Clean up blob URL on unmount
    useEffect(() => {
        return () => {
            if (pdfUrl) URL.revokeObjectURL(pdfUrl)
        }
    }, [pdfUrl])

    const handleTitleSave = async (title: string) => {
        if (!resumeId) return
        await patchResume(resumeId, { title })
        // Only update title in local state to avoid re-initializing editor sections
        setResume((prev) => (prev ? { ...prev, title } : prev))
    }

    const handleRenderRequest = async () => {
        if (!resumeId) return
        setRenderStatus('loading')
        try {
            const result = await renderResume(resumeId)
            if (pdfUrl) URL.revokeObjectURL(pdfUrl)
            setPdfUrl(result.pdfUrl)
            setLatexCode(result.latexCode)
            setRenderStatus('success')
        } catch (err) {
            console.error('[App] Render failed:', err)
            setRenderStatus('error')
        }
    }

    if (!token) {
        return (
            <div className="app-shell">
                <div
                    className="card"
                    style={{ textAlign: 'center', marginTop: '20vh' }}
                >
                    <h2>Authenticating...</h2>
                    <p className="muted">Waiting for secure token from REACH.</p>
                </div>
            </div>
        )
    }

    if (!resumeId) {
        return <Navigate to="/home" replace />
    }

    if (loading) {
        return (
            <div className="app-shell">
                <div
                    className="card"
                    style={{ textAlign: 'center', marginTop: '20vh' }}
                >
                    <h2>Loading resume…</h2>
                </div>
            </div>
        )
    }

    if (!resume) {
        return (
            <div className="app-shell">
                <div
                    className="card"
                    style={{ textAlign: 'center', marginTop: '20vh' }}
                >
                    <h2>{loadError ?? 'Resume not found'}</h2>
                </div>
            </div>
        )
    }

    return (
        <div
            className="editor-page"
            style={{
                display: 'flex',
                gap: '16px',
                height: '100vh',
                overflow: 'hidden',
            }}
        >
            {!isViewerExpanded && (
                <div className="editor-pane">
                    <EditorPanel
                        resume={resume}
                        onTitleSave={handleTitleSave}
                        onRenderRequest={handleRenderRequest}
                    />
                </div>
            )}

            <div className="viewer-pane" style={{ flex: 1 }}>
                <ResumeViewer
                    pdfUrl={pdfUrl}
                    latexCode={latexCode}
                    renderStatus={renderStatus}
                    isExpanded={isViewerExpanded}
                    onToggleExpand={() =>
                        setIsViewerExpanded(!isViewerExpanded)
                    }
                />
            </div>
        </div>
    )
}

export default App
