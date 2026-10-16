import { useEffect, useState } from 'react'
import ResumeSection from './resume-section'
import { DndContext, type DragEndEvent } from '@dnd-kit/core'
import {
    SortableContext,
    verticalListSortingStrategy,
    arrayMove,
} from '@dnd-kit/sortable'
import './editor-layout.css'
import { Pencil } from 'lucide-react'
import type { Resume, SectionEntry } from '../../types/resume'
import type { LocalSection, LocalEntry } from '../../types/editor-panel/local-state'
import { toLocalSection } from '../../types/editor-panel/local-state'
import { updateSection, addEntry } from '../../lib/api'
import type { Project} from '../../types/editor-panel/repos'

// Maps section_type key → short label used in "Experience 1", "Project 2" etc.
const ITEM_LABELS: Record<string, string> = {
    header: 'Header',
    education: 'Education',
    professional_experience: 'Experience',
    key_projects: 'Project',
    technical_skills: 'Skill',
    courses: 'Course',
    positions_of_responsibility: 'PoR',
    scholastic_achievements: 'Achievement',
}

function getItemLabel(sectionTypeKey: string): string {
    return ITEM_LABELS[sectionTypeKey] ?? sectionTypeKey
}

// function projectToLocalEntry(project: Project): LocalEntry {
//     return {
//         id: crypto.randomUUID(),
//         order: 1,
//         rawInput: project.readme,
//         content: '',
//         generationStatus: `${project.generation ? 'done': 'pending'}` ,
//         isCollapsed: true
//     }
// }

interface EditorPanelProps {
    resume: Resume
    onTitleSave: (title: string) => Promise<void>
    onRenderRequest: () => void
}

const EditorPanel = ({
    resume,
    onTitleSave,
    onRenderRequest,
}: EditorPanelProps) => {
    const [sections, setSections] = useState<LocalSection[]>(() =>
        resume.sections.map(toLocalSection)
    )
    const [fileName, setFileName] = useState(resume.title)
    const [isSectionReorderEnabled, setSectionReorderEnabled] = useState(false)

    // Sync title when resume prop changes (e.g., after patch)
    useEffect(() => {
        setFileName(resume.title)
    }, [resume.title])

    // Re-initialize sections only when switching to a different resume
    useEffect(() => {
        setSections(resume.sections.map(toLocalSection))
    }, [resume.id]) // eslint-disable-line react-hooks/exhaustive-deps

    const handleFileNameBlur = async () => {
        const trimmed = fileName.trim()
        if (!trimmed) {
            setFileName(resume.title)
            return
        }
        if (trimmed === resume.title) return
        setFileName(trimmed)
        try {
            await onTitleSave(trimmed)
        } catch {
            setFileName(resume.title)
        }
    }

    const handleSectionCollapse = (sectionId: string) => {
        setSections((prev) =>
            prev.map((s) =>
                s.id === sectionId ? { ...s, isCollapsed: !s.isCollapsed } : s
            )
        )
    }

    const collapseAll = () => {
        setSections((prev) =>
            prev.map((s) => ({
                ...s,
                isCollapsed: true,
                entries: s.entries.map((e) => ({ ...e, isCollapsed: true })),
            }))
        )
    }

    const handleEntriesChanged = (sectionId: string, entries: LocalEntry[]) => {
        setSections((prev) =>
            prev.map((s) => (s.id === sectionId ? { ...s, entries } : s))
        )
    }

    const handleEntryUpdated = (sectionId: string, updated: SectionEntry) => {
        setSections((prev) =>
            prev.map((s) => {
                if (s.id !== sectionId) return s
                return {
                    ...s,
                    entries: s.entries.map((e) =>
                        e.id === updated.id
                            ? { ...e, ...updated }
                            : e
                    ),
                }
            })
        )
    }

    const handleSectionDragEnd = (event: DragEndEvent) => {
        window.LAST_DND_TIME = Date.now()
        const { active, over } = event
        if (!over || active.id === over.id) return

        const oldIndex = sections.findIndex(
            (s) => `section-${s.id}` === active.id
        )
        const newIndex = sections.findIndex(
            (s) => `section-${s.id}` === over.id
        )
        const reordered = arrayMove(sections, oldIndex, newIndex)
        setSections(reordered)

        // Persist new order to server (optimistic — fire and forget)
        reordered.forEach((section, idx) => {
            updateSection(resume.id, section.id, { order: idx }).catch(
                console.error
            )
        })
    }

    // const handleImportRepos = (sectionKey: string, importedRepos: Project[]) => {
    //     console.log(importedRepos)
    
    //     // need to process the repos to match the sectionType
    //     // assume processedRepos is the const which contains 
    //     // the data after processing to match datatpye of Section 
    //     const processedRepos = importedRepos.map(projectToLocalEntry)
        
    //     setSections(prev => 
    //         prev.map(section => {
    //             if(section.sectionType.key !== sectionKey) return section;

    //             return {
    //                 ...section,

    //                 entries: [
    //                     ...section.entries,
    //                     ...processedRepos
    //                 ]
    //             }
    //         })
            
    //     )
    // }

    const handleImportRepos = async (sectionKey: string, importedRepos: Project[]) => {
        const section = sections.find((s) => s.sectionType.key === sectionKey)

        if (!section) {
            console.error(`Section not found: ${sectionKey}`)
            return
        }

        const createdEntries: LocalEntry[] = []

        try {
            for (const project of importedRepos) {
                const entry = await addEntry(
                    resume.id,
                    section.id,
                    project.readme ?? ''
                )

                createdEntries.push({
                    ...entry,
                    isCollapsed: false,
                })
            }

            setSections((prev) =>
                prev.map((s) =>
                    s.id === section.id
                        ? {
                            ...s,
                            entries: [...s.entries, ...createdEntries],
                        }
                        : s
                )
            )
        } catch (error) {
            console.error(
                '[EditorPanel] Failed to save imported projects:',
                error
            )
        }
    }

    return (
        <div className="editor-panel">
            <div className="resume-header">
                <textarea
                    className="file-name-input"
                    value={fileName}
                    maxLength={32}
                    rows={1}
                    onChange={(event) => {
                        const value = event.target.value.replace(/\n/g, '')
                        setFileName(value)
                    }}
                    onBlur={handleFileNameBlur}
                />

                <button
                    className={`section-reorder-button ${isSectionReorderEnabled ? 'save' : 'edit'}`}
                    onClick={() => {
                        if (!isSectionReorderEnabled) collapseAll()
                        setSectionReorderEnabled((prev) => !prev)
                    }}
                >
                    <>
                        {!isSectionReorderEnabled && (
                            <Pencil className="lucide-button-icon" />
                        )}
                        <span>
                            {isSectionReorderEnabled
                                ? 'Save'
                                : 'Reorder Sections'}{' '}
                        </span>
                    </>
                </button>
            </div>

            <div className="resume-section panel-visible">
                <DndContext onDragEnd={handleSectionDragEnd}>
                    <SortableContext
                        items={sections.map((s) => `section-${s.id}`)}
                        strategy={verticalListSortingStrategy}
                    >
                        {sections.map((section) => (
                            <ResumeSection
                                key={section.id}
                                section={section}
                                isSectionReorderEnabled={isSectionReorderEnabled}
                                resumeId={resume.id}
                                itemLabel={getItemLabel(section.sectionType.key)}
                                onSectionCollapse={handleSectionCollapse}
                                onEntriesChanged={handleEntriesChanged}
                                onEntryUpdated={handleEntryUpdated}
                                onRenderRequest={onRenderRequest}
                                onImportRepos={handleImportRepos}
                            />
                        ))}
                    </SortableContext>
                </DndContext>
            </div>
        </div>
    )
}

export default EditorPanel
