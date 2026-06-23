import { useEffect, useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useAuth } from './auth/AuthProvider'
import EditorPanel from './components/editor-panel/editor-layout'
import ResumeViewer from './components/editor-panel/ResumeViewer'
import { getResume, patchResume, type ResumeRecord } from './lib/api'

function App() {
    const { token } = useAuth()
    const { resumeId } = useParams()
    const [isViewerExpanded, setIsViewerExpanded] = useState(false)
    const [masterResumeData, setMasterResumeData] = useState<
        Record<string, unknown>
    >({})
    const [resume, setResume] = useState<ResumeRecord | null>(null)
    const [loading, setLoading] = useState(true)
    const [loadError, setLoadError] = useState<string | null>(null)

    useEffect(() => {
        if (!token || !resumeId) {
            setLoading(false)
            return
        }

        let cancelled = false
        setLoading(true)
        setLoadError(null)
            ; (async () => {
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

    const handleTitleSave = async (title: string) => {
        if (!resumeId) return
        const updated = await patchResume(resumeId, { title })
        setResume(updated)
    }

    if (!token) {
        return (
            <div className="app-shell">
                <div
                    className="card"
                    style={{ textAlign: 'center', marginTop: '20vh' }}
                >
                    <h2>Authenticating...</h2>
                    <p className="muted">
                        Waiting for secure token from REACH.
                    </p>
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

    if (loadError || !resume) {
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
            {/* Conditionally hide the editor if the viewer is expanded */}
            {!isViewerExpanded && (
                <div className="editor-pane">
                    <EditorPanel
                        title={resume.title}
                        onTitleSave={handleTitleSave}
                        onDataChange={(compiledData) =>
                            setMasterResumeData(compiledData)
                        }
                    />
                </div>
            )}

            {/* Viewer pane flexes to take up remaining space */}
            <div className="viewer-pane" style={{ flex: 1 }}>
                <ResumeViewer
                    aggregatedData={masterResumeData}
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
