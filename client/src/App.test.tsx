import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'
import { getResume, renderResume } from './lib/api'

vi.mock('./auth/AuthProvider', () => ({ useAuth: () => ({ token: 'test' }) }))
vi.mock('react-router-dom', () => ({
    useParams: () => ({ resumeId: 'resume' }),
}))
vi.mock('./lib/api', () => ({
    getResume: vi.fn(),
    patchResume: vi.fn(),
    renderResume: vi.fn(),
}))
vi.mock('./components/editor-panel/editor-layout', () => ({
    default: ({
        onPdfUpdate,
        onRenderRequest,
    }: {
        onPdfUpdate: (url: string, latex: string) => void
        onRenderRequest: () => Promise<void>
    }) => (
        <>
            <button onClick={() => onPdfUpdate('blob:style', 'style')}>
                Style update
            </button>
            <button onClick={onRenderRequest}>Generate</button>
        </>
    ),
}))
vi.mock('./components/editor-panel/ResumeViewer', () => ({
    default: ({ pdfUrl }: { pdfUrl: string | null }) => (
        <div data-testid="pdf-url">{pdfUrl}</div>
    ),
}))

afterEach(() => vi.unstubAllGlobals())

it('releases each old PDF once after replacement and the last PDF on unmount', async () => {
    const revoke = vi.fn()
    vi.stubGlobal(
        'URL',
        class extends URL {
            static revokeObjectURL = revoke
        }
    )
    vi.mocked(getResume).mockResolvedValue({ id: 'resume' } as Awaited<
        ReturnType<typeof getResume>
    >)
    vi.mocked(renderResume).mockResolvedValue({
        pdfUrl: 'blob:generated',
        latexCode: 'generated',
    })
    const { unmount } = render(<App />)
    fireEvent.click(await screen.findByText('Style update'))
    expect(screen.getByTestId('pdf-url')).toHaveTextContent('blob:style')
    expect(revoke).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Generate'))
    await waitFor(() =>
        expect(screen.getByTestId('pdf-url')).toHaveTextContent(
            'blob:generated'
        )
    )
    expect(revoke.mock.calls).toEqual([['blob:style']])
    fireEvent.click(screen.getByText('Style update'))
    expect(revoke.mock.calls).toEqual([['blob:style'], ['blob:generated']])
    unmount()
    expect(revoke.mock.calls).toEqual([
        ['blob:style'],
        ['blob:generated'],
        ['blob:style'],
    ])
})
