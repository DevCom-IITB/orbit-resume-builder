from decimal import Decimal

HEADER_GAP_PT = 3  # after the header block
ENTRY_GAP_PT = -4  # after a non-last entry's bullet list (reference uses -4pt; -5pt once)
LIST_SECTION_END_GAP_PT = -18  # after the last entry of experience/projects/PoR
SCHOLASTIC_END_GAP_PT = -20
TABLE_SECTION_END_GAP_PT = -12  # after the skills/courses tables

# Scaling factor in pt per 1.0 line_spacing delta (40 pt per 1.0 delta = 2 pt per 0.05 toggle step)
SPACING_SCALE_PT = 40


def vspace(pt: int) -> str:
    """Format a LaTeX vspace command. If pt is 0, return empty string to avoid stray vspace{0pt}."""
    if pt == 0:
        return ""
    return f"\\vspace{{{pt}pt}}"


def compute_gap(base_pt: int, config_override: dict | None = None) -> str:
    """
    Compute \\vspace{...} gap for base_pt, scaled by line_spacing from config_override.
    When line_spacing is default 1.00 (or config_override is absent), returns vspace(base_pt).
    When line_spacing changes (e.g. 1.05, 1.10), scales the gap proportionally so the spacing
    between blocks expands/contracts with line spacing.
    """
    if not config_override or not isinstance(config_override, dict):
        return vspace(base_pt)

    line_spacing = config_override.get("line_spacing")
    if line_spacing is None:
        style = config_override.get("style")
        if isinstance(style, dict):
            line_spacing = style.get("line_spacing")

    if line_spacing is None:
        return vspace(base_pt)

    try:
        line_d = Decimal(str(line_spacing))
    except Exception:
        return vspace(base_pt)

    delta = line_d - Decimal("1.00")
    if delta == Decimal("0"):
        return vspace(base_pt)

    extra_pt = int(round(float(delta) * SPACING_SCALE_PT))
    return vspace(base_pt + extra_pt)
