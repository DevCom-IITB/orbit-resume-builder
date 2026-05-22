import { useEffect, useRef, useState } from "react";

interface GeneratedTextProps{
    generatedText?: string,
    updateGeneratedText: (updatedText: string) => void 
}

const GeneratedTextArea = ({generatedText = "", updateGeneratedText}: GeneratedTextProps) => {

    const [genTextVal, setGenTextVal] = useState(generatedText)

    const [isEditAllowed, setEditAllowed] = useState(false);

    useEffect(() => {
        setGenTextVal(generatedText);
    }, [generatedText])

    const timeoutRef = useRef<number | null> (null);

    useEffect(() => {
        if(timeoutRef.current) clearTimeout(timeoutRef.current);
        
        timeoutRef.current = setTimeout(() => {
            updateGeneratedText(genTextVal)
        }, 2000)

        return () => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, [genTextVal])

    return(
        <div className="gentext-container">
            <div className="gentext-header">
                <p className="generated-text-title"> Generated Text </p>

                <div className="gentext-edit-button">
                    <button
                        className="generated-text-edit-button"
                        onClick={() => {
                            setEditAllowed(prev => !prev);
                        }}
                    >
                        Edit with JaSON
                    </button>
                </div>
            </div>
            <div
                className="gentext-textarea"
                style={{
                    width: "100%",
                    minWidth: 0
                }}
            >
                <textarea className="generated-textarea"
                    value={genTextVal}
                    placeholder="Generated text will appear here..."
                    onChange={(event) => {
                        setGenTextVal(event.target.value);
                    }}
                    readOnly={!isEditAllowed}
                />
            </div>
        </div>
    );
}
export default GeneratedTextArea;