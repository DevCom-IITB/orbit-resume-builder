import json
from pathlib import Path

import jsonschema

from resume_renderer.JSONSchema.jsonschema import get_schema
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


RESULTS_DIR = Path(__file__).resolve().parent / "llm_results"
FULL_RESUME_FIXTURE = RESULTS_DIR / "full_resume_generated_json.json"


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


def load_full_resume_fixture() -> dict:
    return json.loads(FULL_RESUME_FIXTURE.read_text(encoding="utf-8"))


def test_user_input_to_full_pdf(tmp_path):
    """
    End-to-end test:

    static JSON fixture for each section
    -> JSON schema validation
    -> JSON to LaTeX converters
    -> Docker LaTeX renderer
    -> final PDF file
    """
    resume_data = load_full_resume_fixture()

    for section_type, output in resume_data.items():
        schema = get_schema(section_type)
        jsonschema.validate(instance=output, schema=schema)

    latex_content = build_latex_from_resume_json(resume_data)

    pdf_bytes = compile_latex(latex_content)

    pdf_output_path = tmp_path / "full_resume_generated_from_user_input.pdf"
    pdf_output_path.write_bytes(pdf_bytes)

    assert pdf_output_path.exists()
    assert pdf_output_path.stat().st_size > 0