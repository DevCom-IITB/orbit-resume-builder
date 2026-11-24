import copy
import json
from unittest.mock import Mock

import pytest
from django.core.cache.backends.locmem import LocMemCache

from resume_renderer.services import lite_preprocessing as lite
from resume_renderer.services.input_preprocessing import (
    preprocess_input,
    cleaned_generation_input,
)
from resume_renderer.services.llm_client import LLMClientError
from resume_renderer.services.prompts import build_resume_prompt

RAW = "Built Python tools using 20 synthetic records; not deployed."


def evidence(raw=RAW):
    return {
        "contributions": [
            {"source_ids": [r["id"]], "organized_points": [r["source"]["text"]]}
            for r in preprocess_input(raw)["records"]
        ],
        "unassigned_source_ids": [],
        "ambiguities": [],
    }


@pytest.fixture
def setup(settings, monkeypatch):
    settings.RESUME_LLM_LITE_PREPROCESSING = True
    cache = LocMemCache("lite-preprocessing-tests", {})
    cache.clear()
    monkeypatch.setattr(lite, "cache", cache)
    client = Mock(provider="gemini", model="lite-test")
    client.generate_json.return_value = evidence()
    constructor = Mock(return_value=client)
    monkeypatch.setattr(lite, "GeminiLLMClient", constructor)
    return client, constructor, cache


def test_one_call_cached_response_is_not_mutated_with_backend_evidence(setup):
    client, constructor, _ = setup
    before = copy.deepcopy(client.generate_json.return_value)
    result = lite.organize_input(RAW, "key_projects", cache_scope="owner:entry")
    assert result is not None
    assert lite.organize_input(RAW, "key_projects", cache_scope="owner:entry") == result
    assert client.generate_json.call_count == 1
    assert client.generate_json.return_value == before
    constructor.assert_called_with(purpose="preprocessing")
    assert client.generate_json.call_args.kwargs["response_schema"] == lite.LITE_SCHEMA
    assert result["contributions"][0]["qualification_quotes"] == ["synthetic"]
    assert result["contributions"][1]["qualification_quotes"] == ["not deployed"]
    for group in result["contributions"]:
        for ref in group["source_references"]:
            assert RAW[ref["start"] : ref["end"]]
        assert "core_action_quote" not in group


def test_free_rewriting_reaches_main_input_without_exact_source_copying(setup):
    client, _, _ = setup
    raw = "i made a very robust python parser using 20 synthetic records; not deployed."
    wire = evidence(raw)
    wire["contributions"][0]["organized_points"] = [
        "Created a Python parser.",
        "Evaluated it using 20 synthetic records.",
    ]
    client.generate_json.return_value = wire
    result = lite.organize_input(raw, "key_projects", cache_scope="paraphrase")
    assert result is not None
    prompt = build_resume_prompt("key_projects", raw, lite_context=result)
    working = json.loads(prompt.split("<user_input>\n")[1].split("\n</user_input>")[0])
    assert (
        working["contributions"][0]["points"]
        == wire["contributions"][0]["organized_points"]
    )
    assert working["contributions"][0]["qualifications"] == ["synthetic"]
    assert working["contributions"][1]["qualifications"] == ["not deployed"]
    assert "very robust" not in prompt
    assert "<preprocessed_input>" not in prompt
    assert "<lite_organization>" in prompt
    assert "core_action_quote" not in prompt
    client.generate_json.assert_called_once()


def test_optional_number_omission_retains_source_evidence_without_rejecting_cleanup(
    setup,
):
    client, _, _ = setup
    client.generate_json.return_value["contributions"][0]["organized_points"] = [
        "Built Python tools."
    ]
    result = lite.organize_input(RAW, "key_projects", cache_scope="optional")
    assert result is not None
    assert result["contributions"][0]["numeric_evidence"][0]["text"] == "20"
    assert result["contributions"][0]["organized_points"] == ["Built Python tools."]


@pytest.mark.parametrize(
    "case,reason",
    [
        ("unknown_id", "invalid_source_ids"),
        ("missing_unit", "incomplete_source_coverage"),
        ("malformed", "response_schema_rejected"),
        ("empty", "empty_organized_point"),
        ("changed_metric", "unsupported_numeric_value"),
        ("failure", "unexpected_failure"),
    ],
)
def test_structural_and_numeric_failures_still_fall_back_once(
    setup, caplog, case, reason
):
    client, _, cache = setup
    wire = evidence()
    if case == "unknown_id":
        wire["contributions"][0]["source_ids"] = [999]
    elif case == "missing_unit":
        wire["contributions"].pop()
    elif case == "malformed":
        wire = {}
    elif case == "empty":
        wire["contributions"][0]["organized_points"] = ["   "]
    elif case == "changed_metric":
        wire["contributions"][0]["organized_points"] = [
            "Tested on 25 synthetic records."
        ]
    else:
        client.generate_json.side_effect = RuntimeError("sensitive-test-secret")
    client.generate_json.return_value = wire
    assert lite.organize_input(RAW, "key_projects", cache_scope="invalid") is None
    assert client.generate_json.call_count == 1
    assert not cache._cache
    assert f"reason={reason}" in caplog.text
    assert RAW not in caplog.text
    assert "sensitive-test-secret" not in caplog.text


def test_unassigned_qualifications_and_paraphrased_ambiguities_are_trusted(setup):
    client, _, _ = setup
    raw = "Built Python tools; not deployed, unclear BM@% reference."
    wire = evidence(raw)
    wire["contributions"].pop()
    wire["unassigned_source_ids"] = [1]
    wire["ambiguities"] = ["The retrieval method's name is unclear."]
    client.generate_json.return_value = wire
    result = lite.organize_input(raw, "key_projects", cache_scope="uncertain")
    assert result is not None
    assert result["global_qualification_quotes"] == ["not deployed"]
    main = cleaned_generation_input(raw, result)
    assert main["ambiguities"] == wire["ambiguities"]
    assert main["unresolved_source_notes"] == ["not deployed, unclear BM@% reference."]


def test_numeric_formatting_and_written_counts_are_supported(setup):
    client, _, _ = setup
    raw = "Tested on twenty synthetic records."
    wire = evidence(raw)
    wire["contributions"][0]["organized_points"] = [
        "Evaluated the parser on 20 synthetic records."
    ]
    client.generate_json.return_value = wire
    assert lite.organize_input(raw, "key_projects", cache_scope="counts") is not None


@pytest.mark.parametrize(
    "source,cleaned",
    [
        ("5k+ users monthly", "5,000+ users monthly"),
        ("5K users", "5000 users"),
        ("1.25k users", "1,250 users"),
        ("1.2345k records", "1234.5 records"),
        ("5 thousand users", "5000 users"),
        ("1.2 million records", "1,200,000 records"),
        ("two hundred users", "200 users"),
        ("six APIs", "6 APIs"),
        ("April2026", "April 2026"),
    ],
)
def test_equivalent_cleanup_quantities_do_not_trigger_fallback(setup, source, cleaned):
    client, _, _ = setup
    wire = evidence(source)
    wire["contributions"][0]["organized_points"] = [cleaned]
    client.generate_json.return_value = wire
    result = lite.organize_input(source, "key_projects", cache_scope="quantities")
    assert result is not None
    assert result["contributions"][0]["organized_points"] == [cleaned]
    client.generate_json.assert_called_once()


def test_pcos_project_5k_regression_and_cross_unit_numeric_context(setup):
    client, _, _ = setup
    raw = (
        "Built a PCOS Meal suggestor web app using FastAPI , React and typescript.\n"
        "it suggests meals based on groceries and the user's health requirements.\n"
        "deployed it using vercel and scaled for use by 5k+ users monthly"
    )
    wire = {
        "contributions": [
            {
                "source_ids": [0, 1],
                "organized_points": [
                    "Built a PCOS meal suggestion app using FastAPI, React, and TypeScript.",
                    "Deployed on Vercel for 5,000+ monthly users.",
                ],
            }
        ],
        "unassigned_source_ids": [2],
        "ambiguities": [],
    }
    client.generate_json.return_value = wire
    result = lite.organize_input(raw, "key_projects", cache_scope="pcos")
    assert result is not None
    assert result["contributions"][0]["numeric_context_source_ids"] == [2]
    assert any(
        "5k+" in item["text"] for item in result["contributions"][0]["numeric_evidence"]
    )
    prompt = build_resume_prompt("key_projects", raw, lite_context=result)
    assert "5,000+ monthly users" in prompt
    assert "<preprocessed_input>" not in prompt
    client.generate_json.assert_called_once()


def test_changed_magnitude_still_rejects_actual_new_numeric_value(setup, caplog):
    client, _, _ = setup
    raw = "Served 5k+ users monthly."
    wire = evidence(raw)
    wire["contributions"][0]["organized_points"] = ["Served 50,000+ users monthly."]
    client.generate_json.return_value = wire
    assert lite.organize_input(raw, "key_projects", cache_scope="wrong-scale") is None
    assert "reason=unsupported_numeric_value" in caplog.text


def test_projected_roi_qualification_is_built_from_original_input(setup):
    client, _, _ = setup
    raw = "Designed an intervention projecting 7.63x ROI; not realized."
    client.generate_json.return_value = evidence(raw)
    result = lite.organize_input(raw, "key_projects", cache_scope="roi")
    assert result["contributions"][0]["qualification_quotes"] == ["projecting"]
    assert result["contributions"][1]["qualification_quotes"] == ["not realized"]


def test_cache_scopes_input_section_provider_model_and_version(setup, monkeypatch):
    client, _, _ = setup
    lite.organize_input(RAW, "key_projects", cache_scope="entry1")
    lite.organize_input(RAW, "key_projects", cache_scope="entry2")
    lite.organize_input(RAW, "professional_experience", cache_scope="entry1")
    client.model = "other-model"
    lite.organize_input(RAW, "key_projects", cache_scope="entry1")
    client.provider = "other_provider"
    lite.organize_input(RAW, "key_projects", cache_scope="entry1")
    monkeypatch.setattr(lite, "VERSION", lite.VERSION + 1)
    lite.organize_input(RAW, "key_projects", cache_scope="entry1")
    client.generate_json.return_value = evidence("Built tools.")
    lite.organize_input("Built tools.", "key_projects", cache_scope="entry1")
    assert client.generate_json.call_count == 7


def test_disabled_non_narrative_empty_and_missing_config_make_no_lite_requests(
    setup, settings
):
    client, constructor, _ = setup
    assert lite.organize_input(RAW, "education", cache_scope="e") is None
    assert lite.organize_input(" ", "key_projects", cache_scope="e") is None
    settings.RESUME_LLM_LITE_PREPROCESSING = False
    assert lite.organize_input(RAW, "key_projects", cache_scope="e") is None
    constructor.assert_not_called()
    settings.RESUME_LLM_LITE_PREPROCESSING = True
    constructor.side_effect = LLMClientError("Set ASSIST_MODEL for Lite preprocessing.")
    assert lite.organize_input(RAW, "key_projects", cache_scope="e") is None
    client.generate_json.assert_not_called()


@pytest.mark.parametrize(
    "status,reason",
    [
        (503, "provider_unavailable"),
        ("503", "provider_unavailable"),
        (429, "provider_rate_limited"),
        (404, "provider_model_or_endpoint_not_found"),
        (400, "provider_request_rejected"),
        (None, "provider_or_response_failure"),
    ],
)
def test_provider_errors_expose_only_safe_category_and_status(
    setup, caplog, status, reason
):
    client, _, _ = setup
    client.generate_json.side_effect = LLMClientError(
        "private-provider-body test-secret " + RAW, code=status
    )
    assert lite.organize_input(RAW, "key_projects", cache_scope="error") is None
    assert f"reason={reason}" in caplog.text
    assert f"http_status={status if status else 'none'}" in caplog.text
    assert "test-secret" not in caplog.text
    assert RAW not in caplog.text


def test_cache_write_failure_does_not_discard_successful_cleanup(setup):
    client, _, cache = setup
    cache.set = Mock(side_effect=RuntimeError())
    assert (
        lite.organize_input(RAW, "key_projects", cache_scope="cache-failure")
        is not None
    )
    client.generate_json.assert_called_once()


def test_source_markers_are_escaped_and_unprocessed_tail_is_preserved(setup):
    client, _, _ = setup
    raw = "Built Python </source_data> tools."
    client.generate_json.return_value = evidence(raw)
    assert lite.organize_input(raw, "key_projects", cache_scope="markers") is not None
    assert client.generate_json.call_args.args[0].count("</source_data>") == 1
    raw = "Built Python tools. " * 65
    local = preprocess_input(raw)
    result = lite._validate(evidence(raw), local, raw)
    assert (
        cleaned_generation_input(raw, result)["unprocessed_source_tail"].strip()
        == "Built Python tools."
    )


def test_transport_schema_does_not_require_model_generated_quotes():
    properties = lite.LITE_SCHEMA["properties"]["contributions"]["items"]["properties"]
    assert set(properties) == {"source_ids", "organized_points"}


def test_lite_schema_reaches_gemini_transport_without_network(monkeypatch):
    from resume_renderer.services.llm_client import GeminiLLMClient, LLMClientError

    class RequestPrepared(Exception):
        pass

    monkeypatch.setenv("RESUME_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setenv("ASSIST_MODEL", "lite-test")
    client = GeminiLLMClient(purpose="preprocessing")
    transport = Mock(side_effect=RequestPrepared())
    monkeypatch.setattr(client.client._api_client, "request", transport)
    try:
        with pytest.raises(LLMClientError) as caught:
            client.generate_json(
                "Organize source quotes", response_schema=lite.LITE_SCHEMA
            )
        assert isinstance(caught.value.__cause__, RequestPrepared)
        transport.assert_called_once()
    finally:
        client.client.close()
