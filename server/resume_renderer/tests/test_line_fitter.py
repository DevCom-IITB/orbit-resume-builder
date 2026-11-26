"""Bounded structured optimization; model calls are always stubbed."""

import copy
import json
from unittest.mock import Mock

import pytest

from resume_renderer.services import line_fitter as fitter
from resume_renderer.services.llm_client import LLMClientError


@pytest.fixture(autouse=True)
def default_fill_range(settings):
    settings.ITERATION_CALLS = 1
    settings.BULLET_FIT_MIN_RATIO = 0.92
    settings.BULLET_FIT_MAX_RATIO = 0.97


def data(*bullets, summary=""):
    return [
        {
            "title": "Engineer",
            "organization": "Acme",
            "timeline": "2024",
            "summary": summary,
            "bullets": list(bullets),
        }
    ]


def measurement(ratio, lines=1):
    return {
        "ratio": ratio,
        "lines": lines,
        "width_pt": ratio * 400,
        "available_pt": 400,
    }


def mock_measure(monkeypatch, widths, summaries=None):
    calls = []

    def measure(_resume, entries):
        calls.append(copy.deepcopy(entries))
        return {
            (str(eid), *ref[:3]): measurement(*widths[ref[3]])
            for eid, (section, content) in entries.items()
            for ref in fitter._extract_bullets(content, section)
        }

    monkeypatch.setattr(fitter, "measure_entries", measure)
    if summaries is not None:
        monkeypatch.setattr(
            fitter,
            "measure_summaries",
            lambda _resume, entries: {
                (str(eid), index, "summary"): measurement(*summaries[text])
                for eid, (section, content) in entries.items()
                for index, text in fitter._extract_project_summaries(content, section)
            },
        )
    return calls


def fix(original, *texts, index=0, protected=None, details=None, **kwargs):
    return {
        "index": index,
        "bullets": list(texts),
        "action": "rewrite",
        "dropped": [],
        "added": [],
        "reason": "Equivalent wording",
        "facts": {
            "claims": [original],
            "protected": protected or [],
            "details": details or [],
        },
        **kwargs,
    }


def response(*items):
    return {"fixes": list(items)}


def payload(prompt):
    return json.loads(
        prompt.rsplit("<measurements>\n", 1)[1].split("\n</measurements>")[0]
    )


def test_deterministic_guidance_refreshes_with_retry_without_extra_model_calls(
    monkeypatch,
):
    original = "Developed robust natural language processing systems using NLTK"
    intermediate = "Developed natural language processing systems using NLTK"
    final = "Developed NLP systems using NLTK"
    mock_measure(
        monkeypatch,
        {
            original: (2.4, 3),
            intermediate: (1.4, 2),
            final: (0.95, 1),
        },
    )
    llm = Mock()
    llm.generate_json.side_effect = [
        response(fix(original, intermediate, protected=["NLTK"])),
        response(fix(original, final, protected=["NLTK"])),
    ]
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [final]
    assert llm.generate_json.call_count == 2
    first, retry = [
        payload(call.args[0])[0] for call in llm.generate_json.call_args_list
    ]
    assert (
        first["deterministic_guidance"]["current_candidates"][0]["editing_options"][
            "filler_candidates"
        ][0]["text"]
        == "robust"
    )
    retry_guidance = retry["deterministic_guidance"]["current_candidates"][0]
    assert retry_guidance["editing_options"]["filler_candidates"] == []
    assert (
        retry_guidance["width_budget"]["difference_to_target_pt"]
        < first["deterministic_guidance"]["current_candidates"][0]["width_budget"][
            "difference_to_target_pt"
        ]
    )
    assert retry["previous_rejection"]
    assert report["bullets"][0]["status"] == "fitted"


def test_guidance_uses_source_metrics_and_existing_rejection_checks(monkeypatch):
    original, changed = "Improved Python by 20%", "Improved Python by 25%"
    mock_measure(monkeypatch, {original: (1.4, 2)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, changed))
    out, report = fit(data(original), llm)
    first, retry = [
        payload(call.args[0])[0] for call in llm.generate_json.call_args_list
    ]
    assert first["deterministic_guidance"]["source_constraints"][
        "numeric_inventory"
    ] == {"20%": 1}
    assert retry["previous_rejection"].startswith("Factual check failed:")
    assert out == data(original)
    assert llm.generate_json.call_count == 2
    assert report["bullets"][0]["status"] == "unfitted"


def fit(content, llm):
    return fitter.fit_bullets_in_content(
        content, "key_projects", llm, resume=None, entry_id="e"
    )


@pytest.mark.parametrize("failure", [False, True])
def test_lite_test_mode_has_one_call_for_mixed_unresolved_batch(
    monkeypatch, settings, failure
):
    settings.RESUME_LLM_LITE_PREPROCESSING = True
    settings.ITERATION_CALLS = 0
    original, summary = "Built Python tools", "A project summary"
    mock_measure(monkeypatch, {original: (1.4, 2)}, {summary: (1.4, 2)})
    llm = Mock()
    if failure:
        llm.generate_json.side_effect = LLMClientError("Unavailable")
    else:
        llm.generate_json.return_value = {"fixes": []}
    _, report = fit(data(original, summary=summary), llm)
    assert llm.generate_json.call_count == 1
    assert report["bullets"][0]["attempts"] == 1
    assert report["summaries"][0]["attempts"] == 1


def test_lite_test_mode_still_skips_fitting_acceptable_content(monkeypatch, settings):
    settings.RESUME_LLM_LITE_PREPROCESSING = True
    settings.ITERATION_CALLS = 0
    original = "Built Python tools"
    mock_measure(monkeypatch, {original: (0.95, 1)})
    llm = Mock()
    fit(data(original), llm)
    llm.generate_json.assert_not_called()


@pytest.mark.parametrize("retries", [0, 1, 2])
@pytest.mark.parametrize("lite_enabled", [False, True])
@pytest.mark.parametrize("failure", [False, True])
def test_iteration_calls_controls_each_frozen_batch_independently_of_lite(
    monkeypatch, settings, retries, lite_enabled, failure
):
    settings.ITERATION_CALLS = retries
    settings.RESUME_LLM_LITE_PREPROCESSING = lite_enabled
    settings.BULLET_FIT_MODEL_BATCH_SIZE = 3
    original, summary = "Built Python tools", "A project summary"
    mock_measure(monkeypatch, {original: (1.4, 2)}, {summary: (1.4, 2)})
    llm = Mock()
    if failure:
        llm.generate_json.side_effect = LLMClientError("Unavailable")
    else:
        llm.generate_json.return_value = {"fixes": []}
    _, report = fit(data(original, original, original, summary=summary), llm)
    assert llm.generate_json.call_count == 2 * (1 + retries)
    for item in report["bullets"] + report["summaries"]:
        assert item["attempts"] == 1 + retries


def test_multiple_configured_retries_stop_when_resolved(monkeypatch, settings):
    settings.ITERATION_CALLS = 4
    original, revised = "Built Python tools", "Created Python tools"
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, revised))
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["bullets"][0]["attempts"] == 1
    assert llm.generate_json.call_count == 1


@pytest.mark.parametrize("invalid", [-1, "1", 1.5, True])
def test_invalid_retry_configuration_preserves_source_without_model_call(
    settings, invalid
):
    settings.ITERATION_CALLS = invalid
    original = data("Built Python tools")
    llm = Mock()
    out, report = fit(original, llm)
    assert out == original
    assert report["error"]["stage"] == "configuration"
    llm.generate_json.assert_not_called()


@pytest.mark.parametrize("ratio", [0.92, 0.94, 0.97])
def test_inclusive_boundaries_make_no_model_calls(monkeypatch, ratio):
    original = "Improved Python by 20%"
    mock_measure(monkeypatch, {original: (ratio, 1)})
    llm = Mock()
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert report["bullets"][0]["status"] == "unchanged"
    llm.generate_json.assert_not_called()


@pytest.mark.parametrize("ratio", [0.919, 0.971, 1.2])
def test_one_call_and_remeasurement_resolve_bullet(monkeypatch, ratio):
    original, revised = "Improved Python by 20%", "Optimized Python by 20%"
    calls = mock_measure(monkeypatch, {original: (ratio, 1), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(original, revised, protected=["Python", "20%"])
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert len(calls) == 2
    assert llm.generate_json.call_count == 1
    assert (
        llm.generate_json.call_args.kwargs["response_schema"]
        == fitter.OPTIMIZATION_SCHEMA
    )
    assert report["bullets"][0]["attempts"] == 1


def test_two_call_limit_retains_best_locally_checked_candidate(monkeypatch):
    a, b, c = (
        "Improved Python by 20%",
        "Optimized Python by 20%",
        "Accelerated Python by 20%",
    )
    calls = mock_measure(monkeypatch, {a: (1.3, 2), b: (0.88, 1), c: (1.01, 2)})
    llm = Mock()
    llm.generate_json.side_effect = [response(fix(a, b)), response(fix(a, c))]
    out, report = fit(data(a), llm)
    assert out[0]["bullets"] == [b]
    assert len(calls) == 3
    assert llm.generate_json.call_count == 2
    assert report["bullets"][0]["attempts"] == 2
    assert report["status"] == "partial"
    assert payload(llm.generate_json.call_args.args[0])[0]["current"] == [b]


@pytest.mark.parametrize(
    "candidate",
    [
        "Improved Python by 30%",
        "Improved Java by 20%",
        "Improved Python by 20% with robust results",
    ],
)
def test_local_factual_checks_reject_even_a_self_checked_response(
    monkeypatch, candidate
):
    original = "Improved Python by 20%"
    mock_measure(monkeypatch, {original: (0.6, 1), candidate: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, candidate))
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert llm.generate_json.call_count == 2
    assert "Factual check failed" in report["bullets"][0]["reason"]
    assert (
        "Factual check failed"
        in payload(llm.generate_json.call_args.args[0])[0]["previous_rejection"]
    )


@pytest.mark.parametrize(
    "bad",
    [
        {"fixes": "bad"},
        {"fixes": []},
        {"facts": []},
        response({"index": "0", "bullet": "bad"}),
    ],
)
def test_malformed_or_missing_response_consumes_retry(monkeypatch, bad):
    original = "Improved Python by 20%"
    mock_measure(monkeypatch, {original: (0.5, 1)})
    llm = Mock()
    llm.generate_json.return_value = bad
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert report["bullets"][0]["attempts"] == llm.generate_json.call_count == 2
    assert report["status"] == "partial"
    assert "inventory" not in report["bullets"][0]["reason"].lower()


def test_schema_failure_can_recover_on_only_retry(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.5, 1), b: (0.95, 1)})
    llm = Mock()
    llm.generate_json.side_effect = [{"fixes": "bad"}, response(fix(a, b))]
    out, report = fit(data(a), llm)
    assert out[0]["bullets"] == [b]
    assert report["bullets"][0]["error"] is None
    assert "error" not in report


def test_source_reference_case_difference_does_not_force_a_retry(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.5, 1), b: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(a, b, protected=["python"]))
    out, report = fit(data(a), llm)
    assert out[0]["bullets"] == [b]
    assert report["bullets"][0]["attempts"] == 1
    assert llm.generate_json.call_count == 1


def test_resolved_bullets_leave_original_batch_on_retry(monkeypatch):
    a, b, c, d, e = ["Python 20% " + label for label in "ABCDE"]
    mock_measure(
        monkeypatch,
        {a: (0.5, 1), b: (1.2, 2), c: (0.95, 1), d: (0.88, 1), e: (0.95, 1)},
    )
    llm = Mock()
    llm.generate_json.side_effect = [
        response(fix(a, c), fix(b, d, index=1)),
        response(fix(b, e, index=1)),
    ]
    out, report = fit(data(a, b), llm)
    assert out[0]["bullets"] == [c, e]
    assert [r["attempts"] for r in report["bullets"]] == [1, 2]
    retry = payload(llm.generate_json.call_args.args[0])
    assert [p["index"] for p in retry] == [1]
    assert retry[0]["measurements"][0]["ratio"] == 0.88


def test_failed_retry_keeps_previous_candidate(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.5, 1), b: (0.88, 1)})
    llm = Mock()
    llm.generate_json.side_effect = [
        response(fix(a, b)),
        LLMClientError("busy", code=503),
    ]
    out, report = fit(data(a), llm)
    assert out[0]["bullets"] == [b]
    assert report["error"]["stage"] == "wording_optimization"


def test_multiline_tie_preserves_original(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.95, 2), b: (0.95, 2)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(a, b))
    out, report = fit(data(a), llm)
    assert out == data(a)
    assert report["status"] == "partial"
    assert llm.generate_json.call_count == 2


@pytest.mark.parametrize(
    "code,expected,retryable",
    [
        (503, "model_unavailable", True),
        (429, "model_rate_limited", True),
        (403, "model_access_denied", False),
        (404, "model_not_found", False),
    ],
)
def test_provider_failures_consume_budget_without_touching_fitted_items(
    monkeypatch, code, expected, retryable
):
    a, b = "Used Python", "Built tests"
    mock_measure(monkeypatch, {a: (0.5, 1), b: (0.95, 1)})
    llm = Mock()
    llm.generate_json.side_effect = LLMClientError("test-secret", code=code)
    out, report = fit(data(a, b), llm)
    assert out == data(a, b)
    assert report["error"]["code"] == expected
    assert report["error"]["retryable"] is retryable
    assert report["error"]["stage"] == "wording_optimization"
    assert llm.generate_json.call_count == 2
    assert "test-secret" not in str(report)
    assert report["bullets"][1]["attempts"] == 0
    assert report["bullets"][1]["error"] is None


def test_measurement_failure_makes_no_model_calls(monkeypatch):
    monkeypatch.setattr(
        fitter, "measure_entries", Mock(side_effect=RuntimeError("Docker stopped"))
    )
    llm = Mock()
    out, report = fit(data("Used Python"), llm)
    assert out == data("Used Python")
    assert report["error"]["code"] == "measurement_failed"
    llm.generate_json.assert_not_called()


def test_revision_measurement_failure_preserves_original(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.5, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(a, b))
    out, report = fit(data(a), llm)
    assert out == data(a)
    assert report["error"]["stage"] == "revision_measurement"
    assert llm.generate_json.call_count == 1


def test_unconfigured_model_keeps_measurements(monkeypatch):
    mock_measure(monkeypatch, {"Python": (0.5, 1)})
    _, report = fit(data("Python"), None)
    assert report["error"]["code"] == "model_not_configured"
    assert report["bullets"][0]["short_by_pt"] == [168.0]


def test_multiple_frozen_batches_continue_after_failure(monkeypatch, settings):
    settings.BULLET_FIT_MODEL_BATCH_SIZE = 2
    originals = [f"Used Python for {i} records" for i in range(5)]
    revised = [f"Processed {i} records with Python" for i in range(5)]
    mock_measure(
        monkeypatch,
        {**{s: (0.5, 1) for s in originals}, **{s: (0.95, 1) for s in revised}},
    )
    requests = []

    def respond(prompt, response_schema):
        items = payload(prompt)
        requests.append(items)
        assert len(items) <= 2
        if items[0]["index"] == 0:
            raise LLMClientError("busy", code=503)
        return response(
            *(fix(p["original"], revised[p["index"]], index=p["index"]) for p in items)
        )

    llm = Mock(generate_json=Mock(side_effect=respond))
    out, report = fit(data(*originals), llm)
    assert out[0]["bullets"] == originals[:2] + revised[2:]
    assert len(requests) == 4  # failed batch twice, two other batches once
    assert [r["attempts"] for r in report["bullets"]] == [2, 2, 1, 1, 1]


def test_bullets_and_summaries_share_one_request_and_retry(monkeypatch):
    a, b, summary, short = (
        "Used Python",
        "Developed Python",
        "A very long project purpose",
        "A project purpose",
    )
    mock_measure(
        monkeypatch, {a: (0.5, 1), b: (0.95, 1)}, {summary: (1.4, 2), short: (0.8, 1)}
    )
    llm = Mock()
    llm.generate_json.side_effect = [
        response(fix(a, b)),
        response(fix(summary, short, index=1)),
    ]
    out, report = fit(data(a, summary=summary), llm)
    assert out == data(b, summary=short)
    first = payload(llm.generate_json.call_args_list[0].args[0])
    assert [i["kind"] for i in first] == ["bullet", "summary"]
    assert [i["kind"] for i in payload(llm.generate_json.call_args.args[0])] == [
        "summary"
    ]
    assert llm.generate_json.call_count == 2
    assert report["bullets"][0]["attempts"] == 1
    assert report["summaries"][0]["attempts"] == 2


def test_short_summary_is_not_expanded(monkeypatch):
    mock_measure(monkeypatch, {}, {"A purpose": (0.4, 1)})
    llm = Mock()
    _, report = fit(data(summary="A purpose"), llm)
    llm.generate_json.assert_not_called()
    assert report["summaries"][0]["status"] == "unchanged"


def test_summary_rejects_new_metrics_and_splits(monkeypatch):
    original = "A retrieval project using Python for documents"
    invented = "A retrieval project using Python for 50,000 documents"
    mock_measure(monkeypatch, {}, {original: (1.3, 2), invented: (0.8, 1)})
    llm = Mock()
    llm.generate_json.side_effect = [
        response(fix(original, invented)),
        response(fix(original, "A project", "Another purpose", action="split")),
    ]
    out, report = fit(data(summary=original), llm)
    assert out == data(summary=original)
    assert report["summaries"][0]["attempts"] == 2
    assert (
        "Factual check failed"
        in payload(llm.generate_json.call_args.args[0])[0]["previous_rejection"]
    )


def test_summary_measurement_failure_does_not_block_bullets(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.5, 1), b: (0.95, 1)})
    monkeypatch.setattr(
        fitter, "measure_summaries", Mock(side_effect=RuntimeError("bad summary"))
    )
    llm = Mock()
    llm.generate_json.return_value = response(fix(a, b))
    out, report = fit(data(a, summary="A purpose"), llm)
    assert out == data(b, summary="A purpose")
    assert report["status"] == "partial"
    assert report["summaries"][0]["error"]["stage"] == "original_measurement"


@pytest.mark.parametrize("ratio,lines", [(0.88, 1), (1.0, 1)])
def test_wider_range_accepts_existing_one_liners(monkeypatch, settings, ratio, lines):
    settings.BULLET_FIT_MIN_RATIO = 0.88
    settings.BULLET_FIT_MAX_RATIO = 1.0
    text = "Developed Python tools for document retrieval and evaluated results"
    mock_measure(monkeypatch, {text: (ratio, lines)})
    llm = Mock()
    out, report = fit(data(text), llm)
    assert out == data(text)
    assert report["status"] == "complete"
    assert report["bullets"][0]["attempts"] == 0
    llm.generate_json.assert_not_called()


@pytest.mark.parametrize("ratio,lines", [(1.05, 2), (1.87, 2), (2.01, 3), (0.87, 1)])
def test_sparse_tail_or_more_than_two_lines_still_checked(
    monkeypatch, settings, ratio, lines
):
    settings.BULLET_FIT_MIN_RATIO = 0.88
    settings.BULLET_FIT_MAX_RATIO = 1.0
    text = "Developed Python tools for document retrieval and evaluated results"
    mock_measure(monkeypatch, {text: (ratio, lines)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(text, text))
    out, report = fit(data(text), llm)
    assert out == data(text)
    assert report["status"] == "partial"
    assert llm.generate_json.call_count == 2
    if ratio == 1.87:
        assert report["bullets"][0]["short_by_pt"] == [4.0]


def test_nearly_full_two_line_bullet_can_be_filled_without_splitting(
    monkeypatch, settings
):
    settings.BULLET_FIT_MIN_RATIO = 0.88
    settings.BULLET_FIT_MAX_RATIO = 1.0
    original = (
        "Developed Python tools for retrieval and evaluated the resulting predictions"
    )
    revised = "Developed Python tools for document retrieval and evaluated the resulting predictions"
    mock_measure(monkeypatch, {original: (1.8, 2), revised: (1.94, 2)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, revised))
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"
    item = payload(llm.generate_json.call_args.args[0])[0]
    assert item["target_lines"] == 1
    assert item["max_output_bullets"] == 2
    assert item["target_pt"] == pytest.approx(0.94 * 400)
    assert llm.generate_json.call_count == 2
    assert "two-line fallback" in report["bullets"][0]["reason"]


def test_unrequested_bullet_splitting_is_rejected(monkeypatch):
    original = "Developed Python parser and evaluated predictions with 20% accuracy"
    mock_measure(monkeypatch, {original: (0.6, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            "Developed Python parser.",
            "Evaluated 20% accuracy.",
            action="split",
        )
    )
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert "only wrapping bullets" in report["bullets"][0]["reason"]
    assert llm.generate_json.call_count == 2


def test_number_normalization_and_bold_preservation():
    assert fitter._exact_facts(
        "Processed 50K reviews using Python",
        ["Processed 50,000 reviews using Python"],
        {"protected": ["50K", "Python"]},
    )
    assert not fitter._exact_facts(
        "Used **Python** for 20% improvement",
        ["Used Python for 20% improvement"],
        {"protected": ["Python"]},
    )
    assert not fitter._exact_facts(
        "Developed Python and evaluated 20% accuracy",
        ["Developed Python.", "Evaluated Python with 20% accuracy."],
        {"protected": ["Python", "20%"]},
    )


def test_restored_fitter_prompt_is_simple_and_preserves_useful_detail():
    prompt = fitter._prompt([])
    assert "Aim for one well-filled line" in prompt
    assert "two-line fallback" in prompt
    assert "Do not invent facts" in prompt
    assert "fixes" in fitter.OPTIMIZATION_SCHEMA["properties"]


def test_scope_and_invalid_configuration(settings):
    assert not fitter._extract_bullets([{"text": "award"}], "scholastic_achievements")
    assert fitter._extract_bullets(["award"], "scholastic_achievements")
    assert not fitter._extract_bullets(data("Python"), "education")
    settings.BULLET_FIT_MIN_RATIO = 0.98
    with pytest.raises(ValueError):
        fitter.fill_range()
    settings.BULLET_FIT_MODEL_BATCH_SIZE = 0
    with pytest.raises(ValueError):
        fitter.model_batch_size()


def test_mixed_bullet_and_summary_resolve_in_one_call(monkeypatch):
    a, b, summary, short = (
        "Used Python",
        "Developed Python",
        "A long project purpose",
        "A project purpose",
    )
    mock_measure(
        monkeypatch, {a: (0.5, 1), b: (0.95, 1)}, {summary: (1.4, 2), short: (0.8, 1)}
    )
    llm = Mock()
    llm.generate_json.return_value = response(fix(a, b), fix(summary, short, index=1))
    out, report = fit(data(a, summary=summary), llm)
    assert out == data(b, summary=short)
    assert llm.generate_json.call_count == 1
    assert report["status"] == "complete"


def test_duplicate_index_is_not_applied_and_only_retried_once(monkeypatch):
    a, b = "Used Python", "Developed Python"
    mock_measure(monkeypatch, {a: (0.5, 1), b: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(a, b), fix(a, b))
    out, report = fit(data(a), llm)
    assert out == data(a)
    assert llm.generate_json.call_count == 2
    assert "No usable" in report["bullets"][0]["reason"]


@pytest.mark.parametrize(
    "candidate", ["\\textbf{Python}", "## Python heading", "<b>Python</b>"]
)
def test_structural_markup_is_rejected_locally(monkeypatch, candidate):
    original = "Used Python"
    mock_measure(monkeypatch, {original: (0.5, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, candidate))
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert "Unsupported formatting" in report["bullets"][0]["reason"]


@pytest.mark.parametrize("ratio", [1.88, 2.0])
def test_full_two_line_original_is_optimized_before_accepting_fallback(
    monkeypatch, settings, ratio
):
    settings.BULLET_FIT_MIN_RATIO, settings.BULLET_FIT_MAX_RATIO = 0.88, 1.0
    original = "Developed Python tools and evaluated the resulting predictions"
    mock_measure(monkeypatch, {original: (ratio, 2)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, original))
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert llm.generate_json.call_count == 2
    assert report["status"] == "complete"
    assert "two-line fallback" in report["bullets"][0]["reason"]


def test_full_two_line_original_can_be_shortened_to_one_line(monkeypatch):
    original = "Developed Python parser and evaluated the resulting predictions with 20% accuracy"
    revised = "Developed Python parser and evaluated predictions with 20% accuracy"
    mock_measure(monkeypatch, {original: (1.95, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, revised))
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"
    assert llm.generate_json.call_count == 1


def test_two_distinct_one_line_splits_preserve_mapping(monkeypatch):
    originals = [
        "Developed Python parser and evaluated predictions with 20% accuracy",
        "Built Docker checks for 12 services and reduced build time by 30%",
    ]
    pairs = [
        ["Developed Python parser.", "Evaluated predictions with 20% accuracy."],
        ["Built Docker checks for 12 services.", "Reduced build time by 30%."],
    ]
    mock_measure(
        monkeypatch,
        {
            **{s: (1.95, 2) for s in originals},
            **{s: (0.95, 1) for pair in pairs for s in pair},
        },
    )
    llm = Mock()
    llm.generate_json.return_value = response(
        *(fix(s, *pairs[i], index=i, action="split") for i, s in enumerate(originals))
    )
    out, report = fit(data(*originals), llm)
    assert out[0]["bullets"] == pairs[0] + pairs[1]
    assert report["status"] == "complete"
    assert llm.generate_json.call_count == 1


@pytest.mark.parametrize(
    "drop,details,expected",
    [
        ("Pandas", [{"text": "Pandas", "tier": 3}], True),
        ("Pandas", [{"text": "Pandas", "tier": 1}], False),
        (
            "Pandas",
            [{"text": "Pandas", "tier": 2}, {"text": "records", "tier": 3}],
            True,
        ),
    ],
)
def test_optional_omissions_follow_priority_without_losing_metrics(
    monkeypatch, drop, details, expected
):
    original = "Developed Python parser with Pandas for records, achieving 20% accuracy"
    compact = "Developed Python parser for records, achieving 20% accuracy"
    mock_measure(monkeypatch, {original: (1.6, 2), compact: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            compact,
            protected=["Python", "20%"],
            details=details,
            dropped=[drop],
            action="drop",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == ([compact] if expected else [original])
    if not expected:
        assert "Factual check failed" in report["bullets"][0]["reason"]


def test_metrics_and_test_qualifications_cannot_be_dropped_as_optional(monkeypatch):
    original = "Evaluated Python predictions on 600 synthetic reports with 84% accuracy"
    compact = "Evaluated Python predictions on 600 reports with 84% accuracy"
    mock_measure(monkeypatch, {original: (1.4, 2), compact: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            compact,
            details=[{"text": "synthetic", "tier": 4}],
            dropped=["synthetic"],
            action="drop",
        )
    )
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert "qualification" in report["bullets"][0]["reason"]


def test_split_cap_is_reserved_across_batch(monkeypatch, settings):
    settings.BULLET_FIT_MAX_BULLETS_PER_ITEM = 3
    originals = [
        "Developed Python parser and evaluated predictions with 20% accuracy",
        "Built Docker checks for 12 services and reduced build time by 30%",
    ]
    pairs = [
        ["Developed Python parser.", "Evaluated predictions with 20% accuracy."],
        ["Built Docker checks for 12 services.", "Reduced build time by 30%."],
    ]
    mock_measure(
        monkeypatch,
        {
            **{s: (1.6, 2) for s in originals},
            **{s: (0.95, 1) for pair in pairs for s in pair},
        },
    )
    llm = Mock()
    llm.generate_json.return_value = response(
        *(fix(s, *pairs[i], index=i, action="split") for i, s in enumerate(originals))
    )
    out, report = fit(data(*originals), llm)
    assert out[0]["bullets"] == pairs[0] + [originals[1]]
    assert "bullet limit" in report["bullets"][1]["reason"]


def test_actual_line_feedback_is_sent_without_extra_model_calls(monkeypatch):
    original, revised = "Improved Python by 20%", "Optimized Python by 20%"
    widths = {
        original: {
            **measurement(1.95, 2),
            "line_measurement": "rendered_pdf",
            "line_widths_pt": [396, 140],
            "line_fill_ratios": [0.99, 0.35],
            "fit_line_fill_ratios": [0.99, 0.35],
            "line_pages": [1, 1],
            "has_box_overflow": False,
            "overflow_pt": 0,
        },
        revised: {
            **measurement(0.95, 1),
            "line_measurement": "rendered_pdf",
            "line_widths_pt": [380],
            "line_fill_ratios": [0.95],
            "fit_line_fill_ratios": [0.95],
            "line_pages": [1],
            "has_box_overflow": False,
            "overflow_pt": 0,
        },
    }
    monkeypatch.setattr(
        fitter,
        "measure_entries",
        lambda _resume, entries: {
            (eid, *ref[:3]): widths[ref[3]]
            for eid, (section, content) in entries.items()
            for ref in fitter._extract_bullets(content, section)
        },
    )
    llm = Mock()
    llm.generate_json.return_value = response(fix(original, revised))
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    request = payload(llm.generate_json.call_args.args[0])[0]
    assert request["layout_status"] == ["short_spillover"]
    assert request["measurements"][0]["line_fill_ratios"] == [0.99, 0.35]
    assert report["bullets"][0]["measurement"]["line_measurement"] == "rendered_pdf"
    assert llm.generate_json.call_count == 1


def test_filler_is_removable_even_if_the_model_overprotects_it(monkeypatch):
    original = "Built robust and reliable neural networks for NLP"
    revised = "Built neural networks for NLP"
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["robust", "reliable", "NLP", "neural networks"],
            details=[{"text": "robust", "tier": 1}, {"text": "reliable", "tier": 1}],
            dropped=["robust", "reliable"],
            action="compress",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"
    assert llm.generate_json.call_count == 1


def test_secondary_phrase_can_be_paraphrased_without_literal_preservation(monkeypatch):
    original = (
        "Built Python tools featuring an interactive interface for retrieving documents"
    )
    revised = "Built Python tools with a document search UI"
    mock_measure(monkeypatch, {original: (1.5, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["Python"],
            details=[
                {"text": "an interactive interface for retrieving documents", "tier": 2}
            ],
            added=["Equivalent document search UI wording"],
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"


def test_supporting_library_list_can_be_omitted_as_a_secondary_phrase(monkeypatch):
    original = "Built Python parser with Pandas and NumPy, achieving 20% accuracy"
    revised = "Built Python parser, achieving 20% accuracy"
    mock_measure(monkeypatch, {original: (1.5, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["Python", "20%"],
            details=[{"text": "Pandas and NumPy", "tier": 3}],
            dropped=["Pandas and NumPy"],
            action="drop",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"


def test_tailored_nlp_example_preserves_core_concepts_without_verbose_wording(
    monkeypatch,
):
    original = "Developed natural language processing systems using NLTK and deep learning techniques to build robust neural networks."
    revised = "Developed NLP systems using NLTK and neural networks."
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["natural language processing", "NLTK", "neural networks"],
            details=[
                {"text": "deep learning techniques", "tier": 3},
                {"text": "robust", "tier": 4},
            ],
            dropped=["robust"],
            added=["NLP abbreviates natural language processing"],
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"


def test_explicit_optional_version_can_be_removed_but_outcome_metric_cannot(
    monkeypatch,
):
    original = "Built Python version 3.10 tools, reducing latency by 20%"
    revised = "Built Python tools, reducing latency by 20%"
    mock_measure(monkeypatch, {original: (1.3, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["Python", "20%"],
            details=[{"text": "version 3.10", "tier": 3}],
            dropped=["version 3.10"],
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"
    assert not fitter._exact_facts(
        original,
        ["Built Python tools"],
        {"protected": ["Python"], "details": [{"text": "version 3.10", "tier": 3}]},
        ["version 3.10"],
    )


def test_dataset_population_cannot_be_removed_as_an_optional_detail():
    original = "Evaluated Python matching on 600 reports with 84% accuracy"
    assert not fitter._exact_facts(
        original,
        ["Evaluated Python matching with 84% accuracy"],
        {
            "protected": ["Python", "84%"],
            "details": [{"text": "600 reports", "tier": 3}],
        },
        ["600 reports"],
        allow_optional_rewording=True,
    )


def test_equivalent_percentage_formatting_does_not_change_the_metric():
    assert fitter._exact_facts(
        "Achieved 98 percent accuracy using Python",
        ["Achieved 98% accuracy using Python"],
        {"protected": ["98 percent", "Python"]},
    )


def test_prompt_authorizes_edits_that_preserve_required_facts():
    prompt = fitter._prompt([])
    assert "Freely rephrase and remove secondary details" in prompt
    assert "Never drop a required metric or qualification" in prompt
    assert "Metadata is advisory" in prompt


def test_unmatched_secondary_metadata_is_advisory_not_a_rewrite_gate(monkeypatch):
    original = "Developed Python tools for geographical processing"
    revised = "Built Python geospatial tools"
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["Python", "geospatial processing"],
            details=[{"text": "secondary implementation wording", "tier": 2}],
            dropped=["unmatched optional wording"],
            action="compress",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["bullets"][0]["metadata_notes"]
    assert llm.generate_json.call_count == 1


def test_core_action_paraphrase_is_not_a_t1_deletion(monkeypatch):
    original = "Implemented geographically separated training and test areas to reduce spatial leakage and used SHAP to analyze vegetation"
    revised = "Separated training and test regions geographically and used SHAP to analyze vegetation"
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    phrase = "Implemented geographically separated training and test areas"
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["SHAP"],
            details=[{"text": phrase, "tier": 1}],
            dropped=[phrase],
            action="compress",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"


def test_core_technology_remains_protected_despite_bad_secondary_annotations(
    monkeypatch,
):
    original = "Built Python tools with 20% improvement"
    revised = "Built Java tools with 20% improvement"
    mock_measure(monkeypatch, {original: (1.3, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            details=[{"text": "an unmatched secondary note", "tier": 3}],
            dropped=["Python"],
        )
    )
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert "Python" in report["bullets"][0]["reason"]
    assert "removed" in report["bullets"][0]["reason"]


def test_research_count_and_temperature_formats_can_be_shortened(monkeypatch):
    original = "Processed Python data across twenty four urban neighborhoods with a mean absolute error of 1.8 degrees Celsius on a held out test set"
    revised = (
        "Processed Python data from 24 neighborhoods with 1.8°C MAE on held-out tests"
    )
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=["Python", "24", "1.8°C", "MAE", "held-out"],
            details=[{"text": "across twenty-four urban neighborhoods", "tier": 2}],
            dropped=["verbose wording"],
            action="compress",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["status"] == "complete"
    assert llm.generate_json.call_count == 1


@pytest.mark.parametrize(
    "candidate,reason",
    [
        ("Evaluated Python with 1.8°C MAE on held-out tests", "24"),
        (
            "Evaluated Python across 24 neighborhoods with 1.9°C MAE on held-out tests",
            "1.9",
        ),
        ("Evaluated Python across 24 neighborhoods with 1.8°C MAE", "qualification"),
    ],
)
def test_important_research_facts_are_not_relaxed_with_metadata(
    monkeypatch, candidate, reason
):
    original = "Evaluated Python across twenty four neighborhoods with 1.8 degrees Celsius mean absolute error on a held out test set"
    mock_measure(monkeypatch, {original: (1.4, 2), candidate: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            candidate,
            details=[{"text": "irrelevant optional metadata", "tier": 3}],
            dropped=["all previous wording"],
            action="compress",
        )
    )
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert reason in report["bullets"][0]["reason"]


def test_a_new_defining_label_is_not_authorized_by_an_unmatched_protected_annotation(
    monkeypatch,
):
    original, revised = "Built Python tools", "Built Python tools with Keras"
    mock_measure(monkeypatch, {original: (1.3, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(original, revised, protected=["Python", "Keras"])
    )
    out, report = fit(data(original), llm)
    assert out == data(original)
    assert "Keras" in report["bullets"][0]["reason"]
    assert "not supported" in report["bullets"][0]["reason"]


def test_protected_core_phrase_does_not_freeze_its_verb_and_word_order(monkeypatch):
    original = "Implemented Python processing across twenty four urban neighborhoods"
    revised = "Processed 24 neighborhoods using Python"
    mock_measure(monkeypatch, {original: (1.4, 2), revised: (0.95, 1)})
    llm = Mock()
    llm.generate_json.return_value = response(
        fix(
            original,
            revised,
            protected=[
                "Implemented",
                "Python processing",
                "twenty four urban neighborhoods",
            ],
            details=[{"text": "Implemented Python processing", "tier": 1}],
            dropped=["Implemented Python processing"],
            action="compress",
        )
    )
    out, report = fit(data(original), llm)
    assert out[0]["bullets"] == [revised]
    assert report["bullets"][0]["metadata_notes"]
    assert llm.generate_json.call_count == 1
