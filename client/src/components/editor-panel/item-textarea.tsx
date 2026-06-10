import { useEffect, useRef, useState } from 'react'
import type { PointDensity } from '../../types/editor-panel/pointdensity'
import { createPortal } from 'react-dom'

interface ItemTextAreaProps {
  desc: string
  lastGeneratedNormalized: string
  updateDesc: (updatedDesc: string) => void
  onGenerateClicked: (textVal: string) => void
  generateStatus: 'loading' | 'success' | 'error'
  generateButtonLabel: string
}

const ItemTextArea = ({
  desc = '',
  lastGeneratedNormalized,
  updateDesc,
  onGenerateClicked,
  generateStatus,
  generateButtonLabel,
}: ItemTextAreaProps) => {
  const [textVal, setTextVal] = useState(desc)

  const normalizeText = (text: string) => text.replace(/\s+/g, ' ').trim()

  const hasMeaningfulChanges =
    normalizeText(textVal) !== lastGeneratedNormalized

  const timeoutRef = useRef<number | null>(null)

  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const snapPoints = [15, 50, 85]

  const densityValues: PointDensity[] = ['concise', 'standard', 'detailed']

  const densityMap = {
    concise: {
      title: 'Concise point',
      subtitle: '1-2 lines',
    },

    standard: {
      title: 'Standard point',
      subtitle: '2-3 lines',
    },

    detailed: {
      title: 'Detailed point',
      subtitle: '3-4 lines',
    },
  }

  const [density, setDensity] = useState<PointDensity>('concise')

  const [isFitToLineEnabled, setFitToLineEnabled] = useState(true)

  const [showFitToLineModal, setShowFitToLineModal] = useState(false)

  const [thumbPosition, setThumbPosition] = useState(15)

  const sliderRef = useRef<HTMLDivElement | null>(null)

  const snapThumb = (rawPosition: number) => {
    const nearest = snapPoints.reduce((prev, curr) =>
      Math.abs(curr - rawPosition) < Math.abs(prev - rawPosition) ? curr : prev
    )

    setThumbPosition(nearest)

    setDensity(densityValues[snapPoints.indexOf(nearest)])
  }

  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    const slider = sliderRef.current

    if (!slider) return

    const bounds = slider.getBoundingClientRect()

    const move = (pointerEvent: PointerEvent) => {
      const outsideVerticalBounds =
        pointerEvent.clientY < bounds.top ||
        pointerEvent.clientY > bounds.bottom

      if (outsideVerticalBounds) {
        snapThumb(thumbPosition)

        window.removeEventListener('pointermove', move)

        window.removeEventListener('pointerup', up)

        return
      }

      const relativePosition =
        ((pointerEvent.clientX - bounds.left) / bounds.width) * 100

      const clamped = Math.max(0, Math.min(100, relativePosition))

      setThumbPosition(clamped)
    }

    const up = (pointerEvent: PointerEvent) => {
      const relativePosition =
        ((pointerEvent.clientX - bounds.left) / bounds.width) * 100

      snapThumb(relativePosition)

      window.removeEventListener('pointermove', move)

      window.removeEventListener('pointerup', up)
    }

    move(event.nativeEvent)

    window.addEventListener('pointermove', move)

    window.addEventListener('pointerup', up)
  }

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

  useEffect(() => {
    const textarea = textareaRef.current

    if (!textarea) return

    textarea.style.height = 'auto'

    textarea.style.height = `${Math.min(
      textarea.scrollHeight,
      parseFloat(getComputedStyle(document.documentElement).fontSize) * 12
    )}px`

    textarea.style.overflowY =
      textarea.scrollHeight > textarea.clientHeight ? 'auto' : 'hidden'
  }, [textVal])

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
          ref={textareaRef}
          className="item-description-textarea"
          value={textVal}
          placeholder="Describe your experience..."
          onChange={(event) => {
            setTextVal(event.target.value)
          }}
        />
      </div>

      <div className="qol-buttons">
        <button
          className={`fit-to-line-button ${
            isFitToLineEnabled ? 'enabled' : 'disabled'
          }`}
          onClick={() => {
            if (isFitToLineEnabled) {
              setShowFitToLineModal(true)
              return
            }

            setFitToLineEnabled(true)
          }}
        >
          Fit To Line
        </button>

        <div className="slider-control-group">
          <div
            ref={sliderRef}
            className="slider-shell"
            onPointerDown={startDrag}
          >
            <div className="slider-track" />

            {snapPoints.map((point) => (
              <div
                key={point}
                className="slider-anchor"
                style={{
                  left: `${point}%`,
                }}
              />
            ))}

            <div
              className="slider-thumb"
              style={{
                left: `${thumbPosition}%`,
              }}
            />
          </div>

          <div className="slider-description">
            <span className="slider-title">{densityMap[density].title}</span>
            <span className="slider-subtitle">
              {densityMap[density].subtitle}
            </span>
          </div>
        </div>

        <div className="generate-button-div">
          <button
            className={`generate-text-button ${
              !hasMeaningfulChanges && generateButtonLabel === 'Generate'
                ? 'generated-state'
                : ''
            }`}
            disabled={
              generateStatus === 'loading' ||
              (!hasMeaningfulChanges && generateButtonLabel === 'Generate')
            }
            onClick={() => {
              const cleanedText = textVal.replace(/\n\s*\n+/g, '\n\n')
              onGenerateClicked(cleanedText)
            }}
          >
            {generateButtonLabel}
            {generateStatus === 'loading' && (
              <span className="generate-spinner" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
      {showFitToLineModal &&
        createPortal(
          <div className="fit-to-line-modal-overlay">
            <div className="fit-to-line-modal">
              <div className="fit-to-line-modal-content">
                <div className="fit-to-line-modal-message">
                  <h3>Editing the text would lead to uneven white spaces</h3>
                </div>
                <div className="fit-to-line-modal-icon" />
              </div>

              <div className="fit-to-line-modal-actions">
                <button
                  className="fit-to-line-cancel"
                  onClick={() => {
                    setShowFitToLineModal(false)
                  }}
                >
                  Cancel
                </button>

                <button
                  className="fit-to-line-confirm"
                  onClick={() => {
                    setFitToLineEnabled(false)
                    setShowFitToLineModal(false)
                  }}
                >
                  Continue anyway
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  )
}
export default ItemTextArea
