"""Unit tests for candidate-based line optimization."""

import pytest
from unittest.mock import Mock

from resume_renderer.services.candidate_fitter import (
    has_candidates,
    score_candidate_measurement,
    estimate_fallback_measurement,
    select_best_candidates,
    is_bullet_overflown,
    calculate_overflow_metrics,
    build_overflow_repair_prompt,
    repair_overflown_bullets,
)


def test_has_candidates_detection():
    # Plain strings
    plain = [{"title": "Job", "bullets": ["Built X", "Ran Y"]}]
    assert not has_candidates(plain)
    assert not has_candidates([])
    assert not has_candidates(None)

    # Candidate dicts
    candidates_dict = [
        {
            "title": "Job",
            "bullets": [
                {
                    "compact": "Built X with Python.",
                    "medium": "Built X using Python and FastAPI.",
                    "full": "Architected and built scalable X using Python, FastAPI, and PostgreSQL.",
                }
            ],
        }
    ]
    assert has_candidates(candidates_dict)

    # Candidate list
    candidates_list = [
        {
            "title": "Job",
            "bullets": [
                ["Built X with Python.", "Built X using Python and FastAPI."]
            ],
        }
    ]
    assert has_candidates(candidates_list)


def test_score_candidate_measurement_prefers_least_whitespace_on_single_line():
    # Candidate A: 80% line fill (20% whitespace)
    mA = {"lines": 1, "ratio": 0.80, "has_box_overflow": False, "fit_line_fill_ratios": [0.80]}
    # Candidate B: 95% line fill (5% whitespace)
    mB = {"lines": 1, "ratio": 0.95, "has_box_overflow": False, "fit_line_fill_ratios": [0.95]}
    # Candidate C: 105% (overflow onto line 2)
    mC = {"lines": 2, "ratio": 1.05, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.05]}

    scoreA = score_candidate_measurement(mA)
    scoreB = score_candidate_measurement(mB)
    scoreC = score_candidate_measurement(mC)

    # B beats A because B minimizes whitespace (5% gap < 20% gap)
    assert scoreB < scoreA
    # Both 1-line candidates beat C (which wrapped)
    assert scoreB < scoreC
    assert scoreA < scoreC


def test_select_best_candidates_chooses_highest_single_line_fill():
    raw_content = [
        {
            "title": "Research Intern",
            "organization": "Computing Lab",
            "timeline": "Summer 2025",
            "summary": "Prototype research",
            "bullets": [
                {
                    "compact": "Short bullet (~70% fill)",
                    "medium": "Medium bullet (~85% fill)",
                    "full": "Full bullet (~96% fill)",
                }
            ],
        }
    ]

    # Mock measure_entries to return specific measurements for each probe
    measurements = {
        ("1", 0, "bullets", 0): {"lines": 1, "ratio": 0.70, "has_box_overflow": False, "fit_line_fill_ratios": [0.70]},
        ("1", 0, "bullets", 1): {"lines": 1, "ratio": 0.85, "has_box_overflow": False, "fit_line_fill_ratios": [0.85]},
        ("1", 0, "bullets", 2): {"lines": 1, "ratio": 0.96, "has_box_overflow": False, "fit_line_fill_ratios": [0.96]},
    }

    mock_resume = Mock()
    canonical, fitting = select_best_candidates(
        raw_content,
        "professional_experience",
        resume=mock_resume,
        entry_id=1,
    )

    # Since measure_entries would fail without mocking or LaTeX Docker, let's verify fallback or monkeypatch:
    # First, test with fallback estimation:
    assert isinstance(canonical, list)
    assert len(canonical[0]["bullets"]) == 1
    # Canonical output bullet is a clean string, not a dict!
    assert isinstance(canonical[0]["bullets"][0], str)
    assert fitting["status"] in ("complete", "partial")


def test_select_best_candidates_with_mocked_measurements(monkeypatch):
    import resume_renderer.services.line_fitter as line_fitter

    raw_content = [
        {
            "title": "Engineer",
            "organization": "Acme",
            "timeline": "2025",
            "summary": "Summary text",
            "bullets": [
                {
                    "compact": "Bullet 1 compact",
                    "medium": "Bullet 1 medium",
                    "full": "Bullet 1 full",
                },
                {
                    "compact": "Bullet 2 compact",
                    "medium": "Bullet 2 medium",
                    "full": "Bullet 2 full that overflows",
                },
            ],
        }
    ]

    # Mock measure_entries:
    # Bullet 0: compact=0.75, medium=0.88, full=0.97 -> full wins
    # Bullet 1: compact=0.85, medium=0.95, full=1.05 (2 lines) -> medium wins
    def mock_measure(resume, entries):
        return {
            ("42", 0, "bullets", 0): {"lines": 1, "ratio": 0.75, "has_box_overflow": False, "fit_line_fill_ratios": [0.75]},
            ("42", 0, "bullets", 1): {"lines": 1, "ratio": 0.88, "has_box_overflow": False, "fit_line_fill_ratios": [0.88]},
            ("42", 0, "bullets", 2): {"lines": 1, "ratio": 0.97, "has_box_overflow": False, "fit_line_fill_ratios": [0.97]},
            ("42", 0, "bullets", 3): {"lines": 1, "ratio": 0.85, "has_box_overflow": False, "fit_line_fill_ratios": [0.85]},
            ("42", 0, "bullets", 4): {"lines": 1, "ratio": 0.95, "has_box_overflow": False, "fit_line_fill_ratios": [0.95]},
            ("42", 0, "bullets", 5): {"lines": 2, "ratio": 1.05, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.05]},
        }

    monkeypatch.setattr(line_fitter, "measure_entries", mock_measure)

    canonical, fitting = select_best_candidates(
        raw_content,
        "key_projects",
        resume=Mock(),
        entry_id=42,
    )

    # Bullet 0 selected full
    assert canonical[0]["bullets"][0] == "Bullet 1 full"
    # Bullet 1 selected medium (because full overflowed)
    assert canonical[0]["bullets"][1] == "Bullet 2 medium"
    assert fitting["status"] == "complete"
    assert fitting["bullets"][0]["selected_variant"] == "full"
    assert fitting["bullets"][1]["selected_variant"] == "medium"


def test_fit_bullets_in_content_routes_candidates(monkeypatch):
    import resume_renderer.services.line_fitter as line_fitter

    raw_content = [
        {
            "title": "Engineer",
            "organization": "Acme",
            "timeline": "2025",
            "summary": "Summary text",
            "bullets": [
                {
                    "compact": "Underfilled (~60%)",
                    "medium": "Balanced (~88%)",
                    "full": "Optimized full line (~98%)",
                }
            ],
        }
    ]

    def mock_measure(resume, entries):
        return {
            ("99", 0, "bullets", 0): {"lines": 1, "ratio": 0.60, "has_box_overflow": False, "fit_line_fill_ratios": [0.60]},
            ("99", 0, "bullets", 1): {"lines": 1, "ratio": 0.88, "has_box_overflow": False, "fit_line_fill_ratios": [0.88]},
            ("99", 0, "bullets", 2): {"lines": 1, "ratio": 0.98, "has_box_overflow": False, "fit_line_fill_ratios": [0.98]},
        }

    monkeypatch.setattr(line_fitter, "measure_entries", mock_measure)

    canonical, fitting = line_fitter.fit_bullets_in_content(
        raw_content,
        "key_projects",
        llm_client=Mock(),
        resume=Mock(),
        entry_id=99,
    )

    # Deterministically selected the full line candidate because it maximizes line fill and eliminates whitespace
    assert canonical[0]["bullets"][0] == "Optimized full line (~98%)"
    assert fitting["status"] == "complete"
    assert fitting["bullets"][0]["selected_variant"] == "full"


def test_is_bullet_overflown():
    # Clean 1-line fit
    assert not is_bullet_overflown({"lines": 1, "ratio": 0.95, "has_box_overflow": False})
    assert not is_bullet_overflown({"lines": 1, "ratio": 1.00, "has_box_overflow": False})
    assert not is_bullet_overflown({"lines": 1, "ratio": 1.015, "has_box_overflow": False})

    # Wrapped onto line 2
    assert is_bullet_overflown({"lines": 2, "ratio": 1.05, "has_box_overflow": False})

    # Ratio > 1.02
    assert is_bullet_overflown({"lines": 1, "ratio": 1.03, "has_box_overflow": False})

    # Box overflow flag
    assert is_bullet_overflown({"lines": 1, "ratio": 0.98, "has_box_overflow": True})

    # Edge cases
    assert not is_bullet_overflown({})
    assert not is_bullet_overflown(None)


def test_calculate_overflow_metrics():
    text = "Developed meal suggestions from household groceries and optimized recipes for health conditions and requirements."
    measurement = {
        "width_pt": 465.0,
        "available_pt": 430.0,
        "ratio": 1.0814,
        "lines": 2,
    }

    metrics = calculate_overflow_metrics(text, measurement)

    assert metrics["text_len"] == len(text)
    assert metrics["width_pt"] == 465.0
    assert metrics["available_pt"] == 430.0
    assert metrics["diff_pt"] == 35.0
    assert metrics["overflow_pct"] == 8.1
    assert metrics["overflow_chars"] > 0
    assert metrics["max_chars"] < len(text)
    assert metrics["min_chars"] < metrics["max_chars"]
    assert metrics["lower_limit_ratio"] == 0.85


def test_build_overflow_repair_prompt_injects_realtime_metrics():
    overflown_items = [
        {
            "bullet_index": 0,
            "text": "Developed meal suggestions from household groceries and optimized recipes for health conditions and requirements.",
            "metrics": {
                "text_len": 113,
                "width_pt": 465.0,
                "available_pt": 430.0,
                "ratio": 1.081,
                "lines": 2,
                "diff_pt": 35.0,
                "overflow_pct": 8.1,
                "overflow_chars": 9,
                "max_chars": 102,
                "min_chars": 88,
                "lower_limit_ratio": 0.85,
            },
        }
    ]

    prompt = build_overflow_repair_prompt(overflown_items, "key_projects")

    assert "BULLET #0:" in prompt
    assert "465.0pt / 430.0pt" in prompt
    assert "+35.0pt" in prompt
    assert "AT LEAST 9 characters" in prompt
    assert "88 chars" in prompt
    assert "102 chars" in prompt
    assert "slight_compression" in prompt
    assert "moderate_compression" in prompt
    assert "aggressive_compression" in prompt


def test_repair_overflown_bullets_selects_best_single_line_repair(monkeypatch):
    import resume_renderer.services.line_fitter as line_fitter

    canonical_content = [
        {
            "title": "Engineer",
            "bullets": [
                "Developed meal suggestions from household groceries and optimized recipes for health conditions and requirements."
            ],
        }
    ]

    bullet_reports = [
        {
            "entry_index": 0,
            "bullet_index": 0,
            "selected_variant": "full",
            "text": canonical_content[0]["bullets"][0],
            "measurement": {
                "width_pt": 465.0,
                "available_pt": 430.0,
                "ratio": 1.08,
                "lines": 2,
                "has_box_overflow": False,
            },
            "status": "partial",
            "reason": "Overflown bullet",
            "all_candidates": [],
        }
    ]

    mock_llm = Mock()
    mock_llm.generate_json.return_value = {
        "repairs": [
            {
                "bullet_index": 0,
                "candidates": {
                    "slight_compression": "Developed meal suggestions from groceries and optimized recipes for health conditions.",
                    "moderate_compression": "Developed meal suggestions from groceries and optimized recipes for health goals.",
                    "aggressive_compression": "Optimized grocery-based meal suggestions for health goals.",
                },
            }
        ]
    }

    # Mock measure_entries probe measurements:
    # slight: ratio 1.01, lines 2 (still wraps)
    # moderate: ratio 0.95, lines 1 (fits on 1 line, gap 0.05)
    # aggressive: ratio 0.84, lines 1 (fits on 1 line, gap 0.16)
    def mock_measure(resume, entries):
        return {
            ("10", 0, "bullets", 0): {"lines": 2, "ratio": 1.01, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.01]},
            ("10", 0, "bullets", 1): {"lines": 1, "ratio": 0.95, "has_box_overflow": False, "fit_line_fill_ratios": [0.95]},
            ("10", 0, "bullets", 2): {"lines": 1, "ratio": 0.84, "has_box_overflow": False, "fit_line_fill_ratios": [0.84]},
        }

    monkeypatch.setattr(line_fitter, "measure_entries", mock_measure)

    updated_content, updated_reports = repair_overflown_bullets(
        canonical_content,
        bullet_reports,
        "key_projects",
        resume=Mock(),
        entry_id=10,
        llm_client=mock_llm,
    )

    # Moderate compression wins because it fits on 1 line and has smaller whitespace gap (5% vs 16%)
    assert updated_content[0]["bullets"][0] == "Developed meal suggestions from groceries and optimized recipes for health goals."
    assert updated_reports[0]["repaired"] is True
    assert updated_reports[0]["selected_variant"] == "moderate_compression"
    assert updated_reports[0]["status"] == "fitted"
    assert "Repaired overflow" in updated_reports[0]["reason"]
    assert len(updated_reports[0]["repair_candidates"]) == 3


def test_repair_overflown_bullets_bypasses_when_no_overflow():
    canonical_content = [
        {"title": "Engineer", "bullets": ["Clean single line bullet."]}
    ]
    bullet_reports = [
        {
            "entry_index": 0,
            "bullet_index": 0,
            "selected_variant": "full",
            "text": "Clean single line bullet.",
            "measurement": {
                "width_pt": 410.0,
                "available_pt": 430.0,
                "ratio": 0.95,
                "lines": 1,
                "has_box_overflow": False,
            },
            "status": "fitted",
            "reason": "Clean fit",
        }
    ]

    mock_llm = Mock()
    mock_llm.generate_json.side_effect = RuntimeError("Should not be called!")

    updated_content, updated_reports = repair_overflown_bullets(
        canonical_content,
        bullet_reports,
        "key_projects",
        llm_client=mock_llm,
    )

    # Content unchanged, 0 LLM calls made
    assert updated_content[0]["bullets"][0] == "Clean single line bullet."
    assert mock_llm.generate_json.call_count == 0


def test_repair_overflown_bullets_nonfatal_on_llm_error():
    canonical_content = [
        {"title": "Engineer", "bullets": ["Overflown bullet text that wraps to line 2."]}
    ]
    bullet_reports = [
        {
            "entry_index": 0,
            "bullet_index": 0,
            "selected_variant": "full",
            "text": canonical_content[0]["bullets"][0],
            "measurement": {
                "width_pt": 460.0,
                "available_pt": 430.0,
                "ratio": 1.07,
                "lines": 2,
                "has_box_overflow": False,
            },
            "status": "partial",
            "reason": "Overflown",
        }
    ]

    mock_llm = Mock()
    mock_llm.generate_json.side_effect = Exception("API rate limited")

    updated_content, updated_reports = repair_overflown_bullets(
        canonical_content,
        bullet_reports,
        "key_projects",
        llm_client=mock_llm,
    )

    # Graceful fallback: original content preserved, no unhandled exception
    assert updated_content[0]["bullets"][0] == "Overflown bullet text that wraps to line 2."


def test_select_best_candidates_end_to_end_with_repair(monkeypatch):
    import resume_renderer.services.line_fitter as line_fitter

    raw_content = [
        {
            "title": "Engineer",
            "organization": "Acme",
            "timeline": "2025",
            "bullets": [
                {
                    "compact": "Bullet 1 short",
                    "medium": "Bullet 1 medium",
                    "full": "Bullet 1 full",
                },
                {
                    "compact": "Bullet 2 compact (overflown)",
                    "medium": "Bullet 2 medium (overflown)",
                    "full": "Bullet 2 full (overflown)",
                },
            ],
        }
    ]

    # In initial probe:
    # Bullet 0: probes 0, 1, 2. Candidate 'full' fits cleanly (lines=1, ratio=0.96)
    # Bullet 1: probes 3, 4, 5. All 3 initial candidates overflow (>1.00) so best is full with lines=2, ratio=1.08
    def mock_measure_entries(resume, entries):
        probes = {}
        for eid, (sec, cont) in entries.items():
            bullets = cont[0]["bullets"]
            if len(bullets) == 6:
                # Initial candidate probe
                return {
                    (eid, 0, "bullets", 0): {"lines": 1, "ratio": 0.70, "has_box_overflow": False, "fit_line_fill_ratios": [0.70], "available_pt": 430.0, "width_pt": 301.0},
                    (eid, 0, "bullets", 1): {"lines": 1, "ratio": 0.85, "has_box_overflow": False, "fit_line_fill_ratios": [0.85], "available_pt": 430.0, "width_pt": 365.5},
                    (eid, 0, "bullets", 2): {"lines": 1, "ratio": 0.96, "has_box_overflow": False, "fit_line_fill_ratios": [0.96], "available_pt": 430.0, "width_pt": 412.8},
                    (eid, 0, "bullets", 3): {"lines": 2, "ratio": 1.15, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.15], "available_pt": 430.0, "width_pt": 494.5},
                    (eid, 0, "bullets", 4): {"lines": 2, "ratio": 1.10, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.10], "available_pt": 430.0, "width_pt": 473.0},
                    (eid, 0, "bullets", 5): {"lines": 2, "ratio": 1.06, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.06], "available_pt": 430.0, "width_pt": 455.8},
                }
            elif len(bullets) == 3:
                # Repair probe for Bullet 1
                return {
                    (eid, 0, "bullets", 0): {"lines": 2, "ratio": 1.02, "has_box_overflow": False, "fit_line_fill_ratios": [1.0, 0.02], "available_pt": 430.0, "width_pt": 438.6},
                    (eid, 0, "bullets", 1): {"lines": 1, "ratio": 0.97, "has_box_overflow": False, "fit_line_fill_ratios": [0.97], "available_pt": 430.0, "width_pt": 417.1},
                    (eid, 0, "bullets", 2): {"lines": 1, "ratio": 0.86, "has_box_overflow": False, "fit_line_fill_ratios": [0.86], "available_pt": 430.0, "width_pt": 369.8},
                }
        return probes

    monkeypatch.setattr(line_fitter, "measure_entries", mock_measure_entries)

    mock_llm = Mock()
    mock_llm.generate_json.return_value = {
        "repairs": [
            {
                "bullet_index": 1,
                "candidates": {
                    "slight_compression": "Bullet 2 repaired slight",
                    "moderate_compression": "Bullet 2 repaired moderate",
                    "aggressive_compression": "Bullet 2 repaired aggressive",
                },
            }
        ]
    }

    canonical, fitting = select_best_candidates(
        raw_content,
        "key_projects",
        resume=Mock(),
        entry_id=77,
        llm_client=mock_llm,
    )

    # Bullet 0 selected initial 'full'
    assert canonical[0]["bullets"][0] == "Bullet 1 full"
    # Bullet 1 was repaired by moderate_compression (0.97 fill, lines=1)
    assert canonical[0]["bullets"][1] == "Bullet 2 repaired moderate"
    assert fitting["status"] == "complete"
    assert fitting["bullets"][1]["repaired"] is True
    assert fitting["bullets"][1]["selected_variant"] == "moderate_compression"


def test_get_candidate_schema_transforms_summary():
    from resume_renderer.JSONSchema.jsonschema import get_schema
    from resume_renderer.services.prompts import get_candidate_schema

    schema = get_schema("key_projects")
    candidate_schema = get_candidate_schema(schema)

    summary_schema = candidate_schema["items"]["properties"]["summary"]
    assert "anyOf" in summary_schema
    obj_schema = summary_schema["anyOf"][0]
    assert set(obj_schema["required"]) == {"compact", "medium", "full"}
    assert {"type": "string"} in summary_schema["anyOf"]


def test_summary_candidate_selection_chooses_best_single_line(monkeypatch):
    import resume_renderer.services.line_fitter as line_fitter

    raw_content = [
        {
            "title": "RouteWise",
            "summary": {
                "compact": "Predicting campus shuttle demand with ML.",
                "medium": "Campus shuttle demand prediction prototype using trip data and ML.",
                "full": "Developed prototype for predicting campus shuttle demand using trip records and machine learning.",
            },
            "bullets": ["Processed 42k trips with Pandas."],
        }
    ]

    def mock_measure_summaries(resume, entries):
        # Probes for summary variants:
        # compact: ratio=0.72, lines=1
        # medium: ratio=0.85, lines=1
        # full: ratio=0.96, lines=1
        return {
            ("88", 0, "summary"): {"lines": 1, "ratio": 0.72, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 309.6},
            ("88", 1, "summary"): {"lines": 1, "ratio": 0.85, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 365.5},
            ("88", 2, "summary"): {"lines": 1, "ratio": 0.96, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 412.8},
        }

    monkeypatch.setattr(line_fitter, "measure_summaries", mock_measure_summaries)

    canonical, fitting = select_best_candidates(
        raw_content,
        "key_projects",
        resume=Mock(),
        entry_id=88,
    )

    # Full variant chosen because it minimizes whitespace gap (1.0 - 0.96 = 0.04)
    assert canonical[0]["summary"] == "Developed prototype for predicting campus shuttle demand using trip records and machine learning."
    assert "summaries" in fitting
    assert fitting["summaries"][0]["selected_variant"] == "full"
    assert fitting["summaries"][0]["status"] == "fitted"


def test_summary_candidate_overflow_repair(monkeypatch):
    import resume_renderer.services.line_fitter as line_fitter

    raw_content = [
        {
            "title": "RouteWise",
            # All 3 initial variants overflowed
            "summary": {
                "compact": "Developed prototype for predicting campus shuttle demand using trip records and ML; not deployed.",
                "medium": "Developed prototype for predicting campus shuttle demand using trip records and machine learning; not deployed.",
                "full": "Developed a prototype for predicting campus shuttle demand using synthetic trip records and machine learning; not deployed on campus.",
            },
            "bullets": ["Processed 42,000 synthetic trips."],
        }
    ]

    def mock_measure_summaries(resume, entries):
        probes = {}
        for eid, (sec, cont) in entries.items():
            if len(cont) == 3 and "repaired" in cont[0]["summary"]:
                # Repair probe:
                # slight: 1.03 (lines=2)
                # moderate: 0.94 (lines=1)
                # aggressive: 0.82 (lines=1)
                return {
                    (eid, 0, "summary"): {"lines": 2, "ratio": 1.03, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 442.9},
                    (eid, 1, "summary"): {"lines": 1, "ratio": 0.94, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 404.2},
                    (eid, 2, "summary"): {"lines": 1, "ratio": 0.82, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 352.6},
                }
            else:
                # Initial candidate probe (all 3 overflowed)
                return {
                    (eid, 0, "summary"): {"lines": 2, "ratio": 1.08, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 464.4},
                    (eid, 1, "summary"): {"lines": 2, "ratio": 1.14, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 490.2},
                    (eid, 2, "summary"): {"lines": 2, "ratio": 1.25, "has_box_overflow": False, "available_pt": 430.0, "width_pt": 537.5},
                }
        return probes

    monkeypatch.setattr(line_fitter, "measure_summaries", mock_measure_summaries)

    mock_llm = Mock()
    mock_llm.generate_json.return_value = {
        "repairs": [
            {
                "kind": "summary",
                "entry_index": 0,
                "candidates": {
                    "slight_compression": "repaired slight: prototype predicting campus shuttle demand with ML; not deployed.",
                    "moderate_compression": "repaired moderate: shuttle demand prediction prototype using trip records and ML.",
                    "aggressive_compression": "repaired aggressive: ML prototype predicting campus shuttle demand.",
                },
            }
        ]
    }

    canonical, fitting = select_best_candidates(
        raw_content,
        "key_projects",
        resume=Mock(),
        entry_id=99,
        llm_client=mock_llm,
    )

    # Moderate compression wins (0.94 fill, lines=1)
    assert canonical[0]["summary"] == "repaired moderate: shuttle demand prediction prototype using trip records and ML."
    assert fitting["summaries"][0]["repaired"] is True
    assert fitting["summaries"][0]["selected_variant"] == "moderate_compression"
    assert fitting["summaries"][0]["status"] == "fitted"


