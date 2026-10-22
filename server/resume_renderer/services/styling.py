"""
Style resolution and application for the LaTeX render pipeline.

Public API
----------
FONTS                   : dict mapping key -> LaTeX setup block
DEFAULT_FONT            : "lmodern"
DEFAULT_ACCENT          : "#4B41C8"  (= RGB 75,65,200 — byte-identical default)
get_style_options(template) -> dict
resolve_style(resume)       -> {"font": key, "accent": "#RRGGBB"}
validate_style_patch(patch, template) -> cleaned dict | raises ValidationError
apply_style(resume, patch)  -> bool
"""

from decimal import Decimal, InvalidOperation
import re

from django.db import transaction
from rest_framework import serializers as drf_serializers

# ---------------------------------------------------------------------------
# Font whitelist — values are LaTeX blocks emitted verbatim into the preamble.
# Only fonts confirmed present in texlive-fonts-extra / texlive-fonts-recommended.
# T1 fontenc is included ONLY in non-lmodern blocks so the lmodern default
# produces byte-identical output to the pre-change pipeline.
# ---------------------------------------------------------------------------
FONTS: dict[str, str] = {
    "lmodern": r"\usepackage{lmodern}",
    "times": "\\usepackage[T1]{fontenc}\n\\usepackage{tgtermes}",
    "palatino": "\\usepackage[T1]{fontenc}\n\\usepackage{tgpagella}",
    "charter": "\\usepackage[T1]{fontenc}\n\\usepackage{charter}",
    "helvetica": (
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage{tgheros}\n"
        "\\renewcommand{\\familydefault}{\\sfdefault}"
    ),
    "sourcesans": r"\usepackage[default]{sourcesanspro}",
}

FONT_LABELS: dict[str, str] = {
    "lmodern": "Latin Modern",
    "times": "Times (TeX Gyre Termes)",
    "palatino": "Palatino (TeX Gyre Pagella)",
    "helvetica": "Helvetica (TeX Gyre Heros)",
    "sourcesans": "Source Sans Pro",
    "charter": "Charter",
}

DEFAULT_FONT = "lmodern"
DEFAULT_ACCENT = "#4B41C8"  # RGB(75, 65, 200) — preserves original output

DEFAULT_SPACING_OPTIONS = ["0.90", "0.95", "1.00", "1.05", "1.10", "1.15", "1.20"]
DEFAULT_LINE_SPACING = "1.00"
DEFAULT_WORD_SPACING = "1.00"

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def parse_spacing(value) -> Decimal:
    """
    Parse and validate a spacing value into a Decimal quantized to 0.01.
    Accepts int, float, or numeric string.
    Rejects booleans, None, non-numeric strings, NaN, Infinity, and non-positive numbers.
    Raises drf_serializers.ValidationError on invalid values.
    """
    if isinstance(value, bool):
        raise drf_serializers.ValidationError("Spacing value cannot be a boolean.")
    if value is None:
        raise drf_serializers.ValidationError("Spacing value cannot be null.")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise drf_serializers.ValidationError(f"Invalid spacing value '{value}'.")
    if not d.is_finite() or d <= Decimal("0"):
        raise drf_serializers.ValidationError(f"Spacing value '{value}' must be a positive finite number.")
    return d.quantize(Decimal("0.01"))


def build_spacing_setup(line, word) -> str:
    """
    Build the LaTeX preamble spacing setup block.
    Returns empty string "" when both line and word are 1.00 (preserving byte-identical output).
    When non-empty, lines are joined with '\\n' and end with a trailing '\\n'.
    """
    try:
        line_d = Decimal(str(line)).quantize(Decimal("0.01"))
    except Exception:
        line_d = Decimal("1.00")
    try:
        word_d = Decimal(str(word)).quantize(Decimal("0.01"))
    except Exception:
        word_d = Decimal("1.00")

    if line_d == Decimal("1.00") and word_d == Decimal("1.00"):
        return ""

    blocks = []
    if line_d != Decimal("1.00"):
        line_str = f"{line_d:.2f}"
        blocks.append(
            f"\\linespread{{{line_str}}}\n"
            "\\makeatletter\n"
            "\\ifdefined\\localsize\n"
            "\\renewenvironment{localsize}[1]{\\begingroup\\fontsize{#1}{\\f@baselineskip}\\selectfont}{\\endgroup}\n"
            "\\fi\n"
            "\\makeatother"
        )

    if word_d != Decimal("1.00"):
        word_str = f"{word_d:.2f}"
        blocks.append(
            "\\usepackage{etoolbox}\n"
            f"\\apptocmd{{\\selectfont}}{{\\spaceskip={word_str}\\fontdimen2\\font plus {word_str}\\fontdimen3\\font minus {word_str}\\fontdimen4\\font\\relax}}{{}}{{\\PackageWarning{{resume}}{{spacing patch failed}}}}"
        )

    return "\n".join(blocks) + "\n"


# ---------------------------------------------------------------------------
# WCAG contrast helpers
# ---------------------------------------------------------------------------

def _relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance of a #RRGGBB colour."""
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (1, 3, 5))

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio_vs_white(hex_color: str) -> float:
    """WCAG contrast ratio of hex_color against white (#FFFFFF)."""
    L_white = 1.0
    L2 = _relative_luminance(hex_color)
    lighter = max(L_white, L2)
    darker = min(L_white, L2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# Internal validators
# ---------------------------------------------------------------------------

def _validate_hex(hex_color: str) -> str:
    """Validate and normalise to uppercase #RRGGBB. Raises ValidationError."""
    if not isinstance(hex_color, str) or not _HEX_RE.match(hex_color):
        raise drf_serializers.ValidationError(
            {"accent": f"Invalid hex colour '{hex_color}'. Must match #RRGGBB (e.g. #4B41C8)."}
        )
    return hex_color.upper()


def _validate_contrast(hex_color: str) -> None:
    """Reject colours with WCAG contrast ratio < 3:1 against white."""
    ratio = _contrast_ratio_vs_white(hex_color)
    if ratio < 3.0:
        raise drf_serializers.ValidationError(
            {
                "accent": (
                    f"Colour {hex_color} has a WCAG contrast ratio of {ratio:.2f}:1 against "
                    "white, which is below the required minimum of 3:1. "
                    "Choose a darker colour."
                )
            }
        )


def validate_template_style_config(template_config: dict) -> None:
    """
    Seed-time validation helper for template style configurations.
    Raises ValueError on any violation:
    - font_options: list of 2 to 3 fonts, all in FONTS
    - font_default: must be in font_options
    - accent_options: non-empty list of valid #RRGGBB hex colours
    - accent_default: must be in accent_options
    - line_spacing_options: non-empty list of 1 to 9 valid decimals
    - line_spacing_default: must be in line_spacing_options
    - word_spacing_options: non-empty list of 1 to 9 valid decimals
    - word_spacing_default: must be in word_spacing_options
    """
    if not isinstance(template_config, dict):
        raise ValueError("template_config must be a dictionary.")

    font_options = template_config.get("font_options")
    if not isinstance(font_options, list):
        raise ValueError("template_config must define a 'font_options' list.")
    if len(font_options) < 2 or len(font_options) > 3:
        raise ValueError(
            f"font_options must have between 2 and 3 fonts, got {len(font_options)}: {font_options}"
        )
    for k in font_options:
        if k not in FONTS:
            raise ValueError(f"Unknown font '{k}' in font_options. Allowed keys: {list(FONTS.keys())}")

    font_default = template_config.get("font_default")
    if font_default not in font_options:
        raise ValueError(
            f"font_default '{font_default}' must be present in font_options {font_options}."
        )

    accent_options = template_config.get("accent_options")
    if not isinstance(accent_options, list) or not accent_options:
        raise ValueError("template_config must define a non-empty 'accent_options' list.")
    for hex_code in accent_options:
        if not isinstance(hex_code, str) or not _HEX_RE.match(hex_code):
            raise ValueError(f"Invalid hex code '{hex_code}' in accent_options. Must match #RRGGBB.")

    accent_default = template_config.get("accent_default")
    if accent_default not in accent_options:
        raise ValueError(
            f"accent_default '{accent_default}' must be present in accent_options {accent_options}."
        )

    # Line spacing validation
    line_options = template_config.get("line_spacing_options")
    if line_options is not None:
        if not isinstance(line_options, list) or len(line_options) < 1 or len(line_options) > 9:
            raise ValueError(
                f"line_spacing_options must be a list of 1 to 9 items, got {line_options}"
            )
        for opt in line_options:
            if isinstance(opt, bool):
                raise ValueError(f"Invalid line spacing option '{opt}'.")
            try:
                d = Decimal(str(opt))
                if not d.is_finite() or d <= Decimal("0"):
                    raise ValueError()
            except Exception:
                raise ValueError(f"Invalid line spacing option '{opt}'. Must parse as positive Decimal.")
        line_default = template_config.get("line_spacing_default")
        if line_default not in line_options:
            raise ValueError(
                f"line_spacing_default '{line_default}' must be present in line_spacing_options {line_options}."
            )

    # Word spacing validation
    word_options = template_config.get("word_spacing_options")
    if word_options is not None:
        if not isinstance(word_options, list) or len(word_options) < 1 or len(word_options) > 9:
            raise ValueError(
                f"word_spacing_options must be a list of 1 to 9 items, got {word_options}"
            )
        for opt in word_options:
            if isinstance(opt, bool):
                raise ValueError(f"Invalid word spacing option '{opt}'.")
            try:
                d = Decimal(str(opt))
                if not d.is_finite() or d <= Decimal("0"):
                    raise ValueError()
            except Exception:
                raise ValueError(f"Invalid word spacing option '{opt}'. Must parse as positive Decimal.")
        word_default = template_config.get("word_spacing_default")
        if word_default not in word_options:
            raise ValueError(
                f"word_spacing_default '{word_default}' must be present in word_spacing_options {word_options}."
            )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_style_options(template) -> dict:
    """
    Return available font/accent/spacing options for *template*, falling back to
    module-level defaults when template_config keys are absent or invalid.
    """
    cfg = (template.template_config if template else None) or {}

    raw_font_keys = cfg.get("font_options", list(FONTS.keys()))
    # Sanitise: keep only whitelisted keys (guards against stale DB data)
    font_keys = [k for k in raw_font_keys if k in FONTS] or list(FONTS.keys())

    accents = cfg.get("accent_options", [DEFAULT_ACCENT])

    return {
        "fonts": [{"key": k, "label": FONT_LABELS.get(k, k)} for k in font_keys],
        "accents": accents,
        "font_default": cfg.get("font_default", DEFAULT_FONT),
        "accent_default": cfg.get("accent_default", DEFAULT_ACCENT),
        "line_spacings": cfg.get("line_spacing_options", DEFAULT_SPACING_OPTIONS),
        "line_spacing_default": cfg.get("line_spacing_default", DEFAULT_LINE_SPACING),
        "word_spacings": cfg.get("word_spacing_options", DEFAULT_SPACING_OPTIONS),
        "word_spacing_default": cfg.get("word_spacing_default", DEFAULT_WORD_SPACING),
    }


def resolve_style(resume) -> dict:
    """
    Compute the effective style for *resume* by merging:
        module defaults  <-  template_config defaults  <-  resume.config_override["style"]

    Unknown or invalid stored values are silently replaced with defaults.
    Never raises.
    """
    cfg = (resume.template.template_config if getattr(resume, "template", None) else None) or {}
    font_default = cfg.get("font_default", DEFAULT_FONT)
    accent_default = cfg.get("accent_default", DEFAULT_ACCENT)
    line_spacing_default = cfg.get("line_spacing_default", DEFAULT_LINE_SPACING)
    word_spacing_default = cfg.get("word_spacing_default", DEFAULT_WORD_SPACING)

    if font_default not in FONTS:
        font_default = DEFAULT_FONT
    if not isinstance(accent_default, str) or not _HEX_RE.match(accent_default):
        accent_default = DEFAULT_ACCENT

    # Valid options for this template (falls back to global constants if unconfigured)
    raw_font_options = cfg.get("font_options", list(FONTS.keys()))
    valid_font_options = [k for k in raw_font_options if k in FONTS] or list(FONTS.keys())

    valid_line_options = cfg.get("line_spacing_options", DEFAULT_SPACING_OPTIONS)
    valid_word_options = cfg.get("word_spacing_options", DEFAULT_SPACING_OPTIONS)

    stored = (resume.config_override or {}).get("style", {})

    font = stored.get("font", font_default)
    # Existing resumes whose stored style font is no longer offered fall back to template default
    if not isinstance(font, str) or font not in valid_font_options:
        font = font_default

    accent = stored.get("accent", accent_default)
    if not isinstance(accent, str) or not _HEX_RE.match(accent):
        accent = accent_default

    # Line spacing
    line_spacing = line_spacing_default
    if "line_spacing" in stored:
        try:
            val = stored["line_spacing"]
            if not isinstance(val, bool):
                d = Decimal(str(val)).quantize(Decimal("0.01"))
                s = f"{d:.2f}"
                if s in valid_line_options:
                    line_spacing = s
        except Exception:
            pass

    # Word spacing
    word_spacing = word_spacing_default
    if "word_spacing" in stored:
        try:
            val = stored["word_spacing"]
            if not isinstance(val, bool):
                d = Decimal(str(val)).quantize(Decimal("0.01"))
                s = f"{d:.2f}"
                if s in valid_word_options:
                    word_spacing = s
        except Exception:
            pass

    return {
        "font": font,
        "accent": accent.upper(),
        "line_spacing": line_spacing,
        "word_spacing": word_spacing,
    }


def validate_style_patch(patch: dict, template) -> dict:
    """
    Validate a raw PATCH body dict against *template*'s style options.
    Returns a cleaned dict containing only recognised, valid keys.
    Raises ``drf_serializers.ValidationError`` on any problem.
    """
    if not patch:
        raise drf_serializers.ValidationError(
            {"non_field_errors": "Request body must include at least one of 'font', 'accent', 'line_spacing', or 'word_spacing'."}
        )

    unknown_keys = set(patch.keys()) - {"font", "accent", "line_spacing", "word_spacing"}
    if unknown_keys:
        raise drf_serializers.ValidationError(
            {k: "Unknown field." for k in sorted(unknown_keys)}
        )

    cleaned: dict = {}
    opts = get_style_options(template)
    valid_font_keys = [f["key"] for f in opts["fonts"]]

    if "font" in patch:
        font = patch["font"]
        # Validate against the current template's font_options
        if not isinstance(font, str) or font not in valid_font_keys:
            raise drf_serializers.ValidationError(
                {"font": f"Unknown font '{font}'. Valid options: {valid_font_keys}."}
            )
        cleaned["font"] = font

    if "accent" in patch:
        accent = patch["accent"]
        accent = _validate_hex(accent)   # raises on bad format
        _validate_contrast(accent)       # raises on low contrast
        cleaned["accent"] = accent

    if "line_spacing" in patch:
        d = parse_spacing(patch["line_spacing"])
        str_val = f"{d:.2f}"
        if str_val not in opts["line_spacings"]:
            raise drf_serializers.ValidationError(
                {"line_spacing": f"Invalid line_spacing '{patch['line_spacing']}'. Valid options: {opts['line_spacings']}."}
            )
        cleaned["line_spacing"] = str_val

    if "word_spacing" in patch:
        d = parse_spacing(patch["word_spacing"])
        str_val = f"{d:.2f}"
        if str_val not in opts["word_spacings"]:
            raise drf_serializers.ValidationError(
                {"word_spacing": f"Invalid word_spacing '{patch['word_spacing']}'. Valid options: {opts['word_spacings']}."}
            )
        cleaned["word_spacing"] = str_val

    if not cleaned:
        raise drf_serializers.ValidationError(
            {"non_field_errors": "Provide at least one of 'font', 'accent', 'line_spacing', or 'word_spacing'."}
        )

    return cleaned


def apply_style(resume, patch: dict) -> bool:
    """
    Merge *patch* into ``resume.config_override["style"]`` atomically.

    Uses ``SELECT FOR UPDATE`` to prevent concurrent overwrites on the same row.
    Preserves all other keys inside ``config_override``.

    Returns
    -------
    True  — style changed and saved; ``latex_cache_valid`` set to False.
    False — resolved style unchanged; DB not written.
    """
    from resumes.models import Resume  # local import avoids circular dependency

    with transaction.atomic():
        locked = Resume.objects.select_for_update().get(pk=resume.pk)

        current_style = resolve_style(locked)
        merged = {**current_style, **patch}
        if "accent" in merged:
            merged["accent"] = merged["accent"].upper()

        if merged == current_style:
            return False  # no-op — nothing to write

        new_config = {**(locked.config_override or {}), "style": merged}
        locked.config_override = new_config
        locked.latex_cache_valid = False
        locked.save(update_fields=["config_override", "latex_cache_valid", "updated_at"])

        # Reflect changes on the caller's in-memory instance
        resume.config_override = locked.config_override
        resume.latex_cache_valid = False

    return True
