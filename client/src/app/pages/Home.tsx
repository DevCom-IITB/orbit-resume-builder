import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { IntroSteps, ResumesList } from '../../components'
import ResumePreferencesModal from '../../components/ResumePreferencesModal/ResumePreferencesModal'
import {
    createResume,
    deleteResume,
    duplicateResume,
    listResumes,
    patchResume,
    type ResumeRecord,
} from '../../lib/api'
import '../App.css'

function formatDate(iso: string) {
    const d = new Date(iso)
    return d.toLocaleDateString('en-GB')
}

function sortResumes(items: ResumeRecord[]) {
    return [...items].sort((a, b) => {
        const pinDiff = Number(b.is_pinned) - Number(a.is_pinned)
        if (pinDiff !== 0) return pinDiff
        return (
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )
    })
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
                    if (!cancelled) setResumes(sortResumes(data))
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

    const handlePin = async (id: string) => {
        const resume = resumes.find((r) => r.id === id)
        if (!resume) return

        setError(null)
        try {
            const updated = await patchResume(id, {
                is_pinned: !resume.is_pinned,
            })
            setResumes((current) =>
                sortResumes(
                    current.map((r) => (r.id === id ? updated : r))
                )
            )
        } catch (err) {
            console.error('[Home] Failed to pin resume:', err)
            setError('Could not update resume.')
        }
    }

    const handleDuplicate = async (id: string) => {
        setError(null)
        try {
            const copy = await duplicateResume(id)
            navigate(`/editor/${copy.id}`)
        } catch (err) {
            console.error('[Home] Failed to duplicate resume:', err)
            setError('Could not duplicate resume.')
        }
    }

    const handleDelete = async (id: string) => {
        const resume = resumes.find((r) => r.id === id)
        if (!resume) return

        const confirmed = window.confirm(
            `Delete "${resume.title}"? This cannot be undone.`
        )
        if (!confirmed) return

        setError(null)
        try {
            await deleteResume(id)
            setResumes((current) => current.filter((r) => r.id !== id))
        } catch (err) {
            console.error('[Home] Failed to delete resume:', err)
            setError('Could not delete resume.')
        }
    }

    const listItems = resumes.map((r) => ({
        id: r.id,
        name: r.title,
        pages: r.resume_type === 'ONE' ? 1 : 2,
        type: r.header_type === 'SHORT' ? 'Short header' : 'Long header',
        updatedAt: formatDate(r.updated_at),
        starred: r.is_pinned,
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
                            onPin={handlePin}
                            onDuplicate={handleDuplicate}
                            onDelete={handleDelete}
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
