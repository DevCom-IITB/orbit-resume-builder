"""PDF geometry tests use in-memory documents and never call a model."""

import fitz
import pytest

from resume_renderer.services.line_fitter import _measurement_status, _rank
from resume_renderer.services.rendered_measurement import (
    TEX_PER_PDF_PT,
    compilation_warnings,
    rendered_measurements,
)


def pdf_with_markers(pages, *, rotated=False):
    """Each row is (marker ID or None, text, baseline), in PDF coordinates."""
    with fitz.open() as doc:
        for rows in pages:
            page = doc.new_page(width=600, height=800)
            for i, text, y in rows:
                page.insert_text((50, y), text, fontsize=10)
                if i is not None:
                    width = fitz.get_text_length(text, fontsize=10)
                    page.insert_link(
                        {
                            "kind": fitz.LINK_URI,
                            "from": fitz.Rect(50, y - 12, 50 + width, y + 3),
                            "uri": f"resumefit:{i}",
                        }
                    )
            if rotated:
                page.set_rotation(90)
        return doc.tobytes()


def base(available=500, lines=2, ratio=1.95):
    return {
        "available_pt": available,
        "width_pt": available * ratio,
        "ratio": ratio,
        "lines": lines,
    }


def test_repeated_text_is_mapped_by_marker_not_string():
    pdf = pdf_with_markers(
        [
            [
                (0, "Repeated text", 60),
                (0, "Short tail", 80),
                (1, "Repeated text", 120),
                (None, "Unselected text", 140),
            ]
        ]
    )
    result = rendered_measurements(pdf, {0: base(), 1: base(lines=1)})
    assert result[0]["line_measurement"] == "rendered_pdf"
    assert result[0]["lines"] == 2
    assert result[1]["lines"] == 1
    expected = fitz.get_text_length("Short tail", fontsize=10) * TEX_PER_PDF_PT
    assert result[0]["line_widths_pt"][1] == pytest.approx(expected, abs=0.02)
    assert result[0]["line_pages"] == [1, 1]
    assert result[1]["line_widths_pt"][0] == result[0]["line_widths_pt"][0]


def test_markers_can_span_pages_without_mixing_neighboring_bullets():
    pdf = pdf_with_markers(
        [[(0, "First page", 760)], [(0, "Second page", 60), (1, "Other bullet", 90)]]
    )
    result = rendered_measurements(pdf, {0: base(), 1: base(lines=1)})
    assert result[0]["line_pages"] == [1, 2]
    assert result[0]["lines"] == 2
    assert result[1]["line_pages"] == [2]


@pytest.mark.parametrize(
    "pdf", [b"", b"not a PDF", pdf_with_markers([[(None, "No markers", 60)]])]
)
def test_missing_or_invalid_mapping_explicitly_keeps_estimate(pdf):
    source = base()
    result = rendered_measurements(pdf, {0: source})
    assert result[0]["line_measurement"] == "estimated"
    assert result[0]["line_measurement_reason"]
    assert "line_widths_pt" not in result[0]
    assert source == base()


def test_rotated_page_is_not_reported_as_a_precise_mapping():
    pdf = pdf_with_markers([[(0, "Rotated text", 60)]], rotated=True)
    assert rendered_measurements(pdf, {0: base()})[0]["line_measurement"] == "estimated"


def test_actual_box_overflow_is_distinct_from_wrapping():
    pdf = pdf_with_markers([[(0, "A long unbrokenidentifier", 60)]])
    actual = rendered_measurements(pdf, {0: base(available=20, lines=1)})[0]
    assert actual["has_box_overflow"] is True
    assert actual["overflow_pt"] > 20
    measurement = {**base(available=20, lines=1), **actual}
    assert _measurement_status(measurement, 0.88, 1.0) == "box_overflow"


@pytest.mark.parametrize(
    "fills,status",
    [([0.99, 0.35], "short_spillover"), ([0.99, 0.94], "full_two_line_fallback")],
)
def test_actual_lines_override_misleading_natural_width_estimate(fills, status):
    measurement = {
        **base(),
        "line_measurement": "rendered_pdf",
        "fit_line_fill_ratios": fills,
        "has_box_overflow": False,
    }
    assert _measurement_status(measurement, 0.88, 1.0) == status
    assert _rank(measurement, 0.88, 1.0)[0] == (
        1 if status == "full_two_line_fallback" else 3
    )


def test_both_lines_must_be_full_for_a_two_line_fallback():
    measurement = {
        **base(),
        "line_measurement": "rendered_pdf",
        "fit_line_fill_ratios": [0.6, 0.96],
        "has_box_overflow": False,
    }
    assert _rank(measurement, 0.88, 1.0)[0] == 3


def test_warnings_are_document_scoped_not_falsely_attributed_to_bullets():
    log = (
        "RF-W:0:600pt:500pt\n"
        "Overfull \\hbox (12.5pt too wide) in paragraph at lines 25--26\n"
        "Underfull \\hbox (badness 10000) at line 30\n"
    )
    warnings = compilation_warnings(log)
    assert [w["kind"] for w in warnings] == ["overfull", "underfull"]
    assert all(w["scope"] == "document" and "bullet_id" not in w for w in warnings)
    assert warnings[0]["source_lines"] == [25, 26]


def test_overlapping_markers_fall_back_instead_of_sharing_text():
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 60), "Ambiguous text")
        for i in (0, 1):
            page.insert_link(
                {
                    "kind": fitz.LINK_URI,
                    "from": fitz.Rect(50, 45, 180, 65),
                    "uri": f"resumefit:{i}",
                }
            )
        pdf = doc.tobytes()
    result = rendered_measurements(pdf, {0: base(), 1: base()})
    assert all(m["line_measurement"] == "estimated" for m in result.values())


def test_tiny_empty_page_continuation_is_ignored_only_between_real_text():
    with fitz.open() as doc:
        for pn, text in enumerate(("Before page break", "After page break")):
            page = doc.new_page(width=600, height=800)
            page.insert_text((50, 60), text, fontsize=10)
            page.insert_link(
                {
                    "kind": fitz.LINK_URI,
                    "from": fitz.Rect(50, 48, 180, 63),
                    "uri": "resumefit:0",
                }
            )
            if pn:
                page.insert_link(
                    {
                        "kind": fitz.LINK_URI,
                        "from": fitz.Rect(35, 2, 550, 4),
                        "uri": "resumefit:0",
                    }
                )
        pdf = doc.tobytes()
    actual = rendered_measurements(pdf, {0: base()})[0]
    assert actual["line_measurement"] == "rendered_pdf"
    assert actual["line_pages"] == [1, 2]
    assert actual["ignored_page_boundary_markers"] == 1


def test_unexplained_empty_marker_is_not_silently_ignored():
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 60), "Some text", fontsize=10)
        for rect in (fitz.Rect(50, 48, 180, 63), fitz.Rect(35, 2, 550, 4)):
            page.insert_link(
                {"kind": fitz.LINK_URI, "from": rect, "uri": "resumefit:0"}
            )
        pdf = doc.tobytes()
    assert rendered_measurements(pdf, {0: base()})[0]["line_measurement"] == "estimated"
