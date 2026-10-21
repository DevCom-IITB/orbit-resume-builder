import React, { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import styled, { keyframes } from 'styled-components'
import { X, RefreshCw, PenLine, Clock } from 'lucide-react'
import type { LLMGenerationErrorPayload } from '../../lib/api'

const fadeIn = keyframes`
  from { opacity: 0; }
  to { opacity: 1; }
`

const slideUp = keyframes`
  from {
    opacity: 0;
    transform: translateY(8px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
`

const Overlay = styled.div`
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.45);
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
    width: 480px;
    max-width: calc(100vw - 32px);
    box-shadow:
        0 20px 48px -12px rgba(15, 23, 42, 0.22),
        0 0 0 1px rgba(15, 23, 42, 0.06);
    overflow: hidden;
    animation: ${slideUp} 0.18s ease-out;
    display: flex;
    flex-direction: column;
    font-family: 'Lato', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
`

const HeaderBanner = styled.div<{ $variant?: 'primary' | 'danger' | 'amber' }>`
    background: ${({ $variant }) => {
        switch ($variant) {
            case 'danger':
                return '#dc2626'
            case 'amber':
                return '#2563eb'
            case 'primary':
            default:
                return '#2563eb'
        }
    }};
    color: #ffffff;
    padding: 16px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
`

const HeaderLeft = styled.div`
    display: flex;
    flex-direction: column;
    gap: 4px;
`

const HeaderBadge = styled.span`
    display: inline-block;
    align-self: flex-start;
    font-size: 11px;
    font-weight: 600;
    font-family: 'Poppins', 'Lato', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: rgba(255, 255, 255, 0.18);
    color: #ffffff;
    padding: 2px 8px;
    border-radius: 999px;
`

const ModalTitle = styled.h2`
    font-size: 1.12rem;
    font-weight: 600;
    color: #ffffff;
    margin: 0;
    font-family: 'Poppins', 'Lato', sans-serif;
    letter-spacing: -0.01em;
`

const CloseButton = styled.button`
    background: transparent;
    border: none;
    cursor: pointer;
    color: rgba(255, 255, 255, 0.85);
    padding: 6px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;

    &:hover {
        background: rgba(255, 255, 255, 0.18);
        color: #ffffff;
    }
`

const ContentBody = styled.div`
    padding: 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    background: #ffffff;
`

const DescriptionText = styled.p`
    font-size: 14.5px;
    color: #334155;
    line-height: 1.6;
    margin: 0;
    font-family: 'Lato', sans-serif;
`

const GuidanceText = styled.p`
    font-size: 13.5px;
    color: #64748b;
    line-height: 1.55;
    margin: 0;
    font-family: 'Lato', sans-serif;
`

const StatusPanel = styled.div`
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
`

const StatusLabel = styled.span`
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
    font-family: 'Lato', sans-serif;
    display: flex;
    align-items: center;
    gap: 8px;
`

const StatusValue = styled.span`
    font-size: 14.5px;
    font-weight: 700;
    color: #0f172a;
    font-family: 'Poppins', 'Lato', sans-serif;
    font-variant-numeric: tabular-nums;
`

const FooterActions = styled.div`
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    background: #ffffff;
    border-top: 1px solid #f1f5f9;
`

const ActionButton = styled.button<{ $primary?: boolean }>`
    padding: 8px 18px;
    border-radius: 8px;
    font-size: 13.5px;
    font-weight: 500;
    font-family: 'Poppins', 'Lato', sans-serif;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;

    ${({ $primary }) =>
        $primary
            ? `
        background: #2563eb;
        color: #ffffff;
        border: none;
        &:hover {
          background: #1d4ed8;
        }
      `
            : `
        background: #ffffff;
        color: #475569;
        border: 1.5px solid #cbd5e1;
        &:hover {
          background: #f8fafc;
          border-color: #94a3b8;
          color: #1e293b;
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

    let badgeText = 'Notice'
    let title = 'Generation Notice'
    let bannerVariant: 'primary' | 'danger' | 'amber' = 'primary'

    if (is30MinRateLimit) {
        badgeText = 'Rate Limit'
        title = 'Generation Quota Reached'
        bannerVariant = 'primary'
    } else if (isDailyRateLimit) {
        badgeText = 'Daily Quota'
        title = 'Daily Limit Reached'
        bannerVariant = 'primary'
    } else if (isRestricted) {
        badgeText = 'Account Cooldown'
        title = 'Generation Temporarily Paused'
        bannerVariant = 'danger'
    } else if (isInvalidContent) {
        badgeText = 'Content Verification'
        title = 'Content Mismatch'
        bannerVariant = 'primary'
    } else if (isProviderFailure) {
        badgeText = 'Service Notice'
        title = 'Generation Unavailable'
        bannerVariant = 'amber'
    }

    return createPortal(
        <Overlay onClick={onClose}>
            <ModalCard onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
                <HeaderBanner $variant={bannerVariant}>
                    <HeaderLeft>
                        <HeaderBadge>{badgeText}</HeaderBadge>
                        <ModalTitle>{title}</ModalTitle>
                    </HeaderLeft>
                    <CloseButton onClick={onClose} aria-label="Close dialog">
                        <X size={19} />
                    </CloseButton>
                </HeaderBanner>

                <ContentBody>
                    {is30MinRateLimit && (
                        <>
                            <DescriptionText>
                                You have reached the short-term AI generation limit. To ensure fair
                                availability for all students on campus, generation requests are
                                briefly paused.
                            </DescriptionText>
                            {secondsRemaining > 0 && (
                                <StatusPanel>
                                    <StatusLabel>
                                        <Clock size={16} />
                                        Cooldown remaining
                                    </StatusLabel>
                                    <StatusValue>{formatDuration(secondsRemaining)}</StatusValue>
                                </StatusPanel>
                            )}
                            <GuidanceText>
                                Manual resume editing and LaTeX compilation remain fully available
                                while the cooldown resets.
                            </GuidanceText>
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
                                    <StatusLabel>
                                        <Clock size={16} />
                                        Quota resets at
                                    </StatusLabel>
                                    <StatusValue>{formatTimeString(feedback.resetAt)}</StatusValue>
                                </StatusPanel>
                            )}
                            {secondsRemaining > 0 && !feedback.resetAt && (
                                <StatusPanel>
                                    <StatusLabel>
                                        <Clock size={16} />
                                        Reset in approximately
                                    </StatusLabel>
                                    <StatusValue>{formatDuration(secondsRemaining)}</StatusValue>
                                </StatusPanel>
                            )}
                            <GuidanceText>
                                You can continue editing, rearranging sections, and rendering your
                                resume PDF as normal.
                            </GuidanceText>
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
                                    <StatusLabel>
                                        <Clock size={16} />
                                        Access restores at
                                    </StatusLabel>
                                    <StatusValue>{formatTimeString(feedback.blockedUntil)}</StatusValue>
                                </StatusPanel>
                            )}
                            <GuidanceText>
                                You may continue manual resume editing and LaTeX rendering without
                                interruption.
                            </GuidanceText>
                        </>
                    )}

                    {isInvalidContent && (
                        <>
                            <DescriptionText>
                                {feedback.message ||
                                    'The input provided does not appear to contain content relevant to this resume section.'}
                            </DescriptionText>
                            <GuidanceText>
                                Please verify that your rough notes include relevant achievements,
                                metrics, titles, or technical responsibilities suited for this specific
                                section.
                            </GuidanceText>
                        </>
                    )}

                    {isProviderFailure && (
                        <>
                            <DescriptionText>
                                {feedback.message ||
                                    'The AI generation service is currently experiencing high load and could not complete this request.'}
                            </DescriptionText>
                            <GuidanceText>
                                Your entered notes have been preserved. You can click Retry below or try
                                again in a moment.
                            </GuidanceText>
                        </>
                    )}
                </ContentBody>

                <FooterActions>
                    {isInvalidContent && onEditInput && (
                        <ActionButton
                            $primary
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
                            $primary
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
                </FooterActions>
            </ModalCard>
        </Overlay>,
        document.body
    )
}
