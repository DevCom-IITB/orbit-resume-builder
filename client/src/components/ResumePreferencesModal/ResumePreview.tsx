import shortHeaderImg from './previewimages/Frame 48095666.png'
import longHeaderImg from './previewimages/Group 83.png'
import styled from "styled-components";
const PreviewBox = styled.div`
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  min-width: 130px;
`;

const PreviewLabel = styled.span`
  font-size: 10px;
  color: #94a3b8;
  font-weight: 500;
  text-align: center;
`;

const PreviewImage = styled.img`
  border-radius: 3px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
  transition: all 0.2s ease;
  object-fit: contain;
`;

export default function ResumePreview({
  resumeType,
  header,
  pages,
}: {
  resumeType: string;
  header: string;
  pages: number;
}) {
  const isIITB = resumeType === "iitb";
  const isLong = header === "long";

  const imgSrc = isIITB && isLong ? longHeaderImg : shortHeaderImg;

  const labelParts = [
    isIITB ? "IITB Template" : "External",
    isIITB ? (isLong ? "Long header" : "Short header") : null,
    pages === 1 ? "1 page" : "2 pages",
  ].filter(Boolean);

  const imgWidth = pages === 2 ? 55 : 108;

  return (
    <PreviewBox>
      <PreviewLabel>{labelParts.join(" · ")}</PreviewLabel>
      <div style={{ display: "flex", gap: pages === 2 ? 6 : 0, alignItems: "flex-start" }}>
        <PreviewImage src={imgSrc} alt="resume preview" width={imgWidth} />
        {pages === 2 && (
          <PreviewImage src={imgSrc} alt="resume preview page 2" width={imgWidth} />
        )}
      </div>
    </PreviewBox>
  );
}
