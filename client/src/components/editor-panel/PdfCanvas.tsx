import { useEffect, useRef, useState } from 'react'
import styled, { keyframes } from 'styled-components'

const pulse = keyframes`
  0% { opacity: 0.6; }
  50% { opacity: 0.2; }
  100% { opacity: 0.6; }
`

const CanvasWrapper = styled.div`
    width: 100%;
    flex: 1 1 0;
    min-width: 0;
    min-height: 0;
    position: relative;
    background-color: #b0b2b4;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
`

const Skeleton = styled.div`
    width: 80%;
    height: 90%;
    background-color: white;
    animation: ${pulse} 1.5s infinite;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
`

const EmptyText = styled.p`
    color: #a0aec0;
    font-family: monospace;
`

const Overlay = styled.div`
    position: absolute;
    inset: 0;
    background-color: rgba(255, 255, 255, 0.65);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 5;
`

interface PdfCanvasProps {
    url: string | null
    isLoading: boolean
    fitMode: 'width' | 'height'
    zoom: number | null
}

export default function PdfCanvas({
    url,
    isLoading,
    fitMode,
    zoom,
}: PdfCanvasProps) {
    const wrapperRef = useRef<HTMLDivElement>(null)
    const [viewport, setViewport] = useState({ width: 0, height: 0 })

    useEffect(() => {
        const wrapper = wrapperRef.current
        if (!wrapper) return
        let timer: ReturnType<typeof setTimeout>
        const scheduleSize = (width: number, height: number) => {
            clearTimeout(timer)
            // Initialize the native PDF viewer only after the pane has settled.
            timer = setTimeout(() => {
                const next = {
                    width: Math.round(width),
                    height: Math.round(height),
                }
                setViewport((previous) =>
                    previous.width === next.width &&
                    previous.height === next.height
                        ? previous
                        : next
                )
            }, 100)
        }
        const measure = () => {
            const { width, height } = wrapper.getBoundingClientRect()
            scheduleSize(width, height)
        }
        measure()
        const observer =
            typeof ResizeObserver !== 'undefined'
                ? new ResizeObserver(([entry]) => {
                      if (entry)
                          scheduleSize(
                              entry.contentRect.width,
                              entry.contentRect.height
                          )
                  })
                : null
        observer?.observe(wrapper)
        if (!observer) window.addEventListener('resize', measure)
        return () => {
            observer?.disconnect()
            window.removeEventListener('resize', measure)
            clearTimeout(timer)
        }
    }, [])

    const hasViewport = viewport.width > 0 && viewport.height > 0
    const view =
        zoom !== null
            ? `zoom=${zoom},0,0`
            : `view=${fitMode === 'width' ? 'FitH,0' : 'Fit'}`
    const source = `${url}#toolbar=0&navpanes=0&page=1&${view}`

    return (
        <CanvasWrapper ref={wrapperRef}>
            {url && hasViewport ? (
                <iframe
                    // A new document or pane size needs a fresh native viewer;
                    // reusing it can retain the previous document's viewport.
                    key={`${source}-${viewport.width}-${viewport.height}`}
                    src={source}
                    width="100%"
                    height="100%"
                    style={{
                        position: 'absolute',
                        inset: 0,
                        display: 'block',
                        border: 'none',
                    }}
                    title="Resume PDF"
                />
            ) : isLoading || url ? (
                <Skeleton />
            ) : (
                <EmptyText>PDF Preview</EmptyText>
            )}
            {url && hasViewport && isLoading && (
                <Overlay>
                    <Skeleton />
                </Overlay>
            )}
        </CanvasWrapper>
    )
}
