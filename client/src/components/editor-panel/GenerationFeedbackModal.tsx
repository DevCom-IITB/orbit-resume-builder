import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import styled, { keyframes } from 'styled-components'
import { X, RefreshCw, PenLine } from 'lucide-react'
import type { LLMGenerationErrorPayload } from '../../lib/api'

const fadeIn = keyframes`
  from { opacity: 0; }
  to { opacity: 1; }
`

const scaleUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
`

const Overlay = styled.div`
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.4);
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    padding: 16px;
    animation: ${fadeIn} 0.15s ease-out;
`

const ModalCard = styled.div`
    background: #ffffff;
    border-radius: 14px;
    width: 470px;
    max-width: calc(100vw - 32px);
    border: 1px solid #0f0c0ca9;
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.14), 0 0 1px 1px rgba(0, 0, 0, 0.04);
    overflow: hidden;
    animation: ${scaleUp} 0.18s ease-out;
    display: flex;
    flex-direction: column;
    font-family: 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
`

const ModalHeader = styled.div`
    padding: 24px 24px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
`

const ModalTitle = styled.h2`
    font-size: 1.25rem;
    font-weight: 700;
    padding-left: 10px;
    justify-self: center;
    color: #000000ff;
    margin: 0;
    font-family: 'Lato', sans-serif;
    letter-spacing: -0.01em;
`

const CloseButton = styled.button`
    background: transparent;
    border: none;
    cursor: pointer;
    color: #4b5563;
    padding: 4px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;

    &:hover {
        background: #f1f5f9;
        color: #111827;
    }
`

const ModalBody = styled.div`
    padding: 0 24px 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
`

const DescriptionText = styled.p`
    font-size: 14.5px;
    font-weight: 500;
    color: #03050aff;
    line-height: 1.6;
    margin: 0;
    font-family: 'Lato', sans-serif;
`

const Subtext = styled.p`
    font-size: 13px;
    font-weight: 500;
    color: #292e35ff;
    line-height: 1.55;
    margin: 0;
    font-family: 'Lato', sans-serif;
`

const StatusPanel = styled.div`
    background: #ededed14;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 25px;
    font-style: italic;
    display: flex;
    align-items: center;
    justify-content: space-between;
`

const StatusLabel = styled.span`
    font-size: 13.5px;
    color: #00184fff;
    font-weight: 500;
    font-family: 'Lato', sans-serif;
`

const StatusValue = styled.span`
    font-size: 15px;
    font-weight: 700;
    color: #2646f2;
    font-family: 'Lato', sans-serif;
    font-variant-numeric: tabular-nums;
`

const ModalFooter = styled.div`
    padding: 0px 24px 8px 8px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    background: #ffffff;
`

const ActionButton = styled.button<{ $outline?: boolean }>`
    padding: 8px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    font-family: 'Lato', sans-serif;
    cursor: pointer;
    transition: all 0.18s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;

    ${({ $outline }) =>
        $outline
            ? `
        background: #ffffff;
        color: #2646f2;
        border: 1.5px solid #2646f2;
        &:hover {
          background: #f8f9ff;
        }
      `
            : `
        background: #2646f2;
        color: #ffffff;
        border: 1px solid #2646f2;
        &:hover {
          background: #1d38cb;
          border-color: #1d38cb;
        }
      `}
`

interface GenerationFeedbackModalProps {
    feedback: LLMGenerationErrorPayload | null
    onClose: () => void
    onRetry?: () => void
    onEditInput?: () => void
}

function formatDuration(seconds: number): string {
    if (seconds <= 0) return '0s'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (mins > 0) {
        return `${mins}m ${secs.toString().padStart(2, '0')}s`
    }
    return `${secs}s`
}

function formatTimeString(isoString?: string): string {
    if (!isoString) return ''
    try {
        const date = new Date(isoString)
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
        return isoString
    }
}

export const GenerationFeedbackModal: React.FC<GenerationFeedbackModalProps> = ({
    feedback,
    onClose,
    onRetry,
    onEditInput,
}) => {
    const [secondsRemaining, setSecondsRemaining] = useState<number>(() => {
        return feedback?.retryAfter ?? 0
    })

    useEffect(() => {
        setSecondsRemaining(feedback?.retryAfter ?? 0)
    }, [feedback?.retryAfter])

    // Live countdown timer
    useEffect(() => {
        if (!secondsRemaining || secondsRemaining <= 0) return
        const timer = setInterval(() => {
            setSecondsRemaining((prev) => (prev > 0 ? prev - 1 : 0))
        }, 1000)
        return () => clearInterval(timer)
    }, [secondsRemaining])

    if (!feedback) return null

    const status = feedback.status
    const errorType = feedback.error
    const is30MinRateLimit = status === 429 && feedback.limitType === '30_minute'
    const isDailyRateLimit = status === 429 && feedback.limitType === 'daily'
    const isRestricted = status === 403 || errorType === 'account_restricted'
    const isInvalidContent = status === 422 || errorType === 'invalid_resume_content'
    const isProviderFailure =
        status === 502 ||
        status === 500 ||
        errorType === 'llm_provider_error' ||
        errorType === 'invalid_llm_json'

    let title = 'Notice'

    if (is30MinRateLimit) {
        title = 'Generation Limit Reached'
    } else if (isDailyRateLimit) {
        title = 'Daily Limit Reached'
    } else if (isRestricted) {
        title = 'Generation Temporarily Paused'
    } else if (isInvalidContent) {
        title = 'Content Mismatch'
    } else if (isProviderFailure) {
        title = 'Generation Unavailable'
    }

    return createPortal(
        <Overlay onClick={onClose}>
            <ModalCard onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <ModalHeader>
                    <ModalTitle>{title}</ModalTitle>
                    <CloseButton onClick={onClose} aria-label="Close dialog">
                        <X size={20} />
                    </CloseButton>
                </ModalHeader>

                <ModalBody>
                    {is30MinRateLimit && (
                        <>
                            <DescriptionText>
                                You have reached the short-term AI generation limit. To ensure fair
                                availability for all students on campus, generation requests are
                                briefly paused.
                            </DescriptionText>
                            {secondsRemaining > 0 && (
                                <StatusPanel>
                                    <StatusLabel>Cooldown remaining</StatusLabel>
                                    <StatusValue>{formatDuration(secondsRemaining)}</StatusValue>
                                </StatusPanel>
                            )}
                            <Subtext>
                                Manual resume editing and LaTeX compilation remain fully available
                                while the cooldown resets.
                            </Subtext>
                        </>
                    )}

                    {isDailyRateLimit && (
                        <>
                            <DescriptionText>
                                You have reached today&apos;s AI generation allowance. Generation
                                will be available again when the daily quota resets.
                            </DescriptionText>
                            {feedback.resetAt && (
                                <StatusPanel>
                                    <StatusLabel>Quota resets at</StatusLabel>
                                    <StatusValue>{formatTimeString(feedback.resetAt)}</StatusValue>
                                </StatusPanel>
                            )}
                            {secondsRemaining > 0 && !feedback.resetAt && (
                                <StatusPanel>
                                    <StatusLabel>Reset in approximately</StatusLabel>
                                    <StatusValue>{formatDuration(secondsRemaining)}</StatusValue>
                                </StatusPanel>
                            )}
                            <Subtext>
                                You can continue editing, rearranging sections, and rendering your
                                resume PDF as normal.
                            </Subtext>
                        </>
                    )}

                    {isRestricted && (
                        <>
                            <DescriptionText>
                                AI generation is temporarily restricted for this account following
                                repeated policy flags or off-topic inputs.
                            </DescriptionText>
                            {feedback.blockedUntil && (
                                <StatusPanel>
                                    <StatusLabel>Access restores at</StatusLabel>
                                    <StatusValue>{formatTimeString(feedback.blockedUntil)}</StatusValue>
                                </StatusPanel>
                            )}
                            <Subtext>
                                You may continue manual resume editing and LaTeX rendering without
                                interruption.
                            </Subtext>
                        </>
                    )}

                    {isInvalidContent && (
                        <>
                            <DescriptionText>
                                {feedback.message ||
                                    'The input provided does not appear to contain content relevant to this resume section.'}
                            </DescriptionText>
                            <Subtext>
                                Please verify that your rough notes include relevant achievements,
                                metrics, titles, or technical responsibilities suited for this specific
                                section.
                            </Subtext>
                        </>
                    )}

                    {isProviderFailure && (
                        <>
                            <DescriptionText>
                                {feedback.message ||
                                    'The AI generation service is currently experiencing high load and could not complete this request.'}
                            </DescriptionText>
                            <Subtext>
                                Your entered notes have been preserved. You can click Retry below or try
                                again in a moment.
                            </Subtext>
                        </>
                    )}
                </ModalBody>

                <ModalFooter>
                    {isInvalidContent && onEditInput && (
                        <ActionButton
                            $outline
                            onClick={() => {
                                onClose()
                                onEditInput()
                            }}
                        >
                            <PenLine size={14} />
                            Edit Input
                        </ActionButton>
                    )}

                    {isProviderFailure && onRetry && (
                        <ActionButton
                            $outline
                            onClick={() => {
                                onClose()
                                onRetry()
                            }}
                        >
                            <RefreshCw size={14} />
                            Retry
                        </ActionButton>
                    )}

                    <ActionButton onClick={onClose}>Close</ActionButton>
                </ModalFooter>
            </ModalCard>
        </Overlay>,
        document.body
    )
}
