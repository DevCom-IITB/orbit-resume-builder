import styled from 'styled-components'
const ToggleGroupRow = styled.div`
    display: flex;
    gap: 4px;
`

const ToggleButton = styled.button<{ $active: boolean }>`
    flex: 1;
    padding: 6px 0;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid ${({ $active }) => ($active ? '#2646f2' : '#d1d5db')};
    border-radius: 6px;
    background: ${({ $active }) => ($active ? '#2646f2' : '#fff')};
    color: ${({ $active }) => ($active ? '#fff' : '#374151')};
    cursor: pointer;
    font-family: inherit;
    transition: all 0.15s;
`
interface ToggleOption<T extends string | number = string | number> {
    label: string
    value: T
}

export default function ToggleGroup<T extends string | number>({
    options,
    value,
    onChange,
}: {
    options: ToggleOption<T>[]
    value: T
    onChange: (v: T) => void
}) {
    return (
        <ToggleGroupRow>
            {options.map((opt) => (
                <ToggleButton
                    key={opt.value}
                    type="button"
                    aria-pressed={value === opt.value}
                    $active={value === opt.value}
                    onClick={() => onChange(opt.value)}
                >
                    {opt.label}
                </ToggleButton>
            ))}
        </ToggleGroupRow>
    )
}
