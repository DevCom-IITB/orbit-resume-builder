import { useState } from 'react'
import { createPortal } from 'react-dom'
import axios from 'axios'
import { Sparkles } from 'lucide-react'
import { applyRefit, previewRefit } from '../../lib/api'
import type { RefitPreview } from '../../types/resume'

interface Props {
    resumeId: string
    onApplied: (result: { pdf?: string; latex?: string }) => Promise<void>
}

export default function RefitControl({ resumeId, onApplied }: Props) {
    const [open, setOpen] = useState(false)
    const [includeManual, setIncludeManual] = useState(false)
    const [preview, setPreview] = useState<RefitPreview | null>(null)
    const [selected, setSelected] = useState<string[]>([])
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState('')

    async function run(action: () => Promise<void>) {
        setBusy(true)
        setError('')
        try {
            await action()
        } catch (err) {
            setError(
                axios.isAxiosError<{ error: string }>(err)
                    ? (err.response?.data?.error ??
                          'Refit request failed. Please try again.')
                    : 'Refit request failed. Please try again.'
            )
        } finally {
            setBusy(false)
        }
    }

    return (
        <>
            <button
                className="section-reorder-button edit refit-button"
                onClick={() => {
                    setOpen(true)
                    setPreview(null)
                    setSelected([])
                    setIncludeManual(false)
                    setError('')
                }}
            >
                <Sparkles className="lucide-button-icon" />
                <span>Refit to current style</span>
            </button>
            {open &&
                createPortal(
                    <div className="fit-to-line-modal-overlay">
                        <div
                            className="refit-dialog"
                            role="dialog"
                            aria-modal="true"
                            aria-label="Refit to current style"
                        >
                            <h3>Refit to current style</h3>
                            <p>
                                Review wording changes for the current layout.
                                Only checked changes will be saved.
                            </p>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={includeManual}
                                    disabled={busy}
                                    onChange={(e) => {
                                        setIncludeManual(e.target.checked)
                                        setPreview(null)
                                        setSelected([])
                                    }}
                                />{' '}
                                Include manually edited and existing content
                            </label>
                            <button
                                disabled={busy}
                                onClick={() =>
                                    void run(async () => {
                                        setPreview(
                                            await previewRefit(
                                                resumeId,
                                                includeManual
                                            )
                                        )
                                        setSelected([])
                                    })
                                }
                            >
                                {busy ? 'Working...' : 'Preview changes'}
                            </button>
                            {error && <p role="alert">{error}</p>}
                            {preview && (
                                <>
                                    <p>
                                        {preview.excluded_entries} protected
                                        entries excluded.
                                    </p>
                                    {preview.errors?.map((failure) => (
                                        <p
                                            role="alert"
                                            key={`${failure.code}-${failure.stage}`}
                                        >
                                            {failure.message} Best available
                                            wording retained.
                                        </p>
                                    ))}
                                    {!preview.proposals.length && (
                                        <p>
                                            {preview.errors?.length
                                                ? 'No proposals could be generated because fitting failed.'
                                                : 'No wording changes proposed.'}
                                        </p>
                                    )}
                                    {preview.proposals.map((p) => (
                                        <article
                                            className="refit-proposal"
                                            key={p.id}
                                        >
                                            <label>
                                                <input
                                                    type="checkbox"
                                                    checked={selected.includes(
                                                        p.id
                                                    )}
                                                    disabled={busy}
                                                    onChange={(e) =>
                                                        setSelected((prev) =>
                                                            e.target.checked
                                                                ? [
                                                                      ...prev,
                                                                      p.id,
                                                                  ]
                                                                : prev.filter(
                                                                      (id) =>
                                                                          id !==
                                                                          p.id
                                                                  )
                                                        )
                                                    }
                                                />
                                                Accept{' '}
                                                {p.kind === 'summary'
                                                    ? 'project summary'
                                                    : 'bullet'}{' '}
                                                change (
                                                {p.section_key.replaceAll(
                                                    '_',
                                                    ' '
                                                )}
                                                )
                                            </label>
                                            <p>
                                                <strong>Original:</strong>{' '}
                                                {p.original}
                                            </p>
                                            {p.original_measurement && (
                                                <p>
                                                    Original:{' '}
                                                    {Math.round(
                                                        p.original_measurement
                                                            .ratio * 100
                                                    )}
                                                    % width,{' '}
                                                    {
                                                        p.original_measurement
                                                            .lines
                                                    }{' '}
                                                    line(s).
                                                </p>
                                            )}
                                            <p>
                                                <strong>Proposed:</strong>
                                            </p>
                                            {p.proposed_bullets &&
                                            p.proposed_bullets.length > 1 ? (
                                                <ul>
                                                    {p.proposed_bullets.map(
                                                        (bullet, index) => (
                                                            <li key={index}>
                                                                {bullet}
                                                                {p
                                                                    .measurements?.[
                                                                    index
                                                                ] &&
                                                                    ` (${Math.round(p.measurements[index].ratio * 100)}% width, ${p.measurements[index].lines} line(s))`}
                                                            </li>
                                                        )
                                                    )}
                                                </ul>
                                            ) : (
                                                <p>{p.text}</p>
                                            )}
                                            {p.dropped &&
                                                p.dropped.length > 0 && (
                                                    <p>
                                                        Omitted lower-priority
                                                        details:{' '}
                                                        {p.dropped.join(', ')}
                                                    </p>
                                                )}
                                            {p.added && p.added.length > 0 && (
                                                <p>
                                                    Expanded wording:{' '}
                                                    {p.added.join(', ')}
                                                </p>
                                            )}
                                            {p.short_by_pt?.some(
                                                (width) => width > 0
                                            ) && (
                                                <p>
                                                    Below minimum width by{' '}
                                                    {p.short_by_pt
                                                        .filter(
                                                            (width) => width > 0
                                                        )
                                                        .map(
                                                            (width) =>
                                                                `${width} pt`
                                                        )
                                                        .join(', ')}
                                                    .
                                                </p>
                                            )}
                                            <p>
                                                {p.status === 'fitted'
                                                    ? p.kind === 'summary'
                                                        ? 'Fits on one line.'
                                                        : 'Fits the target range.'
                                                    : 'Target not reached; best available wording retained.'}
                                                {p.measurement &&
                                                    ` ${Math.round(p.measurement.ratio * 100)}% width, ${p.measurement.lines} line(s).`}{' '}
                                                {p.reason}
                                            </p>
                                        </article>
                                    ))}
                                    {preview.reports
                                        .filter(
                                            (r) =>
                                                r.status === 'unfitted' &&
                                                r.text === r.original
                                        )
                                        .map((r, i) => (
                                            <p key={i} role="status">
                                                Unfitted{' '}
                                                {r.kind === 'summary'
                                                    ? 'project summary'
                                                    : 'bullet'}
                                                : {r.original}.{' '}
                                                {r.measurement &&
                                                    `${Math.round(r.measurement.ratio * 100)}% width, ${r.measurement.lines} line(s). `}
                                                {!r.error && r.reason}
                                            </p>
                                        ))}
                                    <button
                                        disabled={busy || selected.length === 0}
                                        onClick={() =>
                                            void run(async () => {
                                                const result = await applyRefit(
                                                    resumeId,
                                                    preview.token,
                                                    selected
                                                )
                                                await onApplied(result)
                                                setOpen(false)
                                            })
                                        }
                                    >
                                        Save accepted changes
                                    </button>
                                </>
                            )}
                            <button
                                disabled={busy}
                                onClick={() => setOpen(false)}
                            >
                                Close
                            </button>
                        </div>
                    </div>,
                    document.body
                )}
        </>
    )
}
