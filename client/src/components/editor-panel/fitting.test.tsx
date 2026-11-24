import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GeneratedTextArea from './generated-textarea'
import SectionItem from './section-item'
import RefitControl from './RefitControl'
import {
    generateEntry,
    updateEntry,
    previewRefit,
    applyRefit,
} from '../../lib/api'
import type { LocalEntry } from '../../types/editor-panel/local-state'
import type { RefitPreview } from '../../types/resume'

vi.mock('../../lib/api', () => ({
    generateEntry: vi.fn(),
    updateEntry: vi.fn(),
    previewRefit: vi.fn(),
    applyRefit: vi.fn(),
}))
vi.mock('@dnd-kit/sortable', () => ({
    useSortable: () => ({ attributes: {}, listeners: {}, setNodeRef: vi.fn() }),
}))

const entry: LocalEntry = {
    id: 'e',
    order: 0,
    rawInput: 'Built Python tools',
    content: null,
    generationStatus: 'pending',
    isCollapsed: false,
}

function sectionItem(value = entry) {
    return render(
        <SectionItem
            entry={value}
            label="Project"
            displayIndex={0}
            resumeId="r"
            sectionId="s"
            isReorderEnabled={false}
            onToggleCollapse={vi.fn()}
            onEntryUpdated={vi.fn()}
            onEntryDelete={vi.fn()}
            onRenderRequest={vi.fn()}
        />
    )
}

beforeEach(() => {
    vi.resetAllMocks()
})

describe('generation fitting preference', () => {
    it.each([true, false])(
        'forwards the entry-local toggle: %s',
        async (enabled) => {
            vi.mocked(updateEntry).mockResolvedValue(entry)
            vi.mocked(generateEntry).mockResolvedValue({
                ...entry,
                generationStatus: 'done',
            })
            sectionItem()
            if (!enabled) {
                fireEvent.click(
                    screen.getByRole('button', { name: 'Fit To Line' })
                )
                fireEvent.click(
                    screen.getByRole('button', { name: 'Continue anyway' })
                )
            }
            fireEvent.click(screen.getByRole('button', { name: 'Generate' }))
            await waitFor(() =>
                expect(generateEntry).toHaveBeenCalledWith(
                    'r',
                    's',
                    'e',
                    enabled
                )
            )
            expect(updateEntry).toHaveBeenCalledWith('r', 's', 'e', {
                rawInput: entry.rawInput,
            })
        }
    )

    it('shows fitting failure as a warning alongside valid content', () => {
        sectionItem({
            ...entry,
            content: [{ bullets: ['Python'] }],
            fitting: {
                status: 'partial',
                bullets: [],
                reason: 'Measurement unavailable',
            },
        })
        expect(screen.getByRole('status')).toHaveTextContent(
            'Best available wording retained'
        )
        expect(screen.getByRole('status')).toHaveTextContent(
            'Measurement unavailable'
        )
        expect(
            screen.getByRole('button', { name: 'Edit With JSON' })
        ).toBeInTheDocument()
    })
})

describe('authoritative JSON editing', () => {
    it('saves exact draft only on Save and waits for success', async () => {
        let finish!: () => void
        const save = vi.fn(
            () =>
                new Promise<void>((resolve) => {
                    finish = resolve
                })
        )
        render(
            <GeneratedTextArea
                generatedText='["old"]'
                updateGeneratedText={save}
            />
        )
        fireEvent.click(screen.getByRole('button', { name: 'Edit With JSON' }))
        const draft = '[\n\n"  chosen wording  "\n]'
        fireEvent.change(screen.getByRole('textbox'), {
            target: { value: draft },
        })
        expect(save).not.toHaveBeenCalled()
        fireEvent.click(screen.getByRole('button', { name: 'Save' }))
        expect(save).toHaveBeenCalledWith(draft)
        expect(screen.getByRole('button', { name: 'Saving...' })).toBeDisabled()
        finish()
        await screen.findByRole('button', { name: 'Edit With JSON' })
    })

    it('keeps the editable draft when saving fails', async () => {
        const save = vi.fn().mockRejectedValue(new Error('bad JSON'))
        render(
            <GeneratedTextArea
                generatedText='["old"]'
                updateGeneratedText={save}
            />
        )
        fireEvent.click(screen.getByRole('button', { name: 'Edit With JSON' }))
        fireEvent.change(screen.getByRole('textbox'), {
            target: { value: 'invalid draft' },
        })
        fireEvent.click(screen.getByRole('button', { name: 'Save' }))
        expect(await screen.findByRole('alert')).toHaveTextContent(
            'Could not save JSON'
        )
        expect(screen.getByRole('textbox')).toHaveValue('invalid draft')
        expect(screen.getByRole('textbox')).not.toHaveAttribute('readonly')
    })
})

const preview: RefitPreview = {
    token: 'signed',
    excluded_entries: 1,
    reports: [],
    proposals: [
        {
            id: '0',
            entry_id: 'e',
            section_key: 'key_projects',
            path: [0, 'bullets', 0],
            original: 'Original Python',
            text: 'Revised Python',
            status: 'fitted',
            attempts: 1,
            measurement: null,
            original_measurement: null,
            reason: '',
        },
        {
            id: '1',
            entry_id: 'e',
            section_key: 'key_projects',
            path: [0, 'bullets', 1],
            original: 'Original Docker',
            text: 'Revised Docker',
            status: 'unfitted',
            attempts: 2,
            measurement: null,
            original_measurement: null,
            reason: 'Target not reached',
        },
    ],
}

describe('explicit refit review', () => {
    it('shows each proposed split bullet and omitted details before acceptance', async () => {
        vi.mocked(previewRefit).mockResolvedValue({
            ...preview,
            proposals: [
                {
                    ...preview.proposals[0],
                    text: 'Built parser\nEvaluated outputs',
                    proposed_bullets: ['Built parser', 'Evaluated outputs'],
                    measurements: [
                        {
                            ratio: 0.94,
                            width_pt: 376,
                            available_pt: 400,
                            lines: 1,
                        },
                        {
                            ratio: 0.96,
                            width_pt: 384,
                            available_pt: 400,
                            lines: 1,
                        },
                    ],
                    dropped: ['Pandas'],
                    action: 'split',
                },
            ],
        })
        render(<RefitControl resumeId="r" onApplied={vi.fn()} />)
        fireEvent.click(
            screen.getByRole('button', { name: 'Refit to current style' })
        )
        fireEvent.click(screen.getByRole('button', { name: 'Preview changes' }))
        expect(await screen.findByText(/Built parser/)).toHaveTextContent(
            '94% width'
        )
        expect(screen.getByText(/Evaluated outputs/)).toHaveTextContent(
            '96% width'
        )
        expect(
            screen.getByText(/Omitted lower-priority details/)
        ).toHaveTextContent('Pandas')
        expect(
            screen.getByLabelText('Accept bullet change (key projects)')
        ).not.toBeChecked()
    })

    it('protects manual entries by default and saves only checked changes', async () => {
        vi.mocked(previewRefit).mockResolvedValue(preview)
        vi.mocked(applyRefit).mockResolvedValue({ pdf: 'pdf', latex: 'latex' })
        const applied = vi.fn().mockResolvedValue(undefined)
        render(<RefitControl resumeId="r" onApplied={applied} />)
        fireEvent.click(
            screen.getByRole('button', { name: 'Refit to current style' })
        )
        expect(
            screen.getByLabelText(
                'Include manually edited and existing content'
            )
        ).not.toBeChecked()
        fireEvent.click(screen.getByRole('button', { name: 'Preview changes' }))
        await screen.findByText('Revised Python')
        expect(previewRefit).toHaveBeenCalledWith('r', false)
        expect(applyRefit).not.toHaveBeenCalled()
        expect(
            screen.getByRole('button', { name: 'Save accepted changes' })
        ).toBeDisabled()
        const selections = screen.getAllByLabelText(
            'Accept bullet change (key projects)'
        )
        expect(selections[0]).not.toBeChecked()
        fireEvent.click(selections[0])
        fireEvent.click(
            screen.getByRole('button', { name: 'Save accepted changes' })
        )
        await waitFor(() =>
            expect(applyRefit).toHaveBeenCalledWith('r', 'signed', ['0'])
        )
        expect(applied).toHaveBeenCalledWith({ pdf: 'pdf', latex: 'latex' })
    })

    it('shows a measured project summary proposal for explicit acceptance', async () => {
        vi.mocked(previewRefit).mockResolvedValue({
            ...preview,
            proposals: [
                {
                    ...preview.proposals[0],
                    kind: 'summary',
                    path: [0, 'summary', 0],
                    original: 'A long project summary listing all tools',
                    text: 'A concise project summary',
                    measurement: {
                        ratio: 0.82,
                        width_pt: 328,
                        available_pt: 400,
                        lines: 1,
                    },
                },
            ],
        })
        render(<RefitControl resumeId="r" onApplied={vi.fn()} />)
        fireEvent.click(
            screen.getByRole('button', { name: 'Refit to current style' })
        )
        fireEvent.click(screen.getByRole('button', { name: 'Preview changes' }))
        expect(
            await screen.findByText('A concise project summary')
        ).toBeInTheDocument()
        expect(
            screen.getByLabelText(
                'Accept project summary change (key projects)'
            )
        ).not.toBeChecked()
    })

    it('requires a fresh preview when manual inclusion changes', async () => {
        vi.mocked(previewRefit).mockResolvedValue(preview)
        render(<RefitControl resumeId="r" onApplied={vi.fn()} />)
        fireEvent.click(
            screen.getByRole('button', { name: 'Refit to current style' })
        )
        fireEvent.click(screen.getByRole('button', { name: 'Preview changes' }))
        await screen.findByText('Revised Python')
        fireEvent.click(
            screen.getByLabelText(
                'Include manually edited and existing content'
            )
        )
        expect(screen.queryByText('Revised Python')).not.toBeInTheDocument()
        fireEvent.click(screen.getByRole('button', { name: 'Preview changes' }))
        await waitFor(() =>
            expect(previewRefit).toHaveBeenLastCalledWith('r', true)
        )
    })

    it('shows a specific model outage rather than suggesting there were no necessary edits', async () => {
        const failure = {
            code: 'model_unavailable',
            stage: 'wording_optimization',
            message:
                'Gemini is temporarily unavailable (HTTP 503; service busy). Try Preview changes again later.',
            retryable: true,
        }
        vi.mocked(previewRefit).mockResolvedValue({
            ...preview,
            proposals: [],
            errors: [failure],
            reports: [
                {
                    ...preview.proposals[0],
                    text: preview.proposals[0].original,
                    status: 'unfitted',
                    error: failure,
                    measurement: {
                        ratio: 0.5,
                        width_pt: 200,
                        available_pt: 400,
                        lines: 1,
                    },
                },
            ],
        })
        render(<RefitControl resumeId="r" onApplied={vi.fn()} />)
        fireEvent.click(
            screen.getByRole('button', { name: 'Refit to current style' })
        )
        fireEvent.click(screen.getByRole('button', { name: 'Preview changes' }))
        expect(await screen.findByRole('alert')).toHaveTextContent('HTTP 503')
        expect(
            screen.getByText(
                'No proposals could be generated because fitting failed.'
            )
        ).toBeInTheDocument()
        expect(
            screen.queryByText('No wording changes proposed.')
        ).not.toBeInTheDocument()
        expect(screen.getByRole('status')).toHaveTextContent('50% width')
        expect(applyRefit).not.toHaveBeenCalled()
    })
})
