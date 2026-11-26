"""Legacy generation wording, with current schema and context plumbing retained."""

import copy
import json
from types import SimpleNamespace

import pytest

from resume_renderer.JSONSchema.jsonschema import get_schema
from resume_renderer.services.prompts import build_resume_prompt


@pytest.mark.parametrize(
    "section",
    ["professional_experience", "key_projects", "positions_of_responsibility"],
)
def test_legacy_prompt_restored_without_short_word_target(section):
    prompt = build_resume_prompt(section, "Built a Python CLI.")
    assert "15-35 words" in prompt
    assert "1 line (80–95 chars) or 2 lines (160–190 chars)" in prompt
    assert "Do not invent facts" in prompt
    assert "12–13" not in prompt
    assert "14–15" not in prompt
    assert "Current bullet constraint" not in prompt
    assert "Final bullet-writing guidance" not in prompt
    assert "8–16 words" not in prompt
    assert "Built a Python CLI." in prompt


def test_stored_requirements_schema_prior_content_and_references_preserved():
    schema = get_schema("key_projects")
    before = copy.deepcopy(schema)
    stdef = SimpleNamespace(
        llm_prompt_instructions="Stored section requirements", json_schema=schema
    )
    prompt = build_resume_prompt(
        "key_projects",
        "User input facts",
        current_content=[{"bullets": ["Prior wording"]}],
        stdef=stdef,
        retrieved_context=[{"entry_title": "Reference", "chunk": "Style example"}],
    )
    assert "Stored section requirements" in prompt
    assert "Prior wording" in prompt
    assert "Style example" in prompt
    assert "source of truth" in prompt
    assert json.dumps(schema, indent=2) in prompt
    assert schema == before


def test_non_bullet_section_keeps_existing_schema():
    prompt = build_resume_prompt("education", "B.Tech. in 2026")
    assert json.dumps(get_schema("education"), indent=2) in prompt
    assert "B.Tech. in 2026" in prompt
