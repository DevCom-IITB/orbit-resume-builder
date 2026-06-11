// import { useEffect, useRef, useState } from 'react'
// import { Pencil } from 'lucide-react'

// interface GeneratedTextProps {
//     generatedText?: string
//     updateGeneratedText: (updatedText: string) => void
// }

// const GeneratedTextArea = ({
//     generatedText = '',
//     updateGeneratedText,
// }: GeneratedTextProps) => {
//     const [genTextVal, setGenTextVal] = useState(generatedText)

//     const [isEditAllowed, setEditAllowed] = useState(false)

//   const textareaRef = useRef<HTMLTextAreaElement | null>(null)

//   useEffect(() => {
//     setGenTextVal(generatedText)
//   }, [generatedText])
//   const timeoutRef = useRef<number | null>(null)

//     useEffect(() => {
//         if (timeoutRef.current) clearTimeout(timeoutRef.current)

//         timeoutRef.current = setTimeout(() => {
//             updateGeneratedText(genTextVal)
//         }, 2000)

//         return () => {
//             if (timeoutRef.current) clearTimeout(timeoutRef.current)
//         }
//     }, [genTextVal, updateGeneratedText])

//   useEffect(() => {
//     const textarea = textareaRef.current

//     if (!textarea) return

//     textarea.style.height = 'auto'

//     textarea.style.height = `${Math.min(
//       textarea.scrollHeight,
//       parseFloat(getComputedStyle(document.documentElement).fontSize) * 16
//     )}px`

//     textarea.style.overflowY =
//       textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden'
//   }, [genTextVal])

//   return (
//     <div className="gentext-container">
//       <div className="gentext-header">
//         <p className="generated-text-title"> Generated Text </p>

//         {!isEditAllowed && (
//           <button
//             className={`generated-text-edit-button ${isEditAllowed ? 'edit-allowed' : 'edit-disabled'}`}
//             onClick={() => {
//               setEditAllowed((prev) => !prev)
//             }}
//           >
//             <>
//               {!isEditAllowed && (
//                 <Pencil className="lucide-button-icon edit-text-icon" />
//               )}
//               <span>{isEditAllowed ? 'Save' : 'Edit With JaSON'} </span>
//             </>
//           </button>
//         )}
//       </div>

//       <div className="gentext-output-card">
//         {isEditAllowed && (
//           <div className="json-editor-header">
//             <span>JSON Editor</span>

//             <button
//               className="json-save-button"
//               onClick={() => {
//                 const cleanedText = genTextVal.replace(/\n\s*\n+/g, '\n')
//                 setGenTextVal(cleanedText)

//                 setEditAllowed(false)
//               }}
//             >
//               Save
//             </button>
//           </div>
//         )}

//         <textarea
//           ref={textareaRef}
//           className="generated-textarea"
//           value={genTextVal}
//           placeholder="Generated text will appebar here..."
//           onChange={(event) => {
//             setGenTextVal(event.target.value)
//           }}
//           readOnly={!isEditAllowed}
//         />
//       </div>
//     </div>
//   )
// }
// export default GeneratedTextArea


//---------------------------------------------
import { useEffect, useRef, useState } from 'react'
import { Pencil } from 'lucide-react'

interface GeneratedTextProps {
  generatedText?: string
  updateGeneratedText: (updatedText: string) => void
}

const GeneratedTextArea = ({
  generatedText = '',
  updateGeneratedText,
}: GeneratedTextProps) => {
  const [genTextVal, setGenTextVal] = useState(generatedText)
  const [isEditAllowed, setEditAllowed] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  // Keep local state in sync with parent props
  useEffect(() => {
    setGenTextVal(generatedText)
  }, [generatedText])

  // Auto-resize the textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(
      textarea.scrollHeight,
      parseFloat(getComputedStyle(document.documentElement).fontSize) * 16
    )}px`

    textarea.style.overflowY =
      textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden'
  }, [genTextVal])

  return (
    <div className="gentext-container">
      <div className="gentext-header">
        <p className="generated-text-title"> Generated Text </p>

        {!isEditAllowed && (
          <button
            className={`generated-text-edit-button ${isEditAllowed ? 'edit-allowed' : 'edit-disabled'}`}
            onClick={() => {
              setEditAllowed((prev) => !prev)
            }}
          >
            <>
              {!isEditAllowed && (
                <Pencil className="lucide-button-icon edit-text-icon" />
              )}
              <span>{isEditAllowed ? 'Save' : 'Edit With JaSON'} </span>
            </>
          </button>
        )}
      </div>

      <div className="gentext-output-card">
        {isEditAllowed && (
          <div className="json-editor-header">
            <span>JSON Editor</span>

            <button
              className="json-save-button"
              onClick={() => {
                const cleanedText = genTextVal.replace(/\n\s*\n+/g, '\n')
                setGenTextVal(cleanedText)
                setEditAllowed(false)

                // ARCHITECTURE FIX: Only update parent when explicitly clicking "Save"
                updateGeneratedText(cleanedText)
              }}
            >
              Save
            </button>
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="generated-textarea"
          value={genTextVal}
          placeholder="Generated text will appear here..."
          onChange={(event) => {
            setGenTextVal(event.target.value)
          }}
          readOnly={!isEditAllowed}
        />
      </div>
    </div>
  )
}
export default GeneratedTextArea