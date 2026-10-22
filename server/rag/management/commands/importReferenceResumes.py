import re
import uuid
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from rag.models import ReferenceResume
from rag.utils import (
    ChromaService,
    EmbeddingService,
    chunk_section_content,
    extract_text_from_pdf,
    split_resume_into_sections,
)

# Department aliases for mapping
DEPARTMENT_KEYWORDS = [
    ("COMPUTER SCIENCE", "COMPUTER SCIENCE"),
    ("ELECTRICAL", "ELECTRICAL"),
    ("MECHANICAL", "MECHANICAL"),
    ("CHEMICAL", "CHEMICAL"),
    ("MATHEMATICS", "MATHEMATICS"),
    ("AEROSPACE", "AEROSPACE"),
    ("CIVIL", "CIVIL"),
    ("METALLURGICAL", "METALLURGICAL"),
    ("ECONOMICS", "ECONOMICS"),
    ("INDUSTRIAL ENGINEERING", "INDUSTRIAL ENGINEERING"),
    ("ENGINEERING PHYSICS", "ENGINEERING PHYSICS"),
    ("CHEMISTRY", "CHEMISTRY"),
    ("ENERGY", "ENERGY"),
    ("ENVIRONMENTAL SCIENCE", "ENVIRONMENTAL SCIENCE"),
    ("APPLIED GEOPHYSICS", "APPLIED GEOPHYSICS"),
]


def extract_name_from_text(resume_text: str) -> str:
    if not resume_text:
        return "ANONYMOUS"

    text_lines = [line.strip() for line in resume_text.split("\n") if line.strip()]
    invalid_keywords = {
        "ACHIEVEMENT", "SCHOLASTIC", "EDUCATION", "EXPERIENCE", "PROJECTS",
        "SKILLS", "RESUME", "PAGE", "CURRICULUM", "VITAE", "SUMMARY",
        "OBJECTIVE", "EMAIL", "PHONE", "GITHUB", "LINKEDIN", "PROFILE",
        "POSITION", "INTERESTS", "AWARDS", "COURSES"
    }
    for line in text_lines[:15]:
        line_upper = line.upper()
        if any(kw in line_upper for kw in invalid_keywords):
            continue
        if "@" in line or re.search(r"\d", line):
            continue

        words = [w for w in line.split() if w.isalpha()]
        if 2 <= len(words) <= 4 and len(words) == len(line.split()):
            return line_upper

    return "ANONYMOUS"


def extract_department_from_text(resume_text: str) -> str:
    header_lines = (resume_text or "").split("\n")[:20]
    search_text = "\n".join(header_lines).upper()

    for keyword, department in DEPARTMENT_KEYWORDS:
        if re.search(r"\b" + re.escape(keyword) + r"\b", search_text):
            return department

    return "COMPUTER SCIENCE"  # Default fallback


def parse_metadata_from_path(file_path: Path, source_root: Path) -> dict:
    try:
        rel_path = file_path.relative_to(source_root)
    except ValueError:
        rel_path = file_path

    parts = rel_path.parts
    meta = {
        "resume_type": "PLACEMENT",
        "season_year": "2024-25",
        "domain": "IT-SOFTWARE",
        "company": "UNKNOWN"
    }

    if len(parts) >= 4:
        folder1 = parts[0].lower()
        if "intern" in folder1:
            meta["resume_type"] = "INTERNSHIP"
        else:
            meta["resume_type"] = "PLACEMENT"

        year_match = re.search(r"\d{4}(?:-\d{2,4})?", parts[0])
        if year_match:
            meta["season_year"] = year_match.group()

        meta["domain"] = parts[1].upper()
        meta["company"] = re.sub(r"\s*\(.*?\)", "", parts[2]).strip().upper()
    elif len(parts) == 3:
        meta["domain"] = parts[0].upper()
        meta["company"] = re.sub(r"\s*\(.*?\)", "", parts[1]).strip().upper()
    elif len(parts) == 2:
        meta["company"] = re.sub(r"\s*\(.*?\)", "", parts[0]).strip().upper()

    return meta


class Command(BaseCommand):
    help = "Bulk import reference PDFs, parse sections, generate embeddings and index into ChromaDB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            required=True,
            help="Path to root folder containing reference PDFs",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Simulate ingestion without writing to DB or Chroma",
        )

    def handle(self, *args, **options):
        source_root = Path(options["source"])
        dry_run = options["dry_run"]

        if not source_root.exists() or not source_root.is_dir():
            self.stderr.write(f"[ERROR] Source must be an existing directory: {source_root}")
            return

        self.stdout.write(f"\nScanning directory: {source_root}\n")
        all_pdfs = sorted(source_root.rglob("*.pdf"))
        total = len(all_pdfs)
        self.stdout.write(f"Found {total} PDF(s). Processing...\n")

        # Initialize Services lazily
        embed_service = EmbeddingService()
        chroma_service = ChromaService()

        success_count = 0
        skip_count = 0
        fail_count = 0

        for pdf_path in all_pdfs:
            self.stdout.write(f"Processing: {pdf_path.name}")

            # Skip if already imported in db
            if ReferenceResume.objects.filter(resume_file__endswith=pdf_path.name).exists() and not dry_run:
                self.stdout.write("  [SKIP] Already exists in database.")
                skip_count += 1
                continue

            try:
                # 1. Extract Full Text
                full_text = extract_text_from_pdf(str(pdf_path))
                if not full_text.strip():
                    self.stderr.write(f"  [ERROR] No text extracted from {pdf_path.name}")
                    fail_count += 1
                    continue

                # 2. Extract Metadata from text & path
                meta = parse_metadata_from_path(pdf_path, source_root)
                name = extract_name_from_text(full_text)
                dept = extract_department_from_text(full_text)

                # 3. Parse Sections
                sections = split_resume_into_sections(full_text)

                # 4. Process Chunks and Embeddings
                chunk_docs = []
                chunk_embeddings = []
                chunk_metadatas = []
                chunk_ids = []

                allowed_sections = [
                    "key_projects",
                    "professional_experience",
                    "positions_of_responsibility",
                    "scholastic_achievements",
                    "courses",
                ]
                for section_key, section_text in sections.items():
                    if section_key not in allowed_sections:
                        continue

                    section_chunks = chunk_section_content(section_key, section_text)
                    for idx, chunk in enumerate(section_chunks):
                        content = chunk["content"]
                        title = chunk["entry_title"]

                        chunk_id = f"{pdf_path.stem}_{section_key}_{idx}_{uuid.uuid4().hex[:6]}"
                        
                        chunk_ids.append(chunk_id)
                        chunk_docs.append(content)
                        chunk_metadatas.append({
                            "source_file": pdf_path.name,
                            "student_name": name,
                            "department": dept,
                            "company": meta["company"],
                            "domain": meta["domain"],
                            "season_year": meta["season_year"],
                            "resume_type": meta["resume_type"],
                            "section_key": section_key,
                            "entry_title": title,
                        })

                if not chunk_docs:
                    self.stderr.write(f"  [WARN] No chunks extracted from sections for {pdf_path.name}")

                if dry_run:
                    self.stdout.write(f"  [DRY RUN] Would import: {name} ({dept})")
                    self.stdout.write(f"  [DRY RUN] Generated {len(chunk_docs)} chunks.")
                    success_count += 1
                    continue

                # Generate Embeddings in batch
                embeddings = embed_service.embed_many(chunk_docs)
                chunk_embeddings.extend(embeddings)

                # 5. Save to Database & Chroma
                with transaction.atomic():
                    # Create ReferenceResume
                    with open(pdf_path, "rb") as f:
                        ref_resume = ReferenceResume.objects.create(
                            name=name,
                            department=dept,
                            company=meta["company"],
                            domain=meta["domain"],
                            season_year=meta["season_year"],
                            resume_type=meta["resume_type"],
                            resume_text=full_text,
                            resume_file=File(f, name=pdf_path.name),
                        )

                    # Update metadata with ReferenceResume database ID
                    for meta_dict in chunk_metadatas:
                        meta_dict["reference_resume_id"] = str(ref_resume.id)

                    # Add chunks to ChromaDB
                    if chunk_ids:
                        chroma_service.add_chunks(
                            ids=chunk_ids,
                            documents=chunk_docs,
                            embeddings=chunk_embeddings,
                            metadatas=chunk_metadatas,
                        )

                self.stdout.write(
                    f"  [SUCCESS] Imported {name} | {dept} | {len(chunk_docs)} chunks indexed."
                )
                success_count += 1

            except Exception as exc:
                self.stderr.write(f"  [ERROR] Ingestion failed for {pdf_path.name}: {exc}")
                fail_count += 1

        self.stdout.write(
            f"\n{'=' * 50}\n"
            f"Ingestion Completed:\n"
            f"  Successfully imported: {success_count}\n"
            f"  Skipped (already in DB): {skip_count}\n"
            f"  Failed: {fail_count}\n"
            f"{'=' * 50}\n"
        )
