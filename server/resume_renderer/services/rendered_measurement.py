"""Read diagnostic-only PDF markers; normal resume PDFs contain no markers."""

import re

import fitz

# LaTeX points (72.27/in) differ from PDF points (72/in).
TEX_PER_PDF_PT = 72.27 / 72
EDGE_TOLERANCE_PT = 0.5


def compilation_warnings(log):
    """Document-scoped warnings, never incorrectly attributed to one bullet."""
    found = []
    pattern = r"(Overfull|Underfull) \\([hv])box \(([^)]+)\)(?:[^\r\n]*?at lines? (\d+)(?:--(\d+))?)?"
    for match in re.finditer(pattern, log):
        item = {
            "scope": "document",
            "kind": match[1].lower(),
            "box": match[2],
            "detail": match[3],
        }
        if match[4]:
            item["source_lines"] = [int(match[4]), int(match[5] or match[4])]
        if item not in found:
            found.append(item)
    return found[:8]


def rendered_measurements(pdf_bytes, measurements):
    """Return per-probe additions, retaining explicit estimates on mapping failure.

    pdfTeX automatically breaks each invisible URI marker into per-line rectangles,
    including across pages. Character positions within those rectangles give ink
    widths without matching potentially repeated bullet strings.
    """
    result = {
        i: {
            "line_measurement": "estimated",
            "line_measurement_reason": "Diagnostic PDF markers could not be mapped reliably.",
        }
        for i in measurements
    }
    if not pdf_bytes:
        return result
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return result
    records, owners, ambiguous, empty_regions = {}, {}, set(), []
    try:
        for page_number, page in enumerate(doc):
            markers = []
            for link in page.get_links():
                match = re.fullmatch(r"resumefit:(\d+)", link.get("uri", ""))
                if match and int(match[1]) in measurements:
                    i = int(match[1])
                    if page.rotation:
                        ambiguous.add(i)
                        result[i]["line_measurement_reason"] = (
                            "Rotated diagnostic pages are not supported for precise mapping."
                        )
                    markers.append((i, fitz.Rect(link["from"])))
            if not markers:
                continue
            lines = []
            for bi, block in enumerate(page.get_text("rawdict")["blocks"]):
                for li, line in enumerate(block.get("lines", [])):
                    chars = [c for span in line["spans"] for c in span["chars"]]
                    lines.append(((page_number, bi, li), chars))
            for i, rect in markers:
                matched = False
                for key, chars in lines:
                    chosen = []
                    for ci, char in enumerate(chars):
                        box = fitz.Rect(char["bbox"])
                        cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
                        if not (
                            rect.x0 - 0.5 <= cx <= rect.x1 + 0.5
                            and rect.y0 - 0.5 <= cy <= rect.y1 + 0.5
                        ):
                            continue
                        if not char["c"].strip():
                            continue
                        char_key = (*key, ci)
                        previous = owners.setdefault(char_key, i)
                        if previous != i:
                            ambiguous.update((i, previous))
                            for probe in (i, previous):
                                result[probe]["line_measurement_reason"] = (
                                    "Diagnostic marker regions overlap another bullet's text."
                                )
                        chosen.append((ci, box))
                    if not chosen:
                        continue
                    matched = True
                    record = records.setdefault(i, {}).setdefault(
                        key,
                        {
                            "left": rect.x0,
                            "chars": {},
                        },
                    )
                    record["left"] = min(record["left"], rect.x0)
                    record["chars"].update(chosen)
                if not matched:
                    empty_regions.append((i, page_number, rect))
        ignored = {}
        for i, page_number, rect in empty_regions:
            current = [
                record
                for key, record in records.get(i, {}).items()
                if key[0] == page_number
            ]
            previous = any(key[0] < page_number for key in records.get(i, {}))
            first_text_y = min(
                (box.y0 for record in current for box in record["chars"].values()),
                default=-1,
            )
            # pdfTeX emits a tiny empty link continuation at a new page's top.
            # Ignore only that artifact, with real text on both sides of the break.
            if (
                previous
                and current
                and rect.height <= 3
                and rect.y1 < first_text_y - 0.5
            ):
                ignored[i] = ignored.get(i, 0) + 1
            else:
                ambiguous.add(i)
                result[i]["line_measurement_reason"] = (
                    "A diagnostic marker region contains no extractable text."
                )
        for i, measurement in measurements.items():
            if i in ambiguous or not records.get(i):
                continue
            widths, left_overflow, pages = [], [], []
            for key, record in sorted(records[i].items()):
                boxes = list(record["chars"].values())
                widths.append(
                    round(
                        (max(b.x1 for b in boxes) - record["left"]) * TEX_PER_PDF_PT, 4
                    )
                )
                left_overflow.append(
                    max(0, record["left"] - min(b.x0 for b in boxes)) * TEX_PER_PDF_PT
                )
                pages.append(key[0] + 1)
            available = measurement["available_pt"]
            overflow = max(0, max(widths) - available, max(left_overflow))
            ratios = [w / available for w in widths]
            # Font ink can protrude slightly beyond its advance width. Keep raw
            # widths/overflow, but tolerate half a TeX point for fit decisions.
            fit_ratios = [
                min(r, 1.0) if w <= available + EDGE_TOLERANCE_PT else r
                for w, r in zip(widths, ratios)
            ]
            result[i] = {
                "line_measurement": "rendered_pdf",
                "line_widths_pt": widths,
                "line_fill_ratios": [round(r, 6) for r in ratios],
                "fit_line_fill_ratios": fit_ratios,
                "line_pages": pages,
                "lines": len(widths),
                "overflow_pt": round(overflow, 4),
                "has_box_overflow": overflow > EDGE_TOLERANCE_PT,
                "estimated_lines": measurement["lines"],
            }
            if ignored.get(i):
                result[i]["ignored_page_boundary_markers"] = ignored[i]
    except Exception:
        # Measurements remain usable as estimates if PDF extraction is unsupported.
        return {
            i: {
                "line_measurement": "estimated",
                "line_measurement_reason": "Diagnostic PDF extraction failed; natural-width estimate retained.",
            }
            for i in measurements
        }
    finally:
        doc.close()
    return result
