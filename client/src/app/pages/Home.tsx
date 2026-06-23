import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IntroSteps, ResumesList } from '../../components'
import ResumePreferencesModal from '../../components/ResumePreferencesModal/ResumePreferencesModal'
import {
    createResume,
    listResumes,
    type ResumeRecord,
} from '../../lib/api'
import '../App.css'

function formatDate(iso: string) {
    const d = new Date(iso)
    return d.toLocaleDateString('en-GB')
}

function Home() {
    const navigate = useNavigate()
    const [showModal, setShowModal] = useState(false)
    const [resumes, setResumes] = useState<ResumeRecord[]>([])
    const [loading, setLoading] = useState(true)
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
            ; (async () => {
                try {
                    const data = await listResumes()
                    if (!cancelled) setResumes(data)
                } catch (err) {
                    console.error('[Home] Failed to load resumes:', err)
                    if (!cancelled) setError('Could not load your resumes.')
                } finally {
                    if (!cancelled) setLoading(false)
                }
            })()
        return () => {
            cancelled = true
        }
    }, [])

    const handleCreate = async (prefs: {
        fileName: string
        resumeType: string
        header: string
        pages: number
    }) => {
        setCreating(true)
        setError(null)
        try {
            const resume = await createResume({
                title: prefs.fileName,
                resume_type: prefs.pages === 1 ? 'ONE' : 'TWO',
                header_type: prefs.header === 'short' ? 'SHORT' : 'LONG',
            })
            navigate(`/editor/${resume.id}`)
        } catch (err) {
            console.error('[Home] Failed to create resume:', err)
            setError('Could not create resume. Check that the backend is running.')
            setShowModal(true)
        } finally {
            setCreating(false)
        }
    }

    const listItems = resumes.map((r) => ({
        id: r.id,
        name: r.title,
        pages: r.resume_type === 'ONE' ? 1 : 2,
        type: r.header_type === 'SHORT' ? 'Short header' : 'Long header',
        updatedAt: formatDate(r.updated_at),
    }))

    return (
        <div className="app">
            <div className="app__body" style={{ padding: '32px' }}>
                <div className="app__main">
                    {loading ? (
                        <p style={{ padding: 24 }}>Loading resumes…</p>
                    ) : error && resumes.length === 0 ? (
                        <p style={{ padding: 24, color: '#b91c1c' }}>{error}</p>
                    ) : resumes.length === 0 ? (
                        <IntroSteps onStartMaking={() => setShowModal(true)} />
                    ) : (
                        <ResumesList
                            items={listItems}
                            onStartMaking={() => setShowModal(true)}
                            onOpenResume={(id) => navigate(`/editor/${id}`)}
                        />
                    )}
                </div>
            </div>

            <ResumePreferencesModal
                isOpen={showModal}
                onClose={() => setShowModal(false)}
                onCreate={handleCreate}
                isSubmitting={creating}
            />
            {error && resumes.length > 0 && (
                <p
                    style={{
                        position: 'fixed',
                        bottom: 16,
                        left: '50%',
                        transform: 'translateX(-50%)',
                        background: '#fef2f2',
                        color: '#b91c1c',
                        padding: '8px 16px',
                        borderRadius: 8,
                        fontSize: 13,
                    }}
                >
                    {error}
                </p>
            )}
        </div>
    )
}

export default Home
