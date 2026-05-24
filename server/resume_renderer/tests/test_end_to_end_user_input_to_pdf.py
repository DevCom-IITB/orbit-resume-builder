import json
import time
from pathlib import Path

import jsonschema

from resume_renderer.JSONSchema.jsonschema import get_schema
from resume_renderer.services.llm_client import GeminiLLMClient
from resume_renderer.services.prompts import build_resume_prompt
from resume_renderer.services.renderer import compile_latex

from resume_renderer.schemas.converters.convert_header import convert_header
from resume_renderer.schemas.converters.convert_education import convert_education
from resume_renderer.schemas.converters.convert_experience import convert_experience
from resume_renderer.schemas.converters.convert_key_project import convert_key_project
from resume_renderer.schemas.converters.convert_technical_skills import (
    convert_technical_skills,
)
from resume_renderer.schemas.converters.convert_courses import convert_courses
from resume_renderer.schemas.converters.convert_pors import convert_pors
from resume_renderer.schemas.converters.convert_scholastic_achievements import (
    convert_scholastic_achievements,
)


DELAY_BETWEEN_LLM_CALLS_SECONDS = 15


USER_INPUTS = {
    "header": (
        "Kushagra Misra BTech CSE IIT Bombay email kushagra@example.com "
        "phone +91 9876543210 linkedin kushagra-misra github kushagramisra06"
    ),

    "education": (
        "BTech in Computer Science and Engineering from IIT Bombay "
        "cpi 9.22/10 year 2025-2029"
    ),

    "professional_experience": (
        "worked as frontend intern at Awaasdhan from May 2025 to July 2025 remote "
        "made website pages using react and tailwind improved ui and fixed responsiveness issues"
    ),

    "key_projects": (
        "made ai resume builder project under DevCom IIT Bombay in May 2026 using react django "
        "gemini api and latex where user enters rough points and ai converts them into resume bullets "
        "and pdf is generated"
    ),

    "technical_skills": (
        "python c++ js react django html css tailwind sql postgres git github docker figma tensorflow pytorch"
    ),

    "courses": (
        "courses done are data structures and algorithms, database management systems, operating systems, "
        "machine learning, linear algebra, probability and statistics"
    ),

    "positions_of_responsibility": (
        "developer at DevCom IIT Bombay from Mar 2025 to present working on ai resume builder "
        "and career research portal for students and professors"
    ),

    "scholastic_achievements": (
        "jee mains 99.5 percentile jee advanced rank 3809 class 12 cbse 92.3 percent "
        "class 10 icse 96.6 percent"
    ),
}


def build_latex_from_resume_json(resume_data: dict) -> str:
    latex_parts = []

    if resume_data.get("header"):
        latex_parts.append(convert_header(resume_data["header"]))

    if resume_data.get("education"):
        latex_parts.append(convert_education(resume_data["education"]))

    if resume_data.get("professional_experience"):
        latex_parts.append(convert_experience(resume_data["professional_experience"]))

    if resume_data.get("key_projects"):
        latex_parts.append(convert_key_project(resume_data["key_projects"]))

    if resume_data.get("technical_skills"):
        latex_parts.append(convert_technical_skills(resume_data["technical_skills"]))

    if resume_data.get("courses"):
        latex_parts.append(convert_courses(resume_data["courses"]))

    if resume_data.get("positions_of_responsibility"):
        latex_parts.append(convert_pors(resume_data["positions_of_responsibility"]))

    if resume_data.get("scholastic_achievements"):
        latex_parts.append(
            convert_scholastic_achievements(resume_data["scholastic_achievements"])
        )

    return "\n\n".join(latex_parts)


def test_user_input_to_full_pdf():
    """
    End-to-end test:

    rough user inputs
    -> Gemini JSON for each section
    -> JSON schema validation
    -> JSON to LaTeX converters
    -> Docker LaTeX renderer
    -> final PDF file
    """

    client = GeminiLLMClient()
    resume_data = {}

    for section_type, user_input in USER_INPUTS.items():
        print("\n" + "=" * 100)
        print(f"Generating section: {section_type}")
        print(f"User input: {user_input}")

        prompt = build_resume_prompt(section_type, user_input)
        output = client.generate_json(prompt)

        schema = get_schema(section_type)
        jsonschema.validate(instance=output, schema=schema)

        resume_data[section_type] = output

        print("Generated JSON:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print("=" * 100)

        time.sleep(DELAY_BETWEEN_LLM_CALLS_SECONDS)

    results_dir = Path("resume_renderer/tests/llm_results")
    results_dir.mkdir(parents=True, exist_ok=True)

    json_output_path = results_dir / "full_resume_generated_json.json"
    json_output_path.write_text(
        json.dumps(resume_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nSaved generated JSON to: {json_output_path}")

    latex_content = build_latex_from_resume_json(resume_data)

    latex_output_path = results_dir / "full_resume_generated_latex.tex"
    latex_output_path.write_text(latex_content, encoding="utf-8")

    print(f"Saved generated LaTeX to: {latex_output_path}")

    print("Compiling LaTeX into PDF using Docker...")
    pdf_bytes = compile_latex(latex_content)

    pdf_output_path = results_dir / "full_resume_generated_from_user_input.pdf"
    pdf_output_path.write_bytes(pdf_bytes)

    print(f"PDF generated successfully at: {pdf_output_path}")

    assert pdf_output_path.exists()
    assert pdf_output_path.stat().st_size > 0