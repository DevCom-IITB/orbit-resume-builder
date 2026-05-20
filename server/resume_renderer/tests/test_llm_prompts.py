import json
import time
from pathlib import Path

import jsonschema
import pytest

from resume_renderer.JSONSchema.jsonschema import get_schema
from resume_renderer.services.llm_client import GeminiLLMClient
from resume_renderer.services.prompts import build_resume_prompt
from .test_inputs import TEST_INPUTS_BY_SECTION


BULLET_SECTIONS = {"professional_experience", "key_projects"}

# Gemini free tier can rate-limit quickly.
# 15 seconds keeps calls safer if the limit is around 5 requests/minute.
DELAY_BETWEEN_LLM_CALLS_SECONDS = 15

# Store generated outputs here so you can manually inspect them.
RESULTS_DIR = Path("resume_renderer/tests/llm_results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


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


@pytest.mark.parametrize("section_type,inputs", TEST_INPUTS_BY_SECTION.items())
def test_llm_prompt_outputs_match_schema(section_type, inputs):
    """
    Integration test for LLM prompts.

    For each resume section:
    1. Builds a stateless prompt.
    2. Sends the prompt to Gemini.
    3. Parses the response as JSON.
    4. Validates the JSON against the section schema.
    5. Checks bullet length for resume whitespace/line-fill requirement.
    6. Saves outputs to a JSON file for manual review.

    Note:
    This test makes real Gemini API calls, so it may fail if quota is exceeded.
    """
    client = GeminiLLMClient()
    schema = get_schema(section_type)
    results = []

    for index, user_input in enumerate(inputs, start=1):
        prompt = build_resume_prompt(section_type, user_input)
        output = client.generate_json(prompt)

        # Save current result in memory
        results.append(
            {
                "section_type": section_type,
                "test_case": index,
                "input": user_input,
                "output": output,
            }
        )

        # Print result in terminal when running pytest with -s
        print("\n" + "=" * 100)
        print(f"SECTION: {section_type}")
        print(f"TEST CASE: {index}")
        print(f"INPUT: {user_input}")
        print("OUTPUT:")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        print("=" * 100)

        # Validate output structure against JSON schema
        jsonschema.validate(instance=output, schema=schema)

        # Validate bullet length for sections with bullets
        bullets = extract_bullets(section_type, output)

        for bullet in bullets:
            word_count = len(bullet.split())

            assert isinstance(bullet, str), (
                f"\nBullet is not a string."
                f"\nSection: {section_type}"
                f"\nInput: {user_input}"
                f"\nBullet value: {bullet}"
            )

            assert bullet_has_acceptable_length(bullet), (
                f"\nBullet length issue in section: {section_type}"
                f"\nInput: {user_input}"
                f"\nBullet: {bullet}"
                f"\nWord count: {word_count}"
                f"\nExpected word count: 18 to 35"
            )

        # Delay after every call to avoid Gemini free-tier rate limit
        time.sleep(DELAY_BETWEEN_LLM_CALLS_SECONDS)

    # Save results for manual inspection
    results_file = RESULTS_DIR / f"llm_results_{section_type}.json"
    results_file.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nSaved LLM test results to: {results_file}")