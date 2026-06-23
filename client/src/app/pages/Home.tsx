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
} from '../../lib/api'
import type { ResumeListItem } from '../../types/resume'
import '../App.css'

function formatDate(iso: string) {
    const d = new Date(iso)
    return d.toLocaleDateString('en-GB')
}

function sortResumes(items: ResumeListItem[]) {
    return [...items].sort((a, b) => {
        const pinDiff = Number(b.isPinned) - Number(a.isPinned)
        if (pinDiff !== 0) return pinDiff
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    })
}

function Home() {
    const navigate = useNavigate()
    const [showModal, setShowModal] = useState(false)
    const [resumes, setResumes] = useState<ResumeListItem[]>([])
    const [loading, setLoading] = useState(true)
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        let cancelled = false
        ;(async () => {
            try {
                const data = await listResumes()
                if (!cancelled) setResumes(sortResumes(data.results))
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
        templateKey: string
        visualThemeKey: string
        pages: number
        configOverride: Record<string, unknown>
    }) => {
        setCreating(true)
        setError(null)
        try {
            const resume = await createResume({
                title: prefs.fileName,
                templateKey: prefs.templateKey,
                visualThemeKey: prefs.visualThemeKey,
                pages: prefs.pages,
                configOverride: prefs.configOverride,
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

        const newPinned = !resume.isPinned
        // Optimistic update
        setResumes((current) =>
            sortResumes(
                current.map((r) =>
                    r.id === id ? { ...r, isPinned: newPinned } : r
                )
            )
        )
        setError(null)
        try {
            await patchResume(id, { isPinned: newPinned })
        } catch (err) {
            console.error('[Home] Failed to pin resume:', err)
            // Revert
            setResumes((current) =>
                sortResumes(
                    current.map((r) =>
                        r.id === id ? { ...r, isPinned: !newPinned } : r
                    )
                )
            )
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
        pages: 1,
        type: r.template.displayName,
        updatedAt: formatDate(r.updatedAt),
        starred: r.isPinned,
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
