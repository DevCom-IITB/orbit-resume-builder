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

from rag.utils import extract_text_from_pdf

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract raw text from a resume PDF.")
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
    print(f"Extracting Raw Text from: {args.pdf}")
    print("=" * 60)

    try:
        text = extract_text_from_pdf(pdf_path)
        print(text)
        print("\n" + "=" * 60)
        print(f"Done. Extracted {len(text)} characters of text.")
        print("=" * 60)
    except Exception as e:
        print(f"Error extracting text: {e}")

if __name__ == "__main__":
    main()
