import io
import re
import uuid
import fitz
import pytesseract
from PIL import Image
from django.conf import settings

# ---------------------------------------------------------------------------
# Section mappings & aliases for normalizing varying resume section names
# ---------------------------------------------------------------------------
SECTION_ALIASES = {
    "education": ["education", "academic details", "academic profile", "academic background"],
    "scholastic_achievements": [
        "scholastic achievements",
        "scholastic achievement",
        "achievements",
        "achievement",
        "scholastic",
        "awards",
        "award",
        "honors",
        "honor",
        "academic achievements",
        "academic achievement",
        "scholarly achievements",
        "scholarly achievement",
        "awards and achievements",
        "awards & achievements"
    ],
    "courses": [
        "courses",
        "course",
        "relevant courses",
        "relevant course",
        "relevant coursework",
        "academic courses",
        "academic course",
        "coursework",
        "relevant courses undertaken",
        "relevant course undertaken",
        "courses taken"
    ],
    "professional_experience": [
        "professional experience",
        "work experience",
        "experience",
        "internships",
        "internship",
        "industrial experience",
        "industrial training",
        "employment history"
    ],
    "key_projects": [
        "key projects",
        "key project",
        "projects",
        "project",
        "technical projects",
        "technical project",
        "engineering exposure",
        "research projects",
        "research project",
        "academic projects",
        "academic project",
        "course projects",
        "course project",
        "personal projects",
        "personal project"
    ],
    "positions_of_responsibility": [
        "positions of responsibility",
        "position of responsibility",
        "por",
        "leadership",
        "responsibilities",
        "responsibility",
        "positions of leadership",
        "position of leadership"
    ],
    "extra_curricular": [
        "extra-curriculars",
        "extra-curricular",
        "extra curricular activities",
        "extra curricular activity",
        "extra curriculars",
        "extra curricular",
        "extra-curricular activities",
        "extra-curricular activity",
        "extracurricular",
        "extracurricular activities",
        "extracurricular activity"
    ],
    "technical_skills": ["technical skills", "technical skill", "skills", "skill", "skills & expertise", "skills and expertise", "key skills", "key skill"]
}


# ---------------------------------------------------------------------------
# Lazy-loaded Embedding & Vector DB Services
# ---------------------------------------------------------------------------
class EmbeddingService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EmbeddingService, cls).__new__(cls, *args, **kwargs)
            cls._instance.model = None
        return cls._instance

    def get_model(self):
        if self.model is None:
            # Lazy import sentence_transformers to avoid PyTorch loading at startup
            from sentence_transformers import SentenceTransformer
            # Using all-MiniLM-L6-v2 as requested (local-only execution)
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        return self.model

    def embed(self, text: str) -> list[float]:
        model = self.get_model()
        embedding = model.encode(text)
        return embedding.tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self.get_model()
        embeddings = model.encode(texts)
        return embeddings.tolist()


class ChromaService:
    def __init__(self):
        import chromadb
        persist_directory = str(settings.BASE_DIR / "chroma_db")
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="resume_chunks",
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, ids: list[str], documents: list[str], embeddings: list[list[float]], metadatas: list[dict]):
        if not ids:
            return
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def query_chunks(self, query_embedding: list[float], n_results: int = 5, where: dict = None) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )


# ---------------------------------------------------------------------------
# PDF Ingestion / Extraction logic (borrowed from REACH implementation)
# ---------------------------------------------------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    """
    Extracts text from PDF page-by-page. Falls back to OCR using pytesseract if a page is scanned.
    """
    import os
    
    pages_text = []
    with fitz.open(file_path) as doc:
        for page in doc:
            page_text = page.get_text().strip()
            if len(page_text) >= 50:
                pages_text.append(page_text)
            else:
                # Scanned page or low-text page: try OCR fallback
                try:
                    # Common Tesseract paths on Windows
                    tesseract_paths = [
                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    ]
                    for path in tesseract_paths:
                        if os.path.exists(path):
                            pytesseract.pytesseract.tesseract_cmd = path
                            break
                    
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(image).strip()
                    pages_text.append(ocr_text)
                except Exception as ocr_exc:
                    print(f"[WARN] OCR failed for page in {file_path}: {ocr_exc}")
                    pages_text.append(page_text)

    return "\n".join(pages_text).strip()


# ---------------------------------------------------------------------------
# Schema Normalization & Parser logic
# ---------------------------------------------------------------------------
def split_resume_into_sections(text: str) -> dict[str, str]:
    """
    Parses full resume text into sections using rule-based section heading alias detection.
    Appends content if a section heading resolves to the same key multiple times.
    """
    lines = text.split("\n")
    sections = {}
    current_section = None
    current_content = []

    # Flatten alias map: UPPER_CASE_ALIAS -> normalized_key
    alias_to_key = {}
    for key, aliases in SECTION_ALIASES.items():
        for alias in aliases:
            alias_to_key[alias.upper()] = key

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            if current_section:
                current_content.append(line)
            continue

        # Check if line looks like a header (short, alphanumeric + spaces + normal symbols)
        # Normalize line to search in alias map
        upper_line = trimmed.upper().replace("&", "AND").replace("-", " ")
        clean_upper = re.sub(r"[\*_#=\-\+\s]+", " ", upper_line).strip()

        matched_key = None
        if clean_upper in alias_to_key:
            matched_key = alias_to_key[clean_upper]
        else:
            # Fallback: check if header starts with an alias as a full word (e.g. "TECHNICAL PROJECTS" starts with "PROJECTS")
            for alias, key in alias_to_key.items():
                if len(clean_upper) > 4 and (clean_upper == alias or re.match(rf"^{re.escape(alias)}\b", clean_upper)):
                    matched_key = key
                    break

        if matched_key:
            # Save the accumulated content of the previous section
            if current_section:
                existing = sections.get(current_section, "")
                new_chunk = "\n".join(current_content).strip()
                if existing:
                    sections[current_section] = existing + "\n\n" + new_chunk
                else:
                    sections[current_section] = new_chunk
            current_section = matched_key
            current_content = []
        else:
            if current_section:
                current_content.append(line)
            else:
                if "header" not in sections:
                    sections["header"] = []
                sections["header"].append(line)

    # Save final section
    if current_section:
        existing = sections.get(current_section, "")
        new_chunk = "\n".join(current_content).strip()
        if existing:
            sections[current_section] = existing + "\n\n" + new_chunk
        else:
            sections[current_section] = new_chunk

    if "header" in sections and isinstance(sections["header"], list):
        sections["header"] = "\n".join(sections["header"]).strip()

    return sections


# ---------------------------------------------------------------------------
# Chunking Strategy
# ---------------------------------------------------------------------------
def chunk_section_content(section_key: str, section_text: str) -> list[dict]:
    """
    Splits a section's text into entry-level chunks (e.g. one project per chunk).
    Returns list of dicts: [{'content': str, 'entry_title': str}]
    """
    chunks = []
    if not section_text.strip():
        return chunks

    bullet_markers = ("•", "-", "*", "+", "⁃", "▪", "‣", "◦")
    bullet_regex = r"^\s*[\-\*•\+]\s+"

    # 1. Scholastic Achievements: Chunk each individual bullet point/achievement
    if section_key == "scholastic_achievements":
        lines = section_text.split("\n")
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue
            is_bullet = trimmed.startswith(bullet_markers) or re.match(bullet_regex, trimmed)
            if is_bullet:
                # Remove the bullet character and clean up
                clean_content = re.sub(r"^[\-\*•\+\u2022\u25e6\u2043⁃▪‣◦\s]+", "", trimmed).strip()
                if clean_content:
                    chunks.append({
                        "content": clean_content,
                        "entry_title": clean_content[:60] + "..." if len(clean_content) > 60 else clean_content
                    })
            else:
                # Keep non-bullet items if they aren't generic headers
                if len(trimmed) > 10 and not any(kw in trimmed.upper() for kw in ["SCHOLASTIC", "ACHIEVEMENT"]):
                    chunks.append({
                        "content": trimmed,
                        "entry_title": trimmed[:60] + "..." if len(trimmed) > 60 else trimmed
                    })
        return chunks

    # 2. Skip chunking entirely for ignored section types
    if section_key not in ["key_projects", "professional_experience", "positions_of_responsibility", "courses"]:
        # Fallback block chunker in case any other section gets called
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]
        for idx, p in enumerate(paragraphs):
            chunks.append({
                "content": p,
                "entry_title": f"{section_key.capitalize()} Block {idx+1}"
            })
        return chunks

    # 3. Projects, Experiences, and PORs: Chunk exactly one entry at a time
    lines = section_text.split("\n")
    
    # Preprocess lines to merge wrapped bullet point lines
    reconstructed_lines = []
    date_pattern = re.compile(
        r"\[\s*[A-Za-z]{3,9}\s*’?\s*\d{2,4}.*?\]|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*’?\s*\d{2,4}\b",
        re.IGNORECASE
    )
    
    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        
        is_bullet = trimmed.startswith(bullet_markers) or re.match(bullet_regex, trimmed)
        
        if reconstructed_lines and not is_bullet:
            prev_line = reconstructed_lines[-1].strip()
            prev_is_bullet = prev_line.startswith(bullet_markers) or re.match(bullet_regex, prev_line)
            
            # Let's check if the current line looks like a new entry
            has_delimiters = "|" in trimmed or "//" in trimmed or "—" in trimmed
            has_date = bool(date_pattern.search(trimmed))
            
            # If the previous line starts with a bullet (or is a continuation) and does not end with sentence-ending punctuation,
            # and the current line doesn't look like a new entry, we merge it.
            if prev_is_bullet and not prev_line.endswith((".", "!", "?")) and not has_delimiters and not has_date:
                reconstructed_lines[-1] = prev_line + " " + trimmed
                continue
                
        reconstructed_lines.append(line)

    current_entry_lines = []
    entry_title = ""

    subheading_keywords = {
        "result", "results", "impact", "testing", "test", "contribution", "responsibility",
        "detail", "description", "summary", "task", "action", "role", "tech stack",
        "technology", "technologies", "tool", "tools", "achievement", "achievements",
        "work", "scope", "research", "design", "development"
    }

    for i, line in enumerate(reconstructed_lines):
        trimmed = line.strip()
        if not trimmed:
            continue

        is_bullet = trimmed.startswith(bullet_markers) or re.match(bullet_regex, trimmed)

        # Check if we should start a new entry
        if not is_bullet and len(current_entry_lines) > 0:
            # We can only start a new entry if the current entry has already collected some bullet points
            has_bullets = any(l.strip().startswith(bullet_markers) or re.match(bullet_regex, l.strip()) for l in current_entry_lines)
            
            if has_bullets:
                is_new = False
                
                # Rule 1: Contains entry delimiters (e.g. '|', '//', '—')
                if "|" in trimmed or "//" in trimmed or "—" in trimmed:
                    is_new = True
                # Rule 2: Contains a date range
                elif date_pattern.search(trimmed):
                    is_new = True
                # Rule 3: Next line contains a date range
                else:
                    next_line = ""
                    for j in range(i + 1, len(reconstructed_lines)):
                        if reconstructed_lines[j].strip():
                            next_line = reconstructed_lines[j].strip()
                            break
                    if next_line and date_pattern.search(next_line):
                        is_new = True
                
                # Rule 4: If not any of the above, check if it's not a common subheading
                if not is_new:
                    # If it doesn't match subheading keywords, it starts a new project/experience
                    is_subheading = any(kw in trimmed.lower().split() for kw in subheading_keywords)
                    if not is_subheading:
                        # Ensure it's not a long wrapped line of a sentence
                        is_likely_title = (
                            len(trimmed) < 60
                            and (trimmed[0].isupper() or trimmed[0].isdigit())
                            and not trimmed.endswith((".", ",", ";"))
                        )
                        if is_likely_title:
                            is_new = True

                if is_new:
                    # Save completed entry
                    content = "\n".join(current_entry_lines).strip()
                    if content:
                        chunks.append({
                            "content": content,
                            "entry_title": entry_title or "Untitled Entry"
                        })
                    current_entry_lines = []
                    entry_title = ""

        if not current_entry_lines and not is_bullet:
            entry_title = trimmed[:100]

        current_entry_lines.append(line)

    # Save remaining entry
    if current_entry_lines:
        content = "\n".join(current_entry_lines).strip()
        if content:
            chunks.append({
                "content": content,
                "entry_title": entry_title or "Untitled Entry"
            })

    return chunks
