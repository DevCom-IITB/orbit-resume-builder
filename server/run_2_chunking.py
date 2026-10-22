import os
import sys

# Configure Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resume_builder.settings")

try:
    import django
    django.setup()
except Exception as django_exc:
    print(f"Django setup warning: {django_exc}")

from rag.utils import (
    extract_text_from_pdf,
    split_resume_into_sections,
    chunk_section_content,
)

def main():
    import sys
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    import argparse
    parser = argparse.ArgumentParser(description="Run chunking step of RAG pipeline on a resume PDF.")
    parser.add_argument(
        "--pdf",
        type=str,
        default="media/resumes/Yash_Rampuria_Amazon_2pg_VSLbtAB.pdf",
        help="Path to resume PDF file"
    )
    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf)
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at '{pdf_path}'")
        sys.exit(1)

    print("=" * 60)
    print(f"Running Chunker on: {args.pdf}")
    print("=" * 60)

    try:
        text = extract_text_from_pdf(pdf_path)
        sections = split_resume_into_sections(text)
        
        allowed_sections = [
            "key_projects",
            "professional_experience",
            "positions_of_responsibility",
            "scholastic_achievements",
            "courses",
        ]
        chunk_count = 0
        for section_key, section_text in sections.items():
            if section_key not in allowed_sections:
                continue
                
            chunks = chunk_section_content(section_key, section_text)
            print(f"\n--- Section: {section_key.upper()} ({len(chunks)} chunks) ---")
            for idx, chunk in enumerate(chunks):
                chunk_count += 1
                print(f"  * Chunk #{chunk_count} | Title: {chunk['entry_title']}")
                print("    Content:")
                print(chunk['content'])
                print("-" * 50)
                
        print(f"\nDone. Generated a total of {chunk_count} entry chunks.")
        print("=" * 60)
    except Exception as e:
        print(f"Error chunking: {e}")

if __name__ == "__main__":
    main()
