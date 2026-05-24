import { useEffect, useRef, useState } from 'react'

interface ItemTextAreaProps {
  desc: string
  updateDesc: (updatedDesc: string) => void
  onGenerateClicked: (textVal: string) => void
  generateStatus: 'loading' | 'success' | 'error'
  generateButtonLabel: string
}

const ItemTextArea = ({
  desc = '',
  updateDesc,
  onGenerateClicked,
  generateStatus,
  generateButtonLabel,
}: ItemTextAreaProps) => {
  const [textVal, setTextVal] = useState(desc)

  const timeoutRef = useRef<number | null>(null)

  useEffect(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)

    timeoutRef.current = setTimeout(() => {
      updateDesc(textVal)
    }, 2000)

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [textVal, updateDesc])

  useEffect(() => {
    setTextVal(desc)
  }, [desc])

  return (
    <div className="item-textarea-container">
      <div
        className="text-area-div"
        style={{
          width: '100%',
          minWidth: 0,
        }}
      >
        <textarea
          className="item-description-textarea"
          value={textVal}
          placeholder="Describe your experience..."
          onChange={(event) => {
            setTextVal(event.target.value)
          }}
        />
      </div>

      <div className="qol-buttons">
        <button className="qol-button">Fit To Line</button>

        <button className="qol-button">List</button>
      </div>

      <div className="generate-button">
        <button
          className="generate-text-button"
          disabled={generateStatus === 'loading'}
          onClick={() => {
            onGenerateClicked(textVal)
          }}
        >
          {generateButtonLabel}
          {generateStatus === 'loading' && (
            <span className="generate-spinner" aria-hidden="true" />
          )}
        </button>
      </div>
    </div>
  )
}
export default ItemTextArea
