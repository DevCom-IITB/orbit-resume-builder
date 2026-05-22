import GeneratedTextArea from "./generated-textarea";
import ItemTextArea from "./item-textarea";
import type { Item } from "../../types/editor-panel/item";
import { useSortable } from "@dnd-kit/sortable";

import deleteIcon from "../../assets/editor-panel/delete.png"
import dragIcon from "../../assets/editor-panel/drag.png"
import collapseIcon from "../../assets/editor-panel/collapse.png"
import expandIcon from "../../assets/editor-panel/expand.png"
// import { useEffect, useState } from "react";
// import { CSS } from "@dnd-kit/utilities";

interface SectionItemProps {
    item: Item
    label: string
    displayIndex: number
    sectionId?: number
    isReorderEnabled: boolean
    
    onToggleCollapse: (itemId: number) => void
    onItemDelete: (itemId: number) => void
    onDescChange: (itemId: number, updatedText: string) => void
    onTextGenerated: (itemId: number, generatedText: string) => void
    onUpdateGeneratedText: (itemId: number, updatedText: string) => void
}

const SectionItem = ({item, label, displayIndex, sectionId, isReorderEnabled, onToggleCollapse, onItemDelete, onDescChange, onTextGenerated, onUpdateGeneratedText}: SectionItemProps) => {

    const isCollapsed = item.isCollapsed;

    const {attributes, listeners, setNodeRef, transform, transition} = useSortable({
        id: `${sectionId}-${item.id}`,
        disabled: !isReorderEnabled
    })

    const handleUpdateDesc = (updatedText: string) => {
        onDescChange(item.id, updatedText);
    } 

    const handleGenerateText = (textVal: string) => {
        // API Call to Generate Text Goes here

        // Lets say the generated text is: "hello wassup how you doing"
        const genText = "hello wassup how you doing";
        onTextGenerated(item.id, genText)
    }

    const handleUpdateGeneratedDesc = (updatedText: string) => {
        onUpdateGeneratedText(item.id, updatedText)
    }

    return(
        <div className="section-item-card"
            ref={setNodeRef}
            style={{
                transform: transform
                    ? `translate3d(0px, ${transform.y}px, 0px)`
                    : undefined,
                transition
            }}
        >
            <div className="section-item-header">
                <p className="section-item-title">
                    {label} {displayIndex+1}
                </p>

                <div className="reorder-drag-button"
                    style={{
                        display: isReorderEnabled ? "flex" : "none"
                    }}
                >
                    <button className="item-drag-button"
                        {...attributes}
                        {...listeners}
                    >
                        <img className="icon-button"
                            src={dragIcon}  
                        />
                    </button>

                </div>


                <div className="section-item-controls"
                    style={{
                        display: isReorderEnabled ? "none" : "flex"
                    }}
                >
                    <button className="delete-item-button"
                        onClick={() => {
                            onItemDelete(item.id)
                        }}
                    >
                        <img className="icon-button"
                            src={deleteIcon}
                        />
                    </button>

                    <button className="collapse-item-button"
                        onClick={() => {

                            const lastDrag =
                                (
                                    window as any
                                ).LAST_DND_TIME ?? 0;

                            if(
                                Date.now() - lastDrag
                                < 180
                            ){
                                return;
                            }

                            onToggleCollapse(item.id);

                        }}
                    >
                        <img className="icon-button"
                            src={ isCollapsed ? expandIcon : collapseIcon}
                        />
                        {/* {isCollapsed ? "+" : "-"} */}
                    </button>

                </div>

            </div>

            <div className={`item-content-wrapper ${
                    item.isCollapsed
                        ? "collapsed"
                        : "expanded"
                }`}
            >
                <div>
                    <ItemTextArea desc={item.desc} 
                        updateDesc={handleUpdateDesc}
                        onGenerateClicked={handleGenerateText}
                        />
                    <GeneratedTextArea
                    generatedText={item.generatedText}
                    updateGeneratedText={handleUpdateGeneratedDesc}/>
                    {/* Text areas here */}
                </div>

            </div>

        </div>

    );
}
export default SectionItem;