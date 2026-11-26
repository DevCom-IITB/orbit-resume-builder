from resume_renderer.JSONSchema.jsonschema import get_schema
from .test_inputs import TEST_INPUTS_BY_SECTION

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")


BULLET_SECTIONS = {"professional_experience", "key_projects"}

RESULTS_DIR = Path(__file__).resolve().parent / "llm_results"


def load_llm_results(section_type: str) -> list[dict]:
    results_file = RESULTS_DIR / f"llm_results_{section_type}.json"
    return json.loads(results_file.read_text(encoding="utf-8"))


def bullet_has_acceptable_length(bullet: str) -> bool:
    """
    Approximate check for the resume whitespace/line-fill requirement.

    If a bullet is too short, it may leave too much blank space in the resume.
    We use word count as a simple proxy.
    """
    word_count = len(bullet.split())
    return 15 <= word_count <= 35


def extract_bullets(section_type: str, output):
    """
    Extract bullets from sections that contain bullet points.

    professional_experience output shape:
    [
        {
            "title": "",
            "organisation": "",
            "location": "",
            "timeline": "",
            "bullets": []
        }
    ]

    key_projects output shape:
    [
        {
            "title": "",
            "guide": "",
            "location": "",
            "timeline": "",
            "bullets": []
        }
    ]
    """
    if section_type not in BULLET_SECTIONS:
        return []

    bullets = []

    for entry in output:
        bullets.extend(entry.get("bullets", []))

    return bullets


# These fixtures are recorded LLM outputs from before the schema change in
# 5dba970 ("fixed issues with pdf gen"), so they no longer validate. They need
# to be regenerated with a real LLM run; editing them by hand would make them
# fake "recorded" outputs. strict=True flags the marker once they pass again.
STALE_FIXTURE_SECTIONS = {
    "header",
    "education",
    "professional_experience",
    "scholastic_achievements",
}


def _section_params():
    for section_type, inputs in TEST_INPUTS_BY_SECTION.items():
        marks = ()
        if section_type in STALE_FIXTURE_SECTIONS:
            marks = pytest.mark.xfail(
                reason="Recorded fixture predates the current JSON schema; regenerate it.",
                strict=True,
            )
        yield pytest.param(section_type, inputs, marks=marks, id=section_type)


@pytest.mark.parametrize("section_type,inputs", list(_section_params()))
def test_llm_prompt_outputs_match_schema(section_type, inputs):
    """
    Integration test for LLM prompt outputs using static fixtures.

    For each resume section:
    1. Loads a stored JSON response.
    2. Validates the JSON against the section schema.
    3. Checks bullet length for resume whitespace/line-fill requirement.
    """
    schema = get_schema(section_type)
    results = load_llm_results(section_type)

    assert results, f"No stored results for section: {section_type}"

    stored_inputs = [entry["input"] for entry in results]
    assert stored_inputs == inputs, (
        f"Stored fixtures are out of sync for section: {section_type}"
    )

    for index, entry in enumerate(results, start=1):
        output = entry["output"]

        assert entry["section_type"] == section_type, (
            f"Unexpected section type in fixture #{index}: {entry['section_type']}"
        )

        # Validate output structure against JSON schema
        jsonschema.validate(instance=output, schema=schema)

        # Validate bullet length for sections with bullets
        bullets = extract_bullets(section_type, output)

        for bullet in bullets:
            word_count = len(bullet.split())

            assert isinstance(bullet, str), (
                f"\nBullet is not a string."
                f"\nSection: {section_type}"
                f"\nInput: {entry['input']}"
                f"\nBullet value: {bullet}"
            )

            assert bullet_has_acceptable_length(bullet), (
                f"\nBullet length issue in section: {section_type}"
                f"\nInput: {entry['input']}"
                f"\nBullet: {bullet}"
                f"\nWord count: {word_count}"
                f"\nExpected word count: 18 to 35"
            )
