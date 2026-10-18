import React, { useEffect, useState } from 'react'
import styled, { keyframes } from 'styled-components'
import {
    Clock,
    CalendarClock,
    ShieldAlert,
    AlertCircle,
    AlertTriangle,
    X,
    RefreshCw,
    PenLine,
} from 'lucide-react'
import type { LLMGenerationErrorPayload } from '../../lib/api'

const fadeIn = keyframes`
  from { opacity: 0; }
  to { opacity: 1; }
`

const scaleUp = keyframes`
  from { opacity: 0; transform: scale(0.95) translateY(12px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
`

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
`

const Overlay = styled.div`
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.65);
    backdrop-filter: blur(6px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    padding: 16px;
    animation: ${fadeIn} 0.18s ease-out;
`

const ModalCard = styled.div`
    background: #ffffff;
    border-radius: 16px;
    width: 460px;
    max-width: 100%;
    box-shadow:
        0 20px 40px -12px rgba(0, 0, 0, 0.25),
        0 0 0 1px rgba(0, 0, 0, 0.05);
    overflow: hidden;
    animation: ${scaleUp} 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
`

const HeaderSection = styled.div<{ $variant: 'warning' | 'danger' | 'purple' | 'amber' }>`
    padding: 24px 24px 16px;
    display: flex;
    align-items: flex-start;
    gap: 16px;
    border-bottom: 1px solid #f1f5f9;
    position: relative;

    background: ${({ $variant }) => {
        switch ($variant) {
            case 'danger':
                return 'linear-gradient(180deg, #fef2f2 0%, #ffffff 100%)'
            case 'purple':
                return 'linear-gradient(180deg, #faf5ff 0%, #ffffff 100%)'
            case 'amber':
                return 'linear-gradient(180deg, #fffbeb 0%, #ffffff 100%)'
            case 'warning':
            default:
                return 'linear-gradient(180deg, #eff6ff 0%, #ffffff 100%)'
        }
    }};
`

const IconContainer = styled.div<{ $variant: 'warning' | 'danger' | 'purple' | 'amber' }>`
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    background: ${({ $variant }) => {
        switch ($variant) {
            case 'danger':
                return '#fee2e2'
            case 'purple':
                return '#f3e8ff'
            case 'amber':
                return '#fef3c7'
            case 'warning':
            default:
                return '#dbeafe'
        }
    }};

    color: ${({ $variant }) => {
        switch ($variant) {
            case 'danger':
                return '#dc2626'
            case 'purple':
                return '#7e22ce'
            case 'amber':
                return '#d97706'
            case 'warning':
            default:
                return '#2563eb'
        }
    }};
`

const TitleContainer = styled.div`
    flex: 1;
`

const ModalTitle = styled.h3`
    font-size: 17px;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 4px 0;
    line-height: 1.3;
`

const Badge = styled.span<{ $variant: 'warning' | 'danger' | 'purple' | 'amber' }>`
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 2px 8px;
    border-radius: 999px;
    margin-bottom: 6px;

    background: ${({ $variant }) => {
        switch ($variant) {
            case 'danger':
                return '#fee2e2'
            case 'purple':
                return '#f3e8ff'
            case 'amber':
                return '#fef3c7'
            case 'warning':
            default:
                return '#dbeafe'
        }
    }};

    color: ${({ $variant }) => {
        switch ($variant) {
            case 'danger':
                return '#b91c1c'
            case 'purple':
                return '#6b21a8'
            case 'amber':
                return '#b45309'
            case 'warning':
            default:
                return '#1d4ed8'
        }
    }};
`

const CloseIconButton = styled.button`
    background: transparent;
    border: none;
    cursor: pointer;
    color: #94a3b8;
    padding: 4px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;

    &:hover {
        background: rgba(0, 0, 0, 0.05);
        color: #475569;
    }
`

const ContentBody = styled.div`
    padding: 20px 24px;
    font-size: 14px;
    color: #475569;
    line-height: 1.55;
    display: flex;
    flex-direction: column;
    gap: 14px;
`

const CountdownBanner = styled.div`
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
`

const CountdownTimer = styled.span`
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    font-variant-numeric: tabular-nums;
    animation: ${pulse} 2s infinite ease-in-out;
`

const TipBox = styled.div`
    background: #f8fafc;
    border-left: 3px solid #3b82f6;
    padding: 10px 14px;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    color: #334155;
`

const FooterActions = styled.div`
    padding: 16px 24px 20px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    background: #fafafa;
    border-top: 1px solid #f1f5f9;
`

const Button = styled.button<{ $primary?: boolean; $variant?: 'primary' | 'danger' }>`
    padding: 9px 18px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 6px;

    ${({ $primary, $variant }) =>
        $primary
            ? `
        background: ${$variant === 'danger' ? '#ef4444' : '#2563eb'};
        color: #ffffff;
        border: none;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
        &:hover {
          background: ${$variant === 'danger' ? '#dc2626' : '#1d4ed8'};
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
        }
      `
            : `
        background: #ffffff;
        color: #334155;
        border: 1px solid #cbd5e1;
        &:hover {
          background: #f1f5f9;
          color: #0f172a;
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

    // Live countdown interval
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

    let variant: 'warning' | 'danger' | 'purple' | 'amber' = 'warning'
    let badgeText = 'Notice'
    let title = 'Generation Notice'
    let icon = <AlertCircle size={24} />

    if (is30MinRateLimit) {
        variant = 'warning'
        badgeText = 'Rate Limit'
        title = 'AI generation limit reached'
        icon = <Clock size={24} />
    } else if (isDailyRateLimit) {
        variant = 'purple'
        badgeText = 'Daily Quota'
        title = 'Daily AI generation limit reached'
        icon = <CalendarClock size={24} />
    } else if (isRestricted) {
        variant = 'danger'
        badgeText = 'Account Restriction'
        title = 'AI generation temporarily restricted'
        icon = <ShieldAlert size={24} />
    } else if (isInvalidContent) {
        variant = 'amber'
        badgeText = 'Content Mismatch'
        title = "Content doesn't match this section"
        icon = <AlertCircle size={24} />
    } else if (isProviderFailure) {
        variant = 'danger'
        badgeText = 'Service Issue'
        title = 'Generation failed'
        icon = <AlertTriangle size={24} />
    }

    return (
        <Overlay onClick={onClose}>
            <ModalCard onClick={(e) => e.stopPropagation()}>
                <HeaderSection $variant={variant}>
                    <IconContainer $variant={variant}>{icon}</IconContainer>
                    <TitleContainer>
                        <Badge $variant={variant}>{badgeText}</Badge>
                        <ModalTitle>{title}</ModalTitle>
                    </TitleContainer>
                    <CloseIconButton onClick={onClose} aria-label="Close modal">
                        <X size={18} />
                    </CloseIconButton>
                </HeaderSection>

                <ContentBody>
                    {is30MinRateLimit && (
                        <>
                            <p>
                                You&apos;ve made several generation requests recently. To ensure fair
                                availability for all students, generation is paused for a short
                                cooldown window.
                            </p>
                            {secondsRemaining > 0 && (
                                <CountdownBanner>
                                    <span>Cooldown remaining:</span>
                                    <CountdownTimer>{formatDuration(secondsRemaining)}</CountdownTimer>
                                </CountdownBanner>
                            )}
                        </>
                    )}

                    {isDailyRateLimit && (
                        <>
                            <p>
                                You&apos;ve reached today&apos;s AI generation limit. You can use AI
                                generation again after the daily quota resets.
                            </p>
                            {feedback.resetAt && (
                                <CountdownBanner>
                                    <span>Reset time:</span>
                                    <CountdownTimer>
                                        {formatTimeString(feedback.resetAt)}
                                    </CountdownTimer>
                                </CountdownBanner>
                            )}
                            {secondsRemaining > 0 && !feedback.resetAt && (
                                <CountdownBanner>
                                    <span>Reset in approximately:</span>
                                    <CountdownTimer>{formatDuration(secondsRemaining)}</CountdownTimer>
                                </CountdownBanner>
                            )}
                        </>
                    )}

                    {isRestricted && (
                        <>
                            <p>
                                AI generation is temporarily restricted for this account due to repeated
                                policy violations or unexpected activity.
                            </p>
                            {feedback.blockedUntil && (
                                <CountdownBanner>
                                    <span>Access will be restored at:</span>
                                    <CountdownTimer>
                                        {formatTimeString(feedback.blockedUntil)}
                                    </CountdownTimer>
                                </CountdownBanner>
                            )}
                            <TipBox>
                                Normal manual editing of your resume and LaTeX rendering remain
                                fully available during this temporary cooldown.
                            </TipBox>
                        </>
                    )}

                    {isInvalidContent && (
                        <>
                            <p>
                                {feedback.message ||
                                    'The input does not appear to contain content relevant to this resume section.'}
                            </p>
                            <TipBox>
                                Please verify that your rough notes contain relevant facts, titles,
                                dates, metrics, or technical roles meant for this specific resume
                                section.
                            </TipBox>
                        </>
                    )}

                    {isProviderFailure && (
                        <>
                            <p>
                                {feedback.message ||
                                    'The AI service could not complete this request. Please try again later.'}
                            </p>
                            <TipBox>
                                Your previous text input is preserved. You can click Retry or try
                                again in a few moments.
                            </TipBox>
                        </>
                    )}
                </ContentBody>

                <FooterActions>
                    {isInvalidContent && onEditInput && (
                        <Button
                            $primary
                            onClick={() => {
                                onClose()
                                onEditInput()
                            }}
                        >
                            <PenLine size={15} />
                            Edit Input
                        </Button>
                    )}

                    {isProviderFailure && onRetry && (
                        <Button
                            $primary
                            onClick={() => {
                                onClose()
                                onRetry()
                            }}
                        >
                            <RefreshCw size={15} />
                            Retry
                        </Button>
                    )}

                    <Button onClick={onClose}>Close</Button>
                </FooterActions>
            </ModalCard>
        </Overlay>
    )
}
