import React from 'react'
import styled from 'styled-components'
import { Minus, Plus } from 'lucide-react'

const Container = styled.div<{ $disabled?: boolean }>`
    display: flex;
    flex-direction: column;
    gap: 5px;
    flex: 1 1 140px;
    min-width: 0;
    opacity: ${({ $disabled }) => ($disabled ? 0.6 : 1)};
`

const HeaderRow = styled.div`
    display: flex;
    justify-content: space-between;
    align-items: center;
`

const Label = styled.label`
    font-size: 11px;
    font-weight: 700;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.04em;
`

const ValueBadge = styled.span`
    font-size: 11px;
    font-weight: 600;
    color: #374151;
    font-variant-numeric: tabular-nums;
`

const StepperRow = styled.div`
    display: flex;
    align-items: center;
    gap: 6px;
    height: 30px;
`

const StepButton = styled.button`
    width: 24px;
    height: 24px;
    border-radius: 6px;
    border: 1px solid #d1d5db;
    background: #ffffff;
    color: #374151;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: pointer;
    flex-shrink: 0;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;

    &:hover:not(:disabled) {
        background-color: #f3f4f6;
        border-color: #9ca3af;
        color: #111827;
    }

    &:focus-visible {
        outline: 2px solid #2563eb;
        outline-offset: 1px;
    }

    &:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }
`

const SegmentTrack = styled.div`
    display: flex;
    align-items: center;
    gap: 3px;
    flex: 1;
    height: 16px;
    cursor: pointer;
`

const Segment = styled.button<{ $filled: boolean; $isDefault: boolean }>`
    flex: 1;
    height: 8px;
    border-radius: 2px;
    border: none;
    padding: 0;
    background-color: ${({ $filled }) => ($filled ? '#2563eb' : '#e5e7eb')};
    position: relative;
    cursor: pointer;
    transition: background-color 0.12s ease;

    &:hover {
        background-color: ${({ $filled }) => ($filled ? '#1d4ed8' : '#d1d5db')};
    }

    &:focus-visible {
        outline: 2px solid #2563eb;
        outline-offset: 1px;
    }

    ${({ $isDefault, $filled }) =>
        $isDefault &&
        `
        &::after {
            content: '';
            position: absolute;
            bottom: -5px;
            left: 50%;
            transform: translateX(-50%);
            width: 3px;
            height: 3px;
            border-radius: 50%;
            background-color: ${$filled ? '#2563eb' : '#9ca3af'};
        }
    `}
`

const SrOnly = styled.span`
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
`

export interface SpacingControlProps {
    label: string
    value: string
    options: string[]
    defaultValue: string
    onChange: (val: string) => void
    disabled?: boolean
}

export default function SpacingControl({
    label,
    value,
    options,
    defaultValue,
    onChange,
    disabled = false,
}: SpacingControlProps) {
    const currentIndex = Math.max(0, options.indexOf(value))
    const canDecrease = !disabled && currentIndex > 0
    const canIncrease = !disabled && currentIndex < options.length - 1

    const handleDecrease = () => {
        if (canDecrease) {
            onChange(options[currentIndex - 1])
        }
    }

    const handleIncrease = () => {
        if (canIncrease) {
            onChange(options[currentIndex + 1])
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (disabled) return
        if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            e.preventDefault()
            handleDecrease()
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            e.preventDefault()
            handleIncrease()
        }
    }

    const percentage = Math.round((parseFloat(value) || 1.0) * 100) + '%'

    return (
        <Container $disabled={disabled} role="group" aria-label={label} onKeyDown={handleKeyDown}>
            <HeaderRow>
                <Label>{label}</Label>
                <ValueBadge aria-hidden="true">{percentage}</ValueBadge>
                <SrOnly aria-live="polite">
                    {label}: {percentage}
                </SrOnly>
            </HeaderRow>
            <StepperRow>
                <StepButton
                    type="button"
                    onClick={handleDecrease}
                    disabled={!canDecrease}
                    aria-label={`Decrease ${label}`}
                    title={`Decrease ${label}`}
                >
                    <Minus size={12} strokeWidth={2.5} />
                </StepButton>

                <SegmentTrack role="radiogroup" aria-label={`${label} options`}>
                    {options.map((opt, idx) => {
                        const isFilled = idx <= currentIndex
                        const isDefault = opt === defaultValue
                        const isSelected = opt === value
                        const optPercentage = Math.round((parseFloat(opt) || 1.0) * 100) + '%'

                        return (
                            <Segment
                                key={opt}
                                type="button"
                                role="radio"
                                aria-checked={isSelected}
                                aria-label={`${label} ${optPercentage}${isDefault ? ' (Default)' : ''}`}
                                title={`${optPercentage}${isDefault ? ' (Default)' : ''}`}
                                $filled={isFilled}
                                $isDefault={isDefault}
                                disabled={disabled}
                                onClick={() => {
                                    if (!disabled && opt !== value) {
                                        onChange(opt)
                                    }
                                }}
                            />
                        )
                    })}
                </SegmentTrack>

                <StepButton
                    type="button"
                    onClick={handleIncrease}
                    disabled={!canIncrease}
                    aria-label={`Increase ${label}`}
                    title={`Increase ${label}`}
                >
                    <Plus size={12} strokeWidth={2.5} />
                </StepButton>
            </StepperRow>
        </Container>
    )
}
