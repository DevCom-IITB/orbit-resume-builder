"""Local editing tools: deterministic suggestions, never automatic wording edits.

Offsets refer to the supplied, unmodified string. Suggestions are advisory;
existing candidate validation and actual-template measurement decide acceptance.
"""

import re


_QUALIFICATIONS = re.compile(
    r"\b(?:not\s+(?:deployed|validated|tested)|prototype|exploratory|synthetic"
    r"|local(?:ly)?(?:\s+load)?\s+tests?|held[- ]out(?:\s+test)?"
    r"|geographically\s+separated|median|mean\s+absolute\s+error"
    r"|root\s+mean\s+squared?\s+error)\b",
    re.I,
)


def _span(match):
    return {"text": match[0], "start": match.start(), "end": match.end()}


def calculate_width_budget(measurement, target_pt, low, high, *, summary=False):
    """Compute point budgets; no conversion from points to exact word counts."""
    available = measurement["available_pt"]
    width = measurement["width_pt"]
    wrapping = measurement["lines"] > 1 or measurement.get("has_box_overflow", False)
    if wrapping or width > available * (1 if summary else high):
        direction = "shorten"
    elif not summary and width < available * low:
        direction = "expand_supported_only"
    else:
        direction = "keep"
    return {
        "direction": direction,
        "available_pt": available,
        "target_pt": round(target_pt, 2),
        "one_line_range_pt": [round(available * low, 2), round(available * high, 2)],
        "difference_to_target_pt": round(width - target_pt, 2),
        "signed_change_needed_pt": round(target_pt - width, 2),
        "minimum_reduction_pt": round(max(0, width - available * high), 2),
        "current_line_widths_pt": measurement.get("line_widths_pt"),
        "current_line_fill_ratios": measurement.get("fit_line_fill_ratios"),
        "current_line_count": measurement.get("lines"),
        "measurement_basis": measurement.get("line_measurement", "estimated"),
        "requires_remeasurement": True,
    }


def find_editing_options(text, filler_words, compression_rules, *, original=""):
    """Return source-positioned operations without deciding semantic importance."""
    filler = [
        {**_span(match), "operation": "consider_removal"}
        for match in re.finditer(r"\b[A-Za-z]+\b", text)
        if match[0].lower() in filler_words
    ]
    compressions, expansions = [], []
    for pattern, replacement in compression_rules:
        source_phrase = re.search(rf"\b{pattern}\b", original, re.I)
        if source_phrase and len(source_phrase[0]) > len(replacement):
            for match in re.finditer(rf"\b{re.escape(replacement)}\b", text):
                expansions.append(
                    {
                        **_span(match),
                        "operation": "consider_source_backed_expansion",
                        "replacement": source_phrase[0],
                        "source_ref": _span(source_phrase),
                    }
                )
        for match in re.finditer(rf"\b{pattern}\b", text, re.I):
            # E.g. 'NLP' already has no useful shorter equivalent here.
            if len(replacement) < len(match[0]):
                compressions.append(
                    {
                        **_span(match),
                        "operation": "consider_equivalent_abbreviation",
                        "replacement": replacement,
                        "characters_saved": len(match[0]) - len(replacement),
                    }
                )
    return {
        "filler_candidates": filler,
        "compression_candidates": compressions,
        "expansion_candidates": expansions,
    }


def build_guidance(
    original,
    texts,
    measurements,
    target_pt,
    low,
    high,
    *,
    summary,
    split_allowed,
    filler_words,
    compression_rules,
    numeric_inventory,
):
    """Prepare evidence and a bounded editing sequence for the existing model call."""
    return {
        "authority": "advisory_edits_backend_validates_and_measures",
        "source_constraints": {
            "numeric_inventory": dict(numeric_inventory),
            "qualification_spans": [
                _span(m) for m in _QUALIFICATIONS.finditer(original)
            ],
            "scope": "original bullet or summary; not independent semantic verification",
        },
        "current_candidates": [
            {
                "candidate_index": index,
                "width_budget": calculate_width_budget(
                    measurement,
                    target_pt,
                    low,
                    high,
                    summary=summary,
                ),
                "editing_options": find_editing_options(
                    text,
                    filler_words,
                    compression_rules,
                    original=original,
                ),
            }
            for index, (text, measurement) in enumerate(zip(texts, measurements))
        ],
        "editing_order": [
            "Keep accepted wording; backend already skips resolved one-line items.",
            "For overflow, consider contextual filler removal and equivalent abbreviations first.",
            "Rewrite or omit secondary detail only if core meaning and factual qualifications survive.",
            (
                "If distinct accomplishments remain too dense, propose two complete bullets."
                if split_allowed and not summary
                else "Do not split this item."
            ),
            (
                "Never expand a short summary."
                if summary
                else "For underfill, expand only supported wording; retain short text if no useful expansion exists."
            ),
            "Return schema-valid wording; Python validates, measures, and ranks it.",
        ],
    }
