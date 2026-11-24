import { StrictMode } from 'react'
import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PdfCanvas from './PdfCanvas'
import ResumeViewer from './ResumeViewer'

let notifyResize: (width: number, height: number) => void
const disconnect = vi.fn()

beforeEach(() => {
    vi.useFakeTimers()
    disconnect.mockClear()
    vi.stubGlobal(
        'ResizeObserver',
        class {
            constructor(callback: ResizeObserverCallback) {
                notifyResize = (width, height) =>
                    callback(
                        [
                            {
                                contentRect: { width, height },
                            } as ResizeObserverEntry,
                        ],
                        this as unknown as ResizeObserver
                    )
            }
            observe() {}
            disconnect = disconnect
        }
    )
})

afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
})

function resize(width = 600, height = 800) {
    act(() => {
        notifyResize(width, height)
        vi.advanceTimersByTime(100)
    })
}

const props = {
    url: 'blob:first',
    isLoading: false,
    fitMode: 'width' as const,
    zoom: null,
}

describe('PDF viewport lifecycle', () => {
    it('waits for a nonzero pane and starts at page one fitted to width', () => {
        render(<PdfCanvas {...props} />)
        resize(0, 0)
        expect(screen.queryByTitle('Resume PDF')).not.toBeInTheDocument()
        resize()
        expect(screen.getByTitle('Resume PDF')).toHaveAttribute(
            'src',
            'blob:first#toolbar=0&navpanes=0&page=1&view=FitH,0'
        )
    })

    it('creates a fresh native viewer for every regenerated PDF', () => {
        const { rerender } = render(
            <StrictMode>
                <PdfCanvas {...props} />
            </StrictMode>
        )
        resize()
        let previous = screen.getByTitle('Resume PDF')
        for (let generation = 1; generation <= 5; generation++) {
            rerender(
                <StrictMode>
                    <PdfCanvas {...props} url={`blob:revision-${generation}`} />
                </StrictMode>
            )
            const current = screen.getByTitle('Resume PDF')
            expect(current).not.toBe(previous)
            expect(previous).not.toBeInTheDocument()
            expect(current).toHaveAttribute(
                'src',
                expect.stringContaining('page=1&view=FitH,0')
            )
            previous = current
        }
    })

    it('debounces pane resizing and refits only when the dimensions change', () => {
        render(<PdfCanvas {...props} />)
        resize()
        const original = screen.getByTitle('Resume PDF')
        resize()
        expect(screen.getByTitle('Resume PDF')).toBe(original)
        act(() => {
            notifyResize(900, 800)
            vi.advanceTimersByTime(80)
            notifyResize(1200, 800)
            vi.advanceTimersByTime(99)
        })
        expect(screen.getByTitle('Resume PDF')).toBe(original)
        act(() => vi.advanceTimersByTime(1))
        expect(screen.getByTitle('Resume PDF')).not.toBe(original)
    })

    it('preserves explicit zoom while resetting the document origin', () => {
        const { rerender } = render(<PdfCanvas {...props} zoom={125} />)
        resize()
        expect(screen.getByTitle('Resume PDF')).toHaveAttribute(
            'src',
            expect.stringContaining('zoom=125,0,0')
        )
        rerender(<PdfCanvas {...props} url="blob:second" zoom={125} />)
        resize(900, 800)
        expect(screen.getByTitle('Resume PDF')).toHaveAttribute(
            'src',
            'blob:second#toolbar=0&navpanes=0&page=1&zoom=125,0,0'
        )
        const zoomed = screen.getByTitle('Resume PDF')
        rerender(<PdfCanvas {...props} fitMode="height" />)
        expect(screen.getByTitle('Resume PDF')).not.toBe(zoomed)
        expect(screen.getByTitle('Resume PDF')).toHaveAttribute(
            'src',
            expect.stringContaining('view=Fit')
        )
    })

    it('keeps the existing document mounted while generation is pending', () => {
        const { rerender } = render(<PdfCanvas {...props} />)
        resize()
        const original = screen.getByTitle('Resume PDF')
        rerender(<PdfCanvas {...props} isLoading />)
        expect(screen.getByTitle('Resume PDF')).toBe(original)
        rerender(<PdfCanvas {...props} />)
        expect(screen.getByTitle('Resume PDF')).toBe(original)
    })

    it('reinitializes after being hidden and cancels pending resize work on unmount', () => {
        const { unmount } = render(<PdfCanvas {...props} />)
        resize()
        const original = screen.getByTitle('Resume PDF')
        resize(0, 0)
        expect(screen.queryByTitle('Resume PDF')).not.toBeInTheDocument()
        resize()
        expect(screen.getByTitle('Resume PDF')).not.toBe(original)
        act(() => notifyResize(900, 800))
        unmount()
        expect(disconnect).toHaveBeenCalledOnce()
        expect(vi.getTimerCount()).toBe(0)
    })

    it('does not revoke PDF URLs owned by the app on replace or viewer unmount', () => {
        const revoke = vi.fn()
        vi.stubGlobal(
            'URL',
            class extends URL {
                static revokeObjectURL = revoke
            }
        )
        const viewerProps = {
            pdfUrl: 'blob:first',
            latexCode: null,
            renderStatus: 'success' as const,
            isExpanded: false,
            onToggleExpand: vi.fn(),
        }
        const { rerender, unmount } = render(<ResumeViewer {...viewerProps} />)
        resize()
        rerender(<ResumeViewer {...viewerProps} pdfUrl="blob:second" />)
        unmount()
        expect(revoke).not.toHaveBeenCalled()
    })
})
