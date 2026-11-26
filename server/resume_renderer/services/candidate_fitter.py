"""
Candidate-based line optimization for resume bullet points.

Generates 3 candidates per bullet with varied line fit percentage ranges,
deterministically measures all candidates in a single LaTeX compile job,
and selects the best candidate that fits the line width while minimizing whitespace.
"""

import copy
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard candidate variants in order of target line fill
CANDIDATE_VARIANTS = ("compact", "medium", "full")

# Repair candidate variants for secondary overflow optimization
REPAIR_VARIANTS = ("slight_compression", "moderate_compression", "aggressive_compression")

OVERFLOW_REPAIR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["repairs"],
    "properties": {
        "repairs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["candidates"],
                "properties": {
                    "kind": {"type": "string"},
                    "bullet_index": {"type": "integer"},
                    "entry_index": {"type": "integer"},
                    "index": {"type": "integer"},
                    "candidates": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "slight_compression",
                            "moderate_compression",
                            "aggressive_compression",
                        ],
                        "properties": {
                            "slight_compression": {"type": "string"},
                            "moderate_compression": {"type": "string"},
                            "aggressive_compression": {"type": "string"},
                        },
                    },
                },
            },
        }
    },
}


def has_candidates(content: Any) -> bool:
    """Check if the content structure contains candidate objects for bullets or summaries."""
    if not isinstance(content, list):
        return False
    for item in content:
        if not isinstance(item, dict):
            continue
        bullets = item.get("bullets")
        if isinstance(bullets, list) and bullets:
            for b in bullets:
                if isinstance(b, dict) and any(k in b for k in ("compact", "medium", "full", "candidates")):
                    return True
                if isinstance(b, (list, tuple)) and len(b) > 1:
                    return True
        summary = item.get("summary")
        if isinstance(summary, dict) and any(k in summary for k in ("compact", "medium", "full", "candidates")):
            return True
        # Scholastic achievements check
        text = item.get("text")
        if isinstance(text, dict) and any(k in text for k in ("compact", "medium", "full", "candidates")):
            return True
    return False


def _extract_variants(val: Any) -> List[Tuple[str, str]]:
    """Extract (variant_label, text) pairs from a candidate value."""
    if isinstance(val, dict):
        if "candidates" in val and isinstance(val["candidates"], list):
            return [(f"candidate_{i}", str(c).strip()) for i, c in enumerate(val["candidates"]) if str(c).strip()]
        res = []
        for v in CANDIDATE_VARIANTS:
            if v in val and isinstance(val[v], str) and val[v].strip():
                res.append((v, val[v].strip()))
        if res:
            return res
        return [(k, str(v).strip()) for k, v in val.items() if str(v).strip()]
    if isinstance(val, (list, tuple)):
        return [(f"candidate_{i}", str(c).strip()) for i, c in enumerate(val) if str(c).strip()]
    if isinstance(val, str) and val.strip():
        return [("default", val.strip())]
    return [("default", "")]


def score_candidate_measurement(measurement: Dict[str, Any]) -> Tuple[int, float]:
    """
    Deterministically score a candidate measurement. Lower tuple is better.

    Rank hierarchy:
    Tier 0: Fits cleanly on 1 line (lines == 1, no box overflow, ratio <= 1.005).
            Whitespace distance = (1.0 - ratio).
            Smaller whitespace distance wins! E.g. ratio 0.97 (gap 0.03) beats ratio 0.85 (gap 0.15).
    Tier 1: Two well-filled lines (lines == 2, no box overflow, both lines >= 0.82 fill).
            Whitespace distance = (1.0 - trailing line fill).
    Tier 2: Single line underfilled (lines == 1, but ratio < 0.80).
            Whitespace distance = (1.0 - ratio).
    Tier 3: Wrapped with short spillover / overflow (lines >= 2 with short trailing line).
            Whitespace distance = (1.0 - trailing line fill).
    """
    lines = measurement.get("lines", 1)
    ratio = measurement.get("ratio", 0.0)
    overflow = measurement.get("has_box_overflow", False)
    fills = measurement.get("fit_line_fill_ratios") or [ratio]

    # Tier 0: Single line fit without box overflow
    if lines == 1 and not overflow and ratio <= 1.025:
        whitespace_gap = max(0.0, 1.0 - ratio)
        return (0, whitespace_gap)

    # Tier 1: Two well-filled lines without overflow
    if lines == 2 and not overflow and len(fills) == 2 and all(f >= 0.82 for f in fills):
        trailing_gap = max(0.0, 1.0 - fills[-1])
        return (1, trailing_gap)

    # Tier 2: Single line underfilled
    if lines == 1 and not overflow:
        return (2, 1.0 - ratio)

    # Tier 3: Wrapped with short spillover / overflow
    trailing_fill = fills[-1] if fills else max(0.0, ratio - (lines - 1))
    return (3, max(0.0, 1.0 - trailing_fill))


def estimate_fallback_measurement(text: str, available_pt: float = 430.0) -> Dict[str, Any]:
    """
    Offline deterministic estimation when Docker/LaTeX measurement is unavailable.
    Uses ~93 characters as typical single-line LaTeX capacity for resume bullets.
    """
    approx_chars_per_line = 93.0
    text_len = len(text)
    char_width = available_pt / approx_chars_per_line
    ratio = round(text_len / approx_chars_per_line, 4)
    lines = max(1, math.ceil(text_len / approx_chars_per_line)) if text_len > 0 else 1

    if lines == 1:
        fills = [ratio]
    else:
        fills = [1.0] * (lines - 1) + [round(ratio - (lines - 1), 4)]

    return {
        "width_pt": round(text_len * char_width, 2),
        "available_pt": available_pt,
        "ratio": ratio,
        "lines": lines,
        "fit_line_fill_ratios": fills,
        "has_box_overflow": False,
        "line_measurement": "estimated",
    }


def is_bullet_overflown(measurement: Dict[str, Any]) -> bool:
    """Check if a measurement indicates overflow past line width or multiple lines."""
    if not isinstance(measurement, dict):
        return False
    lines = measurement.get("lines", 1)
    ratio = measurement.get("ratio", 0.0)
    overflow = measurement.get("has_box_overflow", False)
    return lines > 1 or ratio > 1.02 or overflow


def calculate_overflow_metrics(
    text: str,
    measurement: Dict[str, Any],
    lower_limit_ratio: float = 0.85,
) -> Dict[str, Any]:
    """Calculate real-time LaTeX width deltas and character bounds for shortening."""
    text_len = len(text)
    width_pt = float(measurement.get("width_pt", 0.0))
    available_pt = float(measurement.get("available_pt", 430.0))
    if available_pt <= 0:
        available_pt = 430.0
    ratio = float(measurement.get("ratio", width_pt / available_pt if available_pt else 1.0))
    lines = int(measurement.get("lines", 1))

    diff_pt = max(0.0, round(width_pt - available_pt, 2))
    overflow_pct = round(max(0.0, (ratio - 1.0) * 100), 1)

    # Estimated characters to cut to clear overflow with safety margin
    if width_pt > 0 and diff_pt > 0:
        overflow_chars = max(1, math.ceil(text_len * (diff_pt / width_pt)))
    else:
        overflow_chars = max(2, text_len - 92 if text_len > 92 else 3)

    # Upper bound (clears overflow, ~96-98% fill)
    max_chars = max(70, text_len - overflow_chars - 2)
    # Lower limit bound (~85% fill)
    if width_pt > 0:
        min_chars = max(65, round(text_len * (lower_limit_ratio * available_pt / width_pt)))
    else:
        min_chars = max(65, round(text_len * lower_limit_ratio))
    if min_chars >= max_chars:
        min_chars = max(65, max_chars - 12)

    return {
        "text_len": text_len,
        "width_pt": width_pt,
        "available_pt": available_pt,
        "ratio": ratio,
        "lines": lines,
        "diff_pt": diff_pt,
        "overflow_pct": overflow_pct,
        "overflow_chars": overflow_chars,
        "max_chars": max_chars,
        "min_chars": min_chars,
        "lower_limit_ratio": lower_limit_ratio,
    }


def build_overflow_repair_prompt(
    overflown_items: List[Dict[str, Any]],
    section_key: str,
) -> str:
    """Build targeted repair prompt injecting real-time LaTeX width, overflow %, and exact shortening delta."""
    prompt_lines = [
        "You are an expert resume line optimizer. The following bullet points or project taglines exceeded the line width in the actual LaTeX document rendering.",
        "For each item, you are provided with the real-time LaTeX measurement, exact point overflow, and the exact character difference required to shorten the item.",
        "",
        "YOUR GOAL: Shorten each item to cut the overflow so it fits strictly on EXACTLY 1 LINE, bounded between the overflow cutoff and the lower limit (to avoid excessive whitespace).",
        "",
        "STRICT RULES:",
        "1. Fit strictly on 1 line. NEVER wrap onto a second line.",
        "2. NEVER invent facts, metrics, or technologies.",
        "3. Retain ALL numbers, metrics, and core technical skills.",
        "4. Cut verbose phrasing, compress clauses, or remove filler words to achieve the target length.",
        "5. Generate exactly 3 shortened candidate variants for each item:",
        "   - slight_compression: Cut just enough to clear the overflow (~96%-98% line fill). Minimal wording change.",
        "   - moderate_compression: Midpoint compression (~90%-94% line fill). Balanced tightening of clauses.",
        "   - aggressive_compression: Shorten down towards the lower limit (~85%-88% line fill). Core action + metric.",
        "",
    ]
    for item in overflown_items:
        m = item["metrics"]
        mid_chars = round((m["max_chars"] + m["min_chars"]) / 2)
        if item.get("kind") == "summary":
            prompt_lines.append(f"PROJECT SUMMARY / TAGLINE (Entry #{item.get('entry_index', 0)}):")
        else:
            prompt_lines.append(f"BULLET #{item.get('bullet_index', item.get('index', 0))}:")
        prompt_lines.append(f"  Current Text: \"{item['text']}\"")
        prompt_lines.append(
            f"  Current Length: {m['text_len']} chars | Measured Width: {m['width_pt']}pt / {m['available_pt']}pt ({m['ratio']:.1%} fill, {m['lines']} lines)"
        )
        prompt_lines.append(
            f"  EXACT OVERFLOW: +{m['diff_pt']}pt (+{m['overflow_pct']}%) -> Must cut AT LEAST {m['overflow_chars']} characters to fit on 1 line."
        )
        prompt_lines.append(
            f"  SHORTENING BOUNDS: Target between {m['min_chars']} chars (lower limit, {m['lower_limit_ratio']:.0%} fill) and {m['max_chars']} chars (upper limit, 98% fill)."
        )
        prompt_lines.append(f"    * slight_compression target: ~{m['max_chars']} chars")
        prompt_lines.append(f"    * moderate_compression target: ~{mid_chars} chars")
        prompt_lines.append(f"    * aggressive_compression target: ~{m['min_chars']} chars")
        if item.get("kind") == "summary":
            prompt_lines.append("  STRICT RULE: The project summary/tagline MUST fit on EXACTLY 1 LINE. NEVER wrap onto a second line.")
        prompt_lines.append("")

    return "\n".join(prompt_lines)


def repair_overflown_bullets(
    canonical_content: List[Dict[str, Any]],
    bullet_reports: List[Dict[str, Any]],
    section_key: str,
    *,
    resume: Any = None,
    entry_id: Any = None,
    llm_client: Any = None,
    summary_reports: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Secondary candidate optimizer pass for overflown bullets and taglines (>100% line width / lines > 1).
    Requests 3 shortened candidates, probes their measurements, and deterministically
    picks the best 1-line candidate minimizing whitespace.
    """
    if llm_client is None:
        return canonical_content, bullet_reports

    overflown_items: List[Dict[str, Any]] = []
    # Collect overflown bullets
    for report_idx, report in enumerate(bullet_reports or []):
        if is_bullet_overflown(report.get("measurement", {})):
            metrics = calculate_overflow_metrics(
                report["text"],
                report["measurement"],
            )
            overflown_items.append(
                {
                    "kind": "bullet",
                    "report_idx": report_idx,
                    "entry_index": report["entry_index"],
                    "bullet_index": report.get("bullet_index", 0),
                    "text": report["text"],
                    "metrics": metrics,
                    "current_score": score_candidate_measurement(report["measurement"]),
                }
            )

    # Collect overflown summaries
    if summary_reports:
        for report_idx, report in enumerate(summary_reports):
            if is_bullet_overflown(report.get("measurement", {})):
                metrics = calculate_overflow_metrics(
                    report["text"],
                    report["measurement"],
                )
                overflown_items.append(
                    {
                        "kind": "summary",
                        "report_idx": report_idx,
                        "entry_index": report["entry_index"],
                        "bullet_index": report["entry_index"],
                        "text": report["text"],
                        "metrics": metrics,
                        "current_score": score_candidate_measurement(report["measurement"]),
                    }
                )

    if not overflown_items:
        return canonical_content, bullet_reports

    prompt = build_overflow_repair_prompt(overflown_items, section_key)

    try:
        response = llm_client.generate_json(
            prompt, response_schema=OVERFLOW_REPAIR_SCHEMA
        )
        repairs = response.get("repairs", []) if isinstance(response, dict) else []
    except Exception as exc:
        logger.warning(
            "Overflow repair LLM generation failed (%s); retaining chosen wording.", exc
        )
        return canonical_content, bullet_reports

    # Index repairs by (kind, identifier) with positional fallback
    repair_map: Dict[Tuple[str, int], Dict[str, str]] = {}
    for idx, r in enumerate(repairs):
        if not isinstance(r, dict):
            continue
        cands = r.get("candidates")
        if not isinstance(cands, dict):
            continue
        kind = r.get("kind")
        b_idx = r.get("bullet_index", r.get("index", r.get("entry_index")))
        if kind and b_idx is not None:
            repair_map[(kind, b_idx)] = cands
        elif b_idx is not None:
            if idx < len(overflown_items):
                repair_map[(overflown_items[idx]["kind"], b_idx)] = cands
            else:
                repair_map[("bullet", b_idx)] = cands
        elif idx < len(overflown_items):
            item = overflown_items[idx]
            repair_map[(item["kind"], item["bullet_index"])] = cands

    # 1. Probing bullet repairs
    bullet_repair_probes: List[Tuple[int, str, str]] = []
    for item in overflown_items:
        if item["kind"] != "bullet":
            continue
        cands = repair_map.get(("bullet", item["bullet_index"]))
        if not cands:
            continue
        variants = _extract_variants(cands)
        for var_name, cand_text in variants:
            bullet_repair_probes.append((item["report_idx"], var_name, cand_text))

    measured_bullet_repair_probes: Dict[int, Dict[str, Any]] = {}
    if bullet_repair_probes:
        probe_bullets_by_entry: Dict[int, List[str]] = {}
        for rep_idx, var_name, cand_text in bullet_repair_probes:
            ei = bullet_reports[rep_idx]["entry_index"]
            probe_bullets_by_entry.setdefault(ei, []).append(cand_text)

        probe_content = copy.deepcopy(canonical_content)
        for ei, p_bullets in probe_bullets_by_entry.items():
            if ei < len(probe_content) and isinstance(probe_content[ei], dict):
                probe_content[ei]["bullets"] = p_bullets

        if resume is not None and entry_id is not None:
            try:
                from .line_fitter import measure_entries

                measured = measure_entries(resume, {str(entry_id): (section_key, probe_content)})
                entry_counter: Dict[int, int] = {}
                for probe_i, (rep_idx, var_name, cand_text) in enumerate(bullet_repair_probes):
                    ei = bullet_reports[rep_idx]["entry_index"]
                    bi_seq = entry_counter.get(ei, 0)
                    entry_counter[ei] = bi_seq + 1
                    key = (str(entry_id), ei, "bullets", bi_seq)
                    if key in measured:
                        measured_bullet_repair_probes[probe_i] = measured[key]
            except Exception as exc:
                logger.warning(
                    "LaTeX measurement probe failed for bullet overflow repair (%s); using fallback estimation.",
                    exc,
                )

        for probe_i, (rep_idx, var_name, cand_text) in enumerate(bullet_repair_probes):
            if probe_i not in measured_bullet_repair_probes:
                avail = bullet_reports[rep_idx].get("measurement", {}).get("available_pt", 430.0)
                measured_bullet_repair_probes[probe_i] = estimate_fallback_measurement(cand_text, available_pt=avail)

        # Score and apply bullet repairs
        bullet_repairs_by_report: Dict[int, List[Dict[str, Any]]] = {}
        for probe_i, (rep_idx, var_name, cand_text) in enumerate(bullet_repair_probes):
            m = measured_bullet_repair_probes[probe_i]
            score = score_candidate_measurement(m)
            bullet_repairs_by_report.setdefault(rep_idx, []).append(
                {"variant": var_name, "text": cand_text, "measurement": m, "score": score}
            )

        for item in overflown_items:
            if item["kind"] != "bullet":
                continue
            rep_idx = item["report_idx"]
            rep_candidates = bullet_repairs_by_report.get(rep_idx, [])
            if not rep_candidates:
                continue

            best_repair = min(rep_candidates, key=lambda c: c["score"])
            if best_repair["score"] < item["current_score"]:
                ei = item["entry_index"]
                bi = item["bullet_index"]
                canonical_content[ei]["bullets"][bi] = best_repair["text"]

                report = bullet_reports[rep_idx]
                report["text"] = best_repair["text"]
                report["selected_variant"] = best_repair["variant"]
                report["measurement"] = best_repair["measurement"]
                report["status"] = "fitted" if best_repair["score"][0] == 0 else "partial"
                report["repaired"] = True
                report["reason"] = (
                    f"Repaired overflow: selected '{best_repair['variant']}' candidate "
                    f"(score={best_repair['score']}, ratio={best_repair['measurement'].get('ratio', 0):.2%})."
                )
                report["repair_candidates"] = [
                    {
                        "variant": c["variant"],
                        "text": c["text"],
                        "ratio": c["measurement"].get("ratio", 0),
                        "lines": c["measurement"].get("lines", 1),
                        "score": c["score"],
                    }
                    for c in rep_candidates
                ]

    # 2. Probing summary repairs
    summary_repair_probes: List[Tuple[int, str, str]] = []
    if summary_reports:
        for item in overflown_items:
            if item["kind"] != "summary":
                continue
            cands = repair_map.get(("summary", item["bullet_index"]))
            if not cands:
                continue
            variants = _extract_variants(cands)
            for var_name, cand_text in variants:
                summary_repair_probes.append((item["report_idx"], var_name, cand_text))

    if summary_repair_probes and summary_reports:
        measured_summary_repair_probes: Dict[int, Dict[str, Any]] = {}
        if resume is not None and entry_id is not None:
            try:
                from .line_fitter import measure_summaries

                probe_summary_entries = {
                    str(entry_id): (
                        section_key,
                        [
                            {**canonical_content[summary_reports[rep_idx]["entry_index"]], "summary": cand_text}
                            for rep_idx, var_name, cand_text in summary_repair_probes
                        ],
                    )
                }
                measured = measure_summaries(resume, probe_summary_entries)
                for s_i, (rep_idx, var_name, cand_text) in enumerate(summary_repair_probes):
                    key = (str(entry_id), s_i, "summary")
                    if key in measured:
                        measured_summary_repair_probes[s_i] = measured[key]
            except Exception as exc:
                logger.warning(
                    "LaTeX measurement probe failed for summary overflow repair (%s); using fallback estimation.",
                    exc,
                )

        for s_i, (rep_idx, var_name, cand_text) in enumerate(summary_repair_probes):
            if s_i not in measured_summary_repair_probes:
                avail = summary_reports[rep_idx].get("measurement", {}).get("available_pt", 430.0)
                measured_summary_repair_probes[s_i] = estimate_fallback_measurement(cand_text, available_pt=avail)

        summary_repairs_by_report: Dict[int, List[Dict[str, Any]]] = {}
        for s_i, (rep_idx, var_name, cand_text) in enumerate(summary_repair_probes):
            m = measured_summary_repair_probes[s_i]
            score = score_candidate_measurement(m)
            summary_repairs_by_report.setdefault(rep_idx, []).append(
                {"variant": var_name, "text": cand_text, "measurement": m, "score": score}
            )

        for item in overflown_items:
            if item["kind"] != "summary":
                continue
            rep_idx = item["report_idx"]
            rep_candidates = summary_repairs_by_report.get(rep_idx, [])
            if not rep_candidates:
                continue

            best_repair = min(rep_candidates, key=lambda c: c["score"])
            if best_repair["score"] < item["current_score"]:
                ei = item["entry_index"]
                canonical_content[ei]["summary"] = best_repair["text"]

                report = summary_reports[rep_idx]
                report["text"] = best_repair["text"]
                report["selected_variant"] = best_repair["variant"]
                report["measurement"] = best_repair["measurement"]
                report["status"] = "fitted" if best_repair["score"][0] == 0 else "partial"
                report["repaired"] = True
                report["reason"] = (
                    f"Repaired overflow: selected '{best_repair['variant']}' candidate "
                    f"(score={best_repair['score']}, ratio={best_repair['measurement'].get('ratio', 0):.2%})."
                )
                report["repair_candidates"] = [
                    {
                        "variant": c["variant"],
                        "text": c["text"],
                        "ratio": c["measurement"].get("ratio", 0),
                        "lines": c["measurement"].get("lines", 1),
                        "score": c["score"],
                    }
                    for c in rep_candidates
                ]

    return canonical_content, bullet_reports


def select_best_candidates(
    content: Any,
    section_key: str,
    *,
    resume: Any = None,
    entry_id: Any = None,
    llm_client: Any = None,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Deterministically measure and select the best candidates for each bullet point
    and summary in content.

    Returns:
        (canonical_content, fitting_report)
    """
    if not isinstance(content, list) or not content:
        return content, {"status": "complete", "bullets": []}

    # Step 1: Catalog all candidate positions and assemble probe content
    # probe_map maps probe index -> (entry_idx, field, item_idx, variant_name, cand_text)
    probe_map: List[Tuple[int, str, int, str, str]] = []
    summary_map: List[Tuple[int, List[Tuple[str, str]]]] = []
    probe_content = copy.deepcopy(content)

    for ei, item in enumerate(content):
        if not isinstance(item, dict):
            continue

        # Handle bullets
        bullets = item.get("bullets")
        if isinstance(bullets, list):
            probe_bullets = []
            for bi, b in enumerate(bullets):
                variants = _extract_variants(b)
                for var_name, cand_text in variants:
                    probe_map.append((ei, "bullets", bi, var_name, cand_text))
                    probe_bullets.append(cand_text)
            probe_content[ei]["bullets"] = probe_bullets

        # Handle summary candidates
        summary = item.get("summary")
        if summary:
            variants = _extract_variants(summary)
            if variants:
                summary_map.append((ei, variants))
                probe_content[ei]["summary"] = variants[0][1]

        # Handle scholastic achievement text
        text = item.get("text")
        if text and isinstance(text, (dict, list, tuple)):
            variants = _extract_variants(text)
            probe_content[ei]["text"] = variants[0][1] if variants else ""

    # Step 2: Measure all probe bullets in a single LaTeX compile run
    measured_probes: Dict[int, Dict[str, Any]] = {}
    measured_summaries: Dict[Tuple[int, int], Dict[str, Any]] = {}
    measurement_source = "rendered_pdf"

    if resume is not None and entry_id is not None:
        try:
            from .line_fitter import measure_entries

            measured = measure_entries(resume, {str(entry_id): (section_key, probe_content)})
            for probe_idx, (ei, field, bi, var_name, cand_text) in enumerate(probe_map):
                key = (str(entry_id), ei, field, probe_idx)
                if key in measured:
                    measured_probes[probe_idx] = measured[key]
        except Exception as exc:
            logger.warning(
                "LaTeX probe measurement failed during candidate selection (%s); falling back to deterministic estimation.",
                exc,
            )
            measurement_source = "fallback_estimated"

        if summary_map:
            try:
                from .line_fitter import measure_summaries

                flat_probe_entries = []
                for ei, variants in summary_map:
                    base_item = content[ei] if isinstance(content[ei], dict) else {}
                    for var_name, cand_text in variants:
                        flat_probe_entries.append({**base_item, "summary": cand_text})

                if flat_probe_entries:
                    res = measure_summaries(resume, {str(entry_id): (section_key, flat_probe_entries)})
                    s_idx = 0
                    for ei, variants in summary_map:
                        for vi in range(len(variants)):
                            key = (str(entry_id), s_idx, "summary")
                            if key in res:
                                measured_summaries[(ei, vi)] = res[key]
                            s_idx += 1
            except Exception as exc:
                logger.warning(
                    "LaTeX summary probe measurement failed (%s); falling back to estimation.",
                    exc,
                )

    # Fill any missing measurements with deterministic fallback
    for probe_idx, (ei, field, bi, var_name, cand_text) in enumerate(probe_map):
        if probe_idx not in measured_probes:
            measured_probes[probe_idx] = estimate_fallback_measurement(cand_text)

    for ei, variants in summary_map:
        for vi, (var_name, cand_text) in enumerate(variants):
            if (ei, vi) not in measured_summaries:
                measured_summaries[(ei, vi)] = estimate_fallback_measurement(cand_text, available_pt=430.0)

    # Step 3: Group measurements by (entry_idx, field, item_idx) and pick winning candidate
    candidate_groups: Dict[Tuple[int, str, int], List[Dict[str, Any]]] = {}

    for probe_idx, (ei, field, bi, var_name, cand_text) in enumerate(probe_map):
        m = measured_probes[probe_idx]
        score = score_candidate_measurement(m)
        candidate_groups.setdefault((ei, field, bi), []).append(
            {
                "variant": var_name,
                "text": cand_text,
                "measurement": m,
                "score": score,
            }
        )

    # Step 4: Reconstruct canonical content and build fitting report
    canonical_content = copy.deepcopy(content)
    bullet_reports: List[Dict[str, Any]] = []

    for ei, item in enumerate(canonical_content):
        if not isinstance(item, dict):
            continue

        # Reconstruct bullets
        bullets = item.get("bullets")
        if isinstance(bullets, list):
            chosen_bullets = []
            for bi, b in enumerate(bullets):
                candidates = candidate_groups.get((ei, "bullets", bi), [])
                if candidates:
                    best = min(candidates, key=lambda c: c["score"])
                    chosen_bullets.append(best["text"])
                    bullet_reports.append(
                        {
                            "entry_index": ei,
                            "bullet_index": bi,
                            "selected_variant": best["variant"],
                            "text": best["text"],
                            "measurement": best["measurement"],
                            "status": "fitted" if best["score"][0] == 0 else "partial",
                            "reason": f"Selected '{best['variant']}' candidate (score={best['score']}, ratio={best['measurement'].get('ratio', 0):.2%}).",
                            "all_candidates": [
                                {
                                    "variant": c["variant"],
                                    "text": c["text"],
                                    "ratio": c["measurement"].get("ratio", 0),
                                    "lines": c["measurement"].get("lines", 1),
                                    "score": c["score"],
                                }
                                for c in candidates
                            ],
                        }
                    )
                else:
                    chosen_bullets.append(str(b))
            item["bullets"] = chosen_bullets

        # Reconstruct scholastic achievement text if candidate object was provided
        text = item.get("text")
        if isinstance(text, (dict, list, tuple)):
            variants = _extract_variants(text)
            chosen_text = variants[0][1] if variants else ""
            for v, t in variants:
                if v == "medium":
                    chosen_text = t
                    break
            item["text"] = chosen_text

    # Reconstruct summaries and build summary reports
    summary_reports: List[Dict[str, Any]] = []
    for ei, variants in summary_map:
        scored = []
        for vi, (var_name, cand_text) in enumerate(variants):
            m = measured_summaries[(ei, vi)]
            score = score_candidate_measurement(m)
            scored.append(
                {
                    "variant": var_name,
                    "text": cand_text,
                    "measurement": m,
                    "score": score,
                }
            )
        best = min(scored, key=lambda c: c["score"])
        canonical_content[ei]["summary"] = best["text"]
        summary_reports.append(
            {
                "entry_index": ei,
                "kind": "summary",
                "selected_variant": best["variant"],
                "text": best["text"],
                "measurement": best["measurement"],
                "status": "fitted" if best["score"][0] == 0 else "partial",
                "reason": f"Selected '{best['variant']}' summary candidate (score={best['score']}, ratio={best['measurement'].get('ratio', 0):.2%}).",
                "all_candidates": [
                    {
                        "variant": c["variant"],
                        "text": c["text"],
                        "ratio": c["measurement"].get("ratio", 0),
                        "lines": c["measurement"].get("lines", 1),
                        "score": c["score"],
                    }
                    for c in scored
                ],
            }
        )

    # Step 5: Check for overflown bullets and taglines, and run secondary candidate optimizer if needed
    if llm_client is not None:
        canonical_content, bullet_reports = repair_overflown_bullets(
            canonical_content,
            bullet_reports,
            section_key,
            resume=resume,
            entry_id=entry_id,
            llm_client=llm_client,
            summary_reports=summary_reports,
        )

    all_fitted = all(b.get("status") == "fitted" for b in bullet_reports) and all(
        s.get("status") == "fitted" for s in summary_reports
    )
    overall_status = "complete" if all_fitted else "partial"
    fitting_report = {
        "status": overall_status,
        "method": "candidate_selection",
        "measurement_source": measurement_source,
        "bullets": bullet_reports,
        "summaries": summary_reports,
    }

    return canonical_content, fitting_report
