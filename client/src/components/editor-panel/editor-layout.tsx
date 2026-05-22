import { useState } from "react";
import ResumeSection from "./resume-section";
import { DndContext } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";
import "./editor-layout.css";
import leftIcon from "../../assets/editor-panel/left-arrow.png"
import reorderIcon from "../../assets/editor-panel/reorder.png"


const EditorPanel = () => {
    
    const [sections, setSections] = useState([
        {
            id: 0,
            title: "Exp",
            label: "Experience",
            isCollapsed: true,
            items: [
                {
                    id: 0,
                    desc: "text used for item 1 - Exp",
                    isCollapsed: true,
                    generatedText: ""
                },
                {
                    id: 1,
                    desc: "text used for item 1 - POR",
                    isCollapsed: true,
                    generatedText: ""
                },
            ]
        },
        {
            id: 1,
            title: "POR",
            label: "POR",
            isCollapsed: true,
            items: [
                {
                    id: 0,
                    desc: "text used for item 1 - POR",
                    isCollapsed: true,
                    generatedText: ""
                },
            ]
        },
        {
            id: 2,
            title: "Skills",
            label: "Skill",
            isCollapsed: true,
            items: []
        }
    ])

    const [isPanelCollapsed, setPanelCollapse] = useState(false);

    const [fileName, setFileName] = useState("File name")

    const [isSectionReorderEnabled, setSectionReorderEnabled] = useState(false);

    const handleItemCollapse = (sectionId: number, itemId: number) => {
        setSections(prevSections =>
            prevSections.map((section) => {

                if(sectionId === -1 && itemId === -1){
                    return {
                        ...section,
                        isCollapsed:true,
                        items:section.items.map(item => ({
                            ...item,
                            isCollapsed:true
                        }))
                    };
                }

                if(section.id !== sectionId) return section;

                return {
                    ...section,
                    items:section.items.map((item) => {

                        if(itemId === -1){
                            return {
                                ...item,
                                isCollapsed:true
                            };
                        }

                        if(item.id !== itemId){
                            return item;
                        }

                        return {
                            ...item,
                            isCollapsed:
                                !item.isCollapsed
                        };

                    })
                };

            })
        );

    }

    const handleSectionCollapse = (sectionId: number) => {

        setSections(prevSections =>
            prevSections.map((section) => {

                if(sectionId === -1){
                    return {
                        ...section,
                        isCollapsed: true
                    }
                }else{
                    if(section.id !== sectionId) return section;
                    
                    return {
                        ...section,
                        isCollapsed: !section.isCollapsed
                    }
                }
            })
        );
    }
    
    const handleItemAdd = (sectionId: number) => {

        setSections(prevSections => 
            prevSections.map((section) => {
                if(section.id !== sectionId){
                    return section;
                }
        
                return {
                    ...section,
                    items: [
                        ...section.items,
                        {
                            id:  section.items.length > 0
                                ? Math.max(...section.items.map(item => item.id)) + 1
                                : 0,
                            desc: "",
                            isCollapsed: false,
                            generatedText: ""
                        }
                    ]
                };
            })
        )
    }

    const handleItemReorder = (sectionId: number, reorderedItems: any) => {

        setSections(prevSections => 
            prevSections.map((section) => {
                if(section.id !== sectionId) return section
        
                return {
                    ...section,
                    items: reorderedItems
                };
            })
        )
    }

    const handleItemDescChange = (sectionId: number, itemId: number, updatedText: string) => {

        setSections(prevSections => 
            prevSections.map((section) => {
                if(section.id !== sectionId) return section;
        
                return {
                    ...section,
                    items: section.items.map((item) => {
                        if(item.id !== itemId) return item;
        
                        return {
                            ...item,
                            desc: updatedText
                        };
                    })
                };
                
            })
        )
    }

    const handleItemDelete = (sectionId: number, itemId: number) => {
        setSections(prevSections => 
            prevSections.map((section) => {
                if(section.id !== sectionId){
                    return section;
                }
        
                return {
                    ...section,
                    items: section.items.filter((item) => item.id !== itemId)
                }
                
            })
        )
    }
    
    const handleItemTextGenerated = (sectionId: number, itemId: number, generatedText: string) => {
        setSections(prevSections => 
            prevSections.map((section) => {
                
                if (section.id !== sectionId) return section;
        
                return {
                  ...section,
                  items: section.items.map((item) => {
                    if (item.id !== itemId) return item;
        
                    return {
                      ...item,
                      generatedText: generatedText,
                    };
                  }),
                };
            })
        )

    }

    const handleUpdateItemGeneratedText = (sectionId: number, itemId: number, updatedText: string) => {
        setSections(prevSections => 
            prevSections.map((section) => {
                if (section.id !== sectionId) return section;
        
                return {
                  ...section,
                  items: section.items.map((item) => {
                    if (item.id !== itemId) return item;
        
                    return {
                      ...item,
                      generatedText: updatedText,
                    };
                  }),
                };
            })
        )
    }

    const handleSectionDragEnd = (event: any) => {

        (
            window as any
        ).LAST_DND_TIME = Date.now();

        const { active, over } = event;

        if (!over) return;

        if (active.id === over.id) return;

        const oldIndex = sections.findIndex(
            (section) => `section-${section.id}` === active.id
        );

        const newIndex = sections.findIndex(
            (section) => `section-${section.id}` === over.id
        );

        const reorderedSections = arrayMove(
            sections,
            oldIndex,
            newIndex
        );

        setSections(reorderedSections);
    }

    return(
        <div className="editor-panel">
            <div className="resume-header">
                <button className="panel-collapse-button"
                    onClick={() => {
                        setPanelCollapse(prev => !prev)
                    }}
                >
                    <img className={`
                        panel-collapse-icon
                        ${
                            isPanelCollapsed
                            ? "collapsed"
                            : ""
                        }
                        `}
                        src={leftIcon}
                        alt={isPanelCollapsed ? "Expand" : "Collapse"}
                    />
                </button>

                <textarea className="file-name-input"
                    value={fileName}
                    maxLength={32}
                    rows={1}
                    onChange={(event) => {

                        const value =
                            event.target.value
                                .replace(/\n/g,"");

                        setFileName(value);

                    }}
                />


                <button className="section-reorder-button" disabled={isPanelCollapsed}
                onClick={() => {
                    if(!isSectionReorderEnabled){
                        handleSectionCollapse(-1)
                        handleItemCollapse(-1, -1)
                    }
                    setSectionReorderEnabled(prev => !prev)
                }}>
                    <>
                        <img className="button-icon"
                            src={reorderIcon}
                        />
                        <span>{isSectionReorderEnabled ? "Disable" : "Reorder" } </span>
                    </>
                </button>
            </div>


            <div className={`resume-section ${isPanelCollapsed ? "panel-hidden" : "panel-visible"}`}>
                <DndContext onDragEnd={handleSectionDragEnd}>
                    <SortableContext
                        items={sections.map(
                            (section) => `section-${section.id}`
                        )}
                        strategy={verticalListSortingStrategy}
                    >
                        {sections.map((section) => (
                            <ResumeSection key={section.id}
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
        </div>
 
            
    );
}

export default EditorPanel;