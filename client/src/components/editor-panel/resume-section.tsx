import { useState } from 'react'
import SectionItem from './section-item'
import type { LocalSection, LocalEntry } from '../../types/editor-panel/local-state'
import { toLocalEntry } from '../../types/editor-panel/local-state'
import type { SectionEntry } from '../../types/resume'
import { addEntry, deleteEntry, updateEntry } from '../../lib/api'
import { DndContext, type DragEndEvent } from '@dnd-kit/core'
import {
    SortableContext,
    verticalListSortingStrategy,
    arrayMove,
    useSortable,
} from '@dnd-kit/sortable'
import { Pencil, Plus, Minus, GripHorizontal } from 'lucide-react'
import ProjectModal from './modals/ProjectModal'
import GithubModal from './modals/GithubModal'
import type { Repo } from '../../types/editor-panel/repos'

interface ResumeSectionProps {
    section: LocalSection
    isSectionReorderEnabled: boolean
    resumeId: string
    itemLabel: string
    onSectionCollapse: (sectionId: string) => void
    onEntriesChanged: (sectionId: string, entries: LocalEntry[]) => void
    onEntryUpdated: (sectionId: string, entry: SectionEntry) => void
    onRenderRequest: () => void,
    onImportRepos: (sectionKey: string, importedRepos: Repo[]) => void
}

const ResumeSection = ({
    section,
    isSectionReorderEnabled,
    resumeId,
    itemLabel,
    onSectionCollapse,
    onEntriesChanged,
    onEntryUpdated,
    onRenderRequest,
    onImportRepos
}: ResumeSectionProps) => {
    const [isReorderEnabled, setReorderEnabled] = useState(false)
    const [showProjectModal, setShowProjectModal] = useState(false)
    const [showGithubModal, setShowGithubModal] = useState(false)
    const [githubRepos, setGithubRepos] = useState<Repo[]>([])

    const { attributes, listeners, setNodeRef, transform, transition } =
        useSortable({
            id: `section-${section.id}`,
            disabled: !isSectionReorderEnabled,
        })

    const handleEntryAdd = async () => {
        try {
            const newEntry = await addEntry(resumeId, section.id)
            const localEntry: LocalEntry = { ...toLocalEntry(newEntry), isCollapsed: false }
            onEntriesChanged(section.id, [...section.entries, localEntry])
        } catch (err) {
            console.error('[ResumeSection] addEntry failed:', err)
        }
    }

    const handleEntryDelete = (entryId: string) => {
        deleteEntry(resumeId, section.id, entryId)
            .then(() => {
                onEntriesChanged(
                    section.id,
                    section.entries.filter((e) => e.id !== entryId)
                )
            })
            .catch((err) =>
                console.error('[ResumeSection] deleteEntry failed:', err)
            )
    }

    const handleEntryCollapseToggle = (entryId: string) => {
        onEntriesChanged(
            section.id,
            section.entries.map((e) =>
                e.id === entryId ? { ...e, isCollapsed: !e.isCollapsed } : e
            )
        )
    }

    const handleCollapseAll = () => {
        onEntriesChanged(
            section.id,
            section.entries.map((e) => ({ ...e, isCollapsed: true }))
        )
    }

    const handleDragEnd = (event: DragEndEvent) => {
        window.LAST_DND_TIME = Date.now()
        const { active, over } = event
        if (!over || active.id === over.id) return

        const oldIndex = section.entries.findIndex((e) => e.id === active.id)
        const newIndex = section.entries.findIndex((e) => e.id === over.id)
        const reordered = arrayMove(section.entries, oldIndex, newIndex)

        onEntriesChanged(section.id, reordered)

        // Persist new order to server (optimistic — fire and forget)
        reordered.forEach((entry, idx) => {
            updateEntry(resumeId, section.id, entry.id, { order: idx }).catch(
                console.error
            )
        })
    }

    const handleGithubImport = () => {
        setShowProjectModal(false)

        // Change this to an API call to check if connected to github
        // const connected = true;

        // if(!connected) {
        //     Need to add an API call to connect to github
        //     console.log('not connected')
        // }

        // need to get the available repos and then send to github
        setGithubRepos(
            // =========================================================================Remove after API setup=============================================================================
            [
                {
                    id: 1,
                    name: "Resume Builder",
                    language: "React",
                    selected: false
                },
                {
                    id: 2,
                    name: "Portfolio Website",
                    language: "Next.js",
                    selected: false
                },
                {
                    id: 3,
                    name: "Image Classifier",
                    language: "Python",
                    selected: false
                },
                {
                    id: 4,
                    name: "Resume Builder",
                    language: "React",
                    selected: false
                },
                {
                    id: 5,
                    name: "Portfolio Website",
                    language: "Next.js",
                    selected: false
                },
                {
                    id: 6,
                    name: "Image Classifier",
                    language: "Python",
                    selected: false
                },
            ]
            // =========================================================================Remove after API setup=============================================================================
        )

        console.log("GitHub selected");
        setShowGithubModal(true);
    }

    const handleClearAllImports = () => {
        setGithubRepos(
            githubRepos.map((repo) => {
                return({
                    ...repo,
                    selected: false
                })
            })
        )
    }

    const handleImportedRepoMap = () => {
        // console.log(githubRepos.filter((repo) => repo.selected));
        setShowGithubModal(false)

        const importedRepos = githubRepos.filter((repo) => repo.selected)

        onImportRepos('key_projects', importedRepos)
    }

    return (
        <div
            className="resume-section-card"
            ref={setNodeRef}
            style={{
                transform: transform
                    ? `translate3d(0px, ${transform.y}px, 0px)`
                    : undefined,
                transition,
            }}
        >
            <div className="resume-section-topbar">
                {isSectionReorderEnabled && (
                    <div
                        className="section-drag-container"
                        style={{
                            visibility: isSectionReorderEnabled
                                ? 'visible'
                                : 'hidden',
                            pointerEvents: isSectionReorderEnabled
                                ? 'auto'
                                : 'none',
                        }}
                    >
                        <button
                            className="section-drag-button"
                            {...attributes}
                            {...listeners}
                        >
                            <GripHorizontal className="lucide-icon drag-icon" />
                        </button>
                    </div>
                )}

                <h1
                    className={`resume-section-title ${section.isCollapsed ? 'collapsed' : 'expanded'}`}
                >
                    {section.sectionType.displayName}
                </h1>

                <div
                    className="resume-section-topbar-controls"
                    style={{ minWidth: '11rem' }}
                >
                    <div
                        className="section-item-toolbar"
                        style={{
                            display: isSectionReorderEnabled
                                ? 'none'
                                : section.isCollapsed
                                  ? 'none'
                                  : 'flex',
                        }}
                    >
                        <button
                            className={`item-reorder-toggle-button ${isReorderEnabled ? 'save' : 'edit'}`}
                            onClick={() => {
                                if (!isReorderEnabled) handleCollapseAll()
                                setReorderEnabled((prev) => !prev)
                            }}
                        >
                            <>
                                {!isReorderEnabled && (
                                    <Pencil className="lucide-button-icon" />
                                )}
                                <span>
                                    {isReorderEnabled ? 'Save' : 'Reorder'}{' '}
                                </span>
                            </>
                        </button>
                    </div>

                    <div
                        className="section-collapse-container"
                        style={{
                            display: isSectionReorderEnabled ? 'none' : 'flex',
                        }}
                    >
                        <button
                            className="section-collapse-button"
                            onClick={() => {
                                const lastDrag = window.LAST_DND_TIME ?? 0
                                if (Date.now() - lastDrag < 180) return
                                onSectionCollapse(section.id)
                            }}
                        >
                            {section.isCollapsed ? (
                                <Plus className="lucide-icon" />
                            ) : (
                                <Minus className="lucide-icon collapse-icon" />
                            )}
                        </button>
                    </div>
                </div>
            </div>

            <div
                className={`section-item-container ${
                    section.isCollapsed ? 'collapsed' : 'expanded'
                }`}
            >
                <div className="section-content-wrapper">
                    <DndContext onDragEnd={handleDragEnd}>
                        <SortableContext
                            items={section.entries.map((e) => e.id)}
                            strategy={verticalListSortingStrategy}
                        >
                            <div
                                className="item-data-container"
                                style={{ width: '100%', minWidth: 0 }}
                            >
                                {section.entries.map((entry, index) => (
                                    <SectionItem
                                        key={entry.id}
                                        entry={entry}
                                        label={itemLabel}
                                        displayIndex={index}
                                        resumeId={resumeId}
                                        sectionId={section.id}
                                        isReorderEnabled={isReorderEnabled}
                                        onToggleCollapse={
                                            handleEntryCollapseToggle
                                        }
                                        onEntryUpdated={(updated) =>
                                            onEntryUpdated(section.id, updated)
                                        }
                                        onEntryDelete={handleEntryDelete}
                                        onRenderRequest={onRenderRequest}
                                    />
                                ))}
                            </div>
                        </SortableContext>
                    </DndContext>

                    {section.sectionType.allowMultipleEntries && (
                        <div className="section-item-add">
                            <button
                                className="add-section-item-button"
                                onClick={() => {
                                    if(section.sectionType.key === "key_projects"){
                                        setShowProjectModal(true)
                                        return;
                                    }else{
                                        handleEntryAdd()
                                    }
                                }}
                            >
                                + Add {itemLabel}
                            </button>
                        </div>
                    )}
                </div>
            </div>
            <ProjectModal
                open={showProjectModal}
                onClose={() => setShowProjectModal(false)}
                onGithub={handleGithubImport}
                onManual={() => {
                    setShowProjectModal(false);
                    handleEntryAdd();
                }}
            />
            <GithubModal
                open={showGithubModal}
                onClose={() => {
                    setShowGithubModal(false)
                }}
                repos={githubRepos}
                onRepoToggle={(id) => {
                    setGithubRepos((prev) => prev.map((repo) => repo.id === id ? {
                                    ...repo,
                                    selected: !repo.selected,
                                } : repo
                        )
                    );
                }}
                onImport={handleImportedRepoMap}
                onClear={handleClearAllImports}
            />
        </div>
    )
}

export default ResumeSection
