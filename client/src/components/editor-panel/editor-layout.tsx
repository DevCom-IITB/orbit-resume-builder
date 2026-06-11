import { useState } from 'react'
import ResumeSection from './resume-section'
import { DndContext, type DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import './editor-layout.css'

import { Pencil } from 'lucide-react'
import type { Section } from '../../types/editor-panel/section'
import type { Item } from '../../types/editor-panel/item'

//======prop for comping data feature===========
interface EditorPanelProps {
  onDataChange: (compiledData: Record<string, unknown[]>) => void
}
//===========================================

//==============Compiling all json results for pdf generation - function========================

const compileMasterPayload = (sections: Section[]) => {
  const sectionTypeMap: Record<string, string> = {
    education: 'education',
    professional_experience: 'experience',
    key_projects: 'key_projects',
    positions_of_responsibility: 'pors',
    scholastic_achievements: 'scholastic_achievements',
    courses: 'courses',
    technical_skills: 'technical_skills',
  }
  const payload: Record<string, unknown[]> = {}

  sections.forEach((section) => {
    const validItems = section.items.filter(
      (item) => item.generatedText && item.generatedText.trim() !== ''
    )

    const sectionData = validItems.map((item) => {
      try {
        return JSON.parse(item.generatedText as string)
      } catch {
        return item.generatedText
      }
    })

    const payloadKey =
      sectionTypeMap[section.sectionType] ?? section.sectionType

    if (!payload[payloadKey]) {
      payload[payloadKey] = []
    }

    payload[payloadKey].push(...sectionData)
  })

  return payload
}

//==============================================================================

const EditorPanel = ({ onDataChange }: EditorPanelProps) => {
  const [sections, setSections] = useState<Section[]>([
    {
      id: 0,
      title: 'Experience',
      label: 'Experience',
      sectionType: 'professional_experience',
      isCollapsed: true,
      items: [
        {
          id: 0,
          desc: 'text used for item 1 - Exp',
          isCollapsed: true,
          generatedText: '',
        },
        {
          id: 1,
          desc: 'text used for item 1 - POR',
          isCollapsed: true,
          generatedText: '',
        },
      ],
    },
    {
      id: 1,
      title: 'POR',
      label: 'POR',
      sectionType: 'positions_of_responsibility',
      isCollapsed: true,
      items: [
        {
          id: 0,
          desc: 'text used for item 1 - POR',
          isCollapsed: true,
          generatedText: '',
        },
      ],
    },
    {
      id: 2,
      title: 'Scholastic Achievements',
      label: 'Scholastic Achievement',
      sectionType: 'scholastic_achievements',
      isCollapsed: true,
      items: [],
    },
    {
      id: 3,
      title: 'Education',
      label: 'Education',
      sectionType: 'education',
      isCollapsed: true,
      items: [],
    },
    {
      id: 4,
      title: 'Key Projects',
      label: 'Key Project',
      sectionType: 'key_projects',
      isCollapsed: true,
      items: [],
    },
    {
      id: 5,
      title: 'Courses',
      label: 'Course',
      sectionType: 'courses',
      isCollapsed: true,
      items: [],
    },
    {
      id: 6,
      title: 'Technical Skills',
      label: 'Technical Skill',
      sectionType: 'technical_skills',
      isCollapsed: true,
      items: [],
    },
  ])

  // Removed the redundant isPanelCollapsed state entirely!
  const [fileName, setFileName] = useState('File name')
  const [isSectionReorderEnabled, setSectionReorderEnabled] = useState(false)

  const handleItemCollapse = (sectionId: number, itemId: number) => {
    setSections((prevSections) =>
      prevSections.map((section) => {
        if (sectionId === -1 && itemId === -1) {
          return {
            ...section,
            isCollapsed: true,
            items: section.items.map((item) => ({
              ...item,
              isCollapsed: true,
            })),
          }
        }
        if (section.id !== sectionId) return section
        return {
          ...section,
          items: section.items.map((item) => {
            if (itemId === -1) return { ...item, isCollapsed: true }
            if (item.id !== itemId) return item
            return { ...item, isCollapsed: !item.isCollapsed }
          }),
        }
      })
    )
  }

  const handleSectionCollapse = (sectionId: number) => {
    setSections((prevSections) =>
      prevSections.map((section) => {
        if (sectionId === -1) return { ...section, isCollapsed: true }
        if (section.id !== sectionId) return section
        return { ...section, isCollapsed: !section.isCollapsed }
      })
    )
  }

  const handleItemAdd = (sectionId: number) => {
    setSections((prevSections) =>
      prevSections.map((section) => {
        if (section.id !== sectionId) return section
        return {
          ...section,
          items: [
            ...section.items,
            {
              id:
                section.items.length > 0
                  ? Math.max(...section.items.map((item) => item.id)) + 1
                  : 0,
              desc: '',
              isCollapsed: false,
              generatedText: '',
            },
          ],
        }
      })
    )
  }

  const handleItemReorder = (sectionId: number, reorderedItems: Item[]) => {
    setSections((prevSections) =>
      prevSections.map((section) => {
        if (section.id !== sectionId) return section
        return { ...section, items: reorderedItems }
      })
    )
  }

  const handleItemDescChange = (
    sectionId: number,
    itemId: number,
    updatedText: string
  ) => {
    setSections((prevSections) =>
      prevSections.map((section) => {
        if (section.id !== sectionId) return section
        return {
          ...section,
          items: section.items.map((item) => {
            if (item.id !== itemId) return item
            return { ...item, desc: updatedText }
          }),
        }
      })
    )
  }

  const handleItemDelete = (sectionId: number, itemId: number) => {
    setSections((prevSections) =>
      prevSections.map((section) => {
        if (section.id !== sectionId) return section
        return {
          ...section,
          items: section.items.filter((item) => item.id !== itemId),
        }
      })
    )
  }

  const handleItemTextGenerated = (
    sectionId: number,
    itemId: number,
    generatedText: string
  ) => {
    setSections((prevSections) => {
      const nextSections = prevSections.map((section) => {
        if (section.id !== sectionId) return section
        return {
          ...section,
          items: section.items.map((item) => {
            if (item.id !== itemId) return item
            return { ...item, generatedText: generatedText }
          }),
        }
      })

      const compiledPayload = compileMasterPayload(nextSections)
      if (Object.keys(compiledPayload).length > 0) {
        onDataChange(compiledPayload)
      }

      return nextSections
    })
  }

  const handleUpdateItemGeneratedText = (
    sectionId: number,
    itemId: number,
    updatedText: string
  ) => {
    setSections((prevSections) => {
      const nextSections = prevSections.map((section) => {
        if (section.id !== sectionId) return section
        return {
          ...section,
          items: section.items.map((item) => {
            if (item.id !== itemId) return item
            return { ...item, generatedText: updatedText }
          }),
        }
      })

      const compiledPayload = compileMasterPayload(nextSections)
      if (Object.keys(compiledPayload).length > 0) {
        onDataChange(compiledPayload)
      }

      return nextSections
    })
  }

  const handleSectionDragEnd = (event: DragEndEvent) => {
    window.LAST_DND_TIME = Date.now()
    const { active, over } = event
    if (!over) return
    if (active.id === over.id) return

    const oldIndex = sections.findIndex(
      (section) => `section-${section.id}` === active.id
    )
    const newIndex = sections.findIndex(
      (section) => `section-${section.id}` === over.id
    )
    const reorderedSections = arrayMove(sections, oldIndex, newIndex)
    setSections(reorderedSections)
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
        />

        <button
          className={`section-reorder-button ${isSectionReorderEnabled ? 'save' : 'edit'}`}
          onClick={() => {
            if (!isSectionReorderEnabled) {
              handleSectionCollapse(-1)
              handleItemCollapse(-1, -1)
            }
            setSectionReorderEnabled((prev) => !prev)
          }}
        >
          <>
            {!isSectionReorderEnabled && (
              <Pencil className="lucide-button-icon" />
            )}
            <span>{isSectionReorderEnabled ? 'Save' : 'Edit'} </span>
          </>
        </button>
      </div>

      <div className="resume-section panel-visible">
        <DndContext onDragEnd={handleSectionDragEnd}>
          <SortableContext
            items={sections.map((section) => `section-${section.id}`)}
            strategy={verticalListSortingStrategy}
          >
            {sections.map((section) => (
              <ResumeSection
                key={section.id}
                section={section}
                isSectionReorderEnabled={isSectionReorderEnabled}
                onItemCollapse={handleItemCollapse}
                onItemAdd={handleItemAdd}
                onItemDelete={handleItemDelete}
                onItemDescChange={handleItemDescChange}
                onItemTextGenerated={handleItemTextGenerated}
                onUpdateItemGeneratedText={handleUpdateItemGeneratedText}
                onItemReorder={handleItemReorder}
                onSectionCollapse={handleSectionCollapse}
              />
            ))}
          </SortableContext>
        </DndContext>
      </div>

      <div
        className="add-field-button-container"
        style={{ display: isSectionReorderEnabled ? 'flex' : 'none' }}
      >
        <button className="add-field-button">+ Add Field</button>
      </div>
    </div>
  )
}

export default EditorPanel