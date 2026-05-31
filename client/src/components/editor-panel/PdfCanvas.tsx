import styled, { keyframes } from 'styled-components'

const pulse = keyframes`
  0% { opacity: 0.6; }
  50% { opacity: 0.2; }
  100% { opacity: 0.6; }
`

const CanvasWrapper = styled.div`
  width: 100%;
  flex-grow: 1; /* Stretches to fill the remaining height below the button */
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

interface PdfCanvasProps {
  url: string | null
  isLoading: boolean
}

export default function PdfCanvas({ url, isLoading }: PdfCanvasProps) {
  if (isLoading) {
    return (
      <CanvasWrapper>
        <Skeleton />
      </CanvasWrapper>
    )
  }

  if (url) {
    return (
      <CanvasWrapper>
        <iframe
          src={`${url}#toolbar=0`}
          width="100%"
          height="100%"
          style={{ border: 'none' }}
          title="Resume PDF"
        />
      </CanvasWrapper>
    )
  }

  return (
    <CanvasWrapper>
      <EmptyText>PDF Preview</EmptyText>
    </CanvasWrapper>
  )
}
