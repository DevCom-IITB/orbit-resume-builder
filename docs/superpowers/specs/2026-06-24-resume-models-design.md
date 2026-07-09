# Resume Builder — Data Model Design Spec

**Date:** 2026-06-24  
**Status:** Awaiting approval before implementation

---

## 1. Overview

The resume builder generates PDF resumes by taking a user's free-form input, passing it through an LLM to produce structured JSON, then converting that JSON into LaTeX via section-specific converters, and finally compiling the LaTeX to a PDF using pdflatex.

The system needs to be **future-proof** in three ways:

1. **New templates** — different combinations of sections, constraints, aesthetics (IIT Bombay, External, Consult, Tech, etc.)
2. **New section types** — sections that only exist in certain templates (e.g. case studies in consult)
3. **New visual aesthetics** — same content JSON rendered into completely different LaTeX styling

---

## 2. Three-Layer Architecture

The core architectural principle is that **content, structure, and presentation are fully independent**:

```
Layer 1 — CONTENT        What the resume says.
                         Lives in: SectionEntry.content (JSON per entry)

Layer 2 — STRUCTURE      Which sections exist, what constraints apply.
                         Lives in: ResumeTemplate + TemplateSectionType

Layer 3 — PRESENTATION   How content becomes LaTeX.
                         Lives in: VisualTheme (converter set + preamble)
```

Because these layers are independent, the same content JSON can be run through a different visual theme at any time to produce a completely different-looking PDF — with no LLM call needed.

---

## 3. Models

### 3.1 `SectionTypeDefinition`

**What it is:** The global registry of every section type that exists in the system. A section type is a named kind of content — "professional experience", "key projects", "header", etc.

Every section type has:
- A key that the LLM, converters, and frontend all use (eliminating translation mismatches)
- The LLM instructions and JSON schema for generating content
- Whether users can have multiple entries or just one

```python
class SectionTypeDefinition(models.Model):
    key = CharField(max_length=64, unique=True)
    # The canonical identifier used everywhere: in converters, LLM prompts, and the DB.
    # Examples: "professional_experience", "key_projects", "header", "case_studies"
    # This replaces the old Section.section_type choices field.

    display_name = CharField(max_length=128)
    # Human-readable name shown in the UI.
    # Example: "Professional Experience", "Key Projects", "Header"

    llm_prompt_instructions = TextField()
    # The section-specific instructions appended to the base system prompt when
    # calling the LLM to generate content for this section type.
    # Currently lives in resume_renderer/services/prompts.py — moves here.

    json_schema = JSONField()
    # The exact JSON schema the LLM must conform to for this section type.
    # Currently lives in resume_renderer/JSONSchema/jsonschema.py — moves here.
    # Used to validate LLM output before storing it.

    entry_hint_text = TextField(blank=True, default="")
    # Placeholder/hint text shown inside the raw input textarea in the UI.
    # Example for experience: "Describe your role, company, and what you worked on."

    allow_multiple_entries = BooleanField(default=True)
    # True: users can add multiple SectionEntry rows under this section type.
    #       The converter receives the list [entry.content, ...] assembled from all entries.
    #       LLM is called once per entry.
    #       Used for: experience, key_projects, education, por,
    #                 technical_skills, courses, scholastic_achievements
    #
    # False: this section has exactly one SectionEntry.
    #        The converter receives entry.content directly (a dict).
    #        LLM is called once for the whole section.
    #        Used for: header (content = {"name": ..., "edu": ..., "contact": {...}})

    default_converter_key = CharField(max_length=64, default="default_projects")
    # Key into the converter registry (code) for this section type.
    # Points to a Python function that converts content JSON → LaTeX string.
    # "default_projects" is used as a fallback for user-added custom sections.
    # For core sections, this is the specific converter (e.g. "convert_experience").
```

**Why `allow_multiple_entries` instead of `is_singleton`:**
`is_singleton` is ambiguous. `allow_multiple_entries` cleanly expresses the user-facing behaviour: can the user add a second entry to this section or not? Only `header` is `False` — every other section type supports multiple entries.

---

### 3.2 `ResumeTemplate`

**What it is:** A named resume configuration. Examples: "IIT Bombay (General)", "IIT Bombay (Consult)", "External (Standard)".

A template defines:
- Which **family** it belongs to (iitb, external — determines visual theme options available)
- Which **domain** it's for (general, tech, consult — determines section set and constraints)
- Which section types are available to users of this template
- Hard constraints like max pages

```python
class ResumeTemplate(models.Model):
    key = CharField(max_length=64, unique=True)
    # Canonical identifier. Examples: "iitb-general", "iitb-consult", "external-standard"

    display_name = CharField(max_length=128)
    # Shown in the "Create Resume" UI. Example: "IIT Bombay — General"

    family = CharField(max_length=32)
    # Groups templates by institution/context. Examples: "iitb", "external"
    # Used to determine which visual themes are compatible.

    domain = CharField(max_length=32)
    # The career domain this template is optimised for.
    # Examples: "general", "tech", "consult"
    # "consult" implies single-page, different section set.

    max_pages = IntegerField(null=True, blank=True)
    # Hard upper limit on the number of pages a resume of this template can have.
    # null = no limit. 1 = consult resumes (always single page).
    # Enforced at PDF generation time.

    template_config = JSONField(default=dict)
    # Template-specific configuration options that users can override at resume creation.
    # This is how IITB-specific concepts like "header style" are captured without
    # polluting the Resume model with template-specific fields.
    #
    # Example for iitb-general:
    # {
    #   "header_style_options": ["short", "long"],
    #   "header_style_default": "short"
    # }
    # Example for external-standard: {}
    #
    # The Resume.config_override field stores the user's chosen value.

    available_themes = ManyToManyField(VisualTheme, related_name="templates", blank=True)
    # The visual themes a user can choose from when creating a resume with this template.
    # Filtered in the UI: when the user picks "IIT Bombay", only IITB-compatible
    # themes appear. When they pick "External", only external themes appear.
    # Enforced at the serializer level (Resume.visual_theme must be in
    # resume.template.available_themes).

    is_active = BooleanField(default=True)
    # Soft-delete / toggle. Inactive templates don't appear in the UI but
    # existing resumes using them continue to work.
```

---

### 3.3 `TemplateSectionType`

**What it is:** The **join table** between `ResumeTemplate` and `SectionTypeDefinition`. It answers the question: "For template X, which section types exist, which are on by default, and in what order?"

Think of it as the template's "section manifest". When a resume is created with a given template, the system reads this table to know which sections to create automatically.

```python
class TemplateSectionType(models.Model):
    template = ForeignKey(ResumeTemplate, on_delete=CASCADE, related_name="section_manifest")
    # The template this row belongs to.

    section_type = ForeignKey(SectionTypeDefinition, on_delete=PROTECT, related_name="template_usages")
    # The section type being configured for this template.

    is_default = BooleanField(default=True)
    # If True, this section is automatically added to a new resume when the user
    # creates a resume with this template.
    # If False, the section exists in the pool (user can add it), but isn't added by default.
    # Example: "extracurriculars" might be in the pool but not default.

    is_required = BooleanField(default=False)
    # If True, the user cannot remove this section from their resume.
    # Example: "education" is required in all IITB templates.

    default_order = IntegerField(default=0)
    # The default position of this section in a new resume.
    # 0 = first. User can reorder sections after creation.

    class Meta:
        unique_together = [("template", "section_type")]
        ordering = ["default_order"]
```

**How ResumeTemplate and TemplateSectionType work together (example):**

```
ResumeTemplate: "iitb-consult"
  TemplateSectionType rows:
    order=0  section_type="header"                  is_default=True  is_required=True
    order=1  section_type="education"               is_default=True  is_required=True
    order=2  section_type="scholastic_achievements" is_default=True  is_required=False
    order=3  section_type="case_studies"            is_default=True  is_required=False
    order=4  section_type="key_projects"            is_default=True  is_required=False
    order=5  section_type="positions_of_resp..."    is_default=True  is_required=False
    order=6  section_type="technical_skills"        is_default=False is_required=False
```

"case_studies" appears here but NOT in "iitb-general" — that's how template-specific sections work. No special case code. Just presence or absence in this table.

---

### 3.4 `VisualTheme`

**What it is:** A named visual aesthetic — the LaTeX preamble and the set of converters that transform section content JSON into styled LaTeX.

Two resumes can share the same content JSON but use different VisualThemes to produce PDFs that look completely different (different fonts, spacing, table layouts, etc.).

```python
class VisualTheme(models.Model):
    key = CharField(max_length=64, unique=True)
    # Canonical identifier. Examples: "iitb-classic", "iitb-minimal", "external-modern"

    display_name = CharField(max_length=128)
    # Shown in the UI when the user picks an aesthetic.
    # Example: "Classic (IIT Bombay)", "Modern (External)"

    compatible_families = JSONField(default=list)
    # List of template families this theme is compatible with.
    # Example: ["iitb"] — only shown for IITB templates.
    # Example: ["external"] — only shown for external templates.
    # Example: ["iitb", "external"] — shown for both.
    # Used to filter theme options in the "Create Resume" UI.

    converter_set_key = CharField(max_length=64)
    # Maps to a Python dictionary in the converter registry (code).
    # The registry maps section_type keys to converter functions.
    # Example: CONVERTER_SETS["iitb-classic"] = {
    #   "header": convert_header_iitb,
    #   "experience": convert_experience_iitb_classic,
    #   ...
    # }
    # Different themes can share converters or have their own.

    latex_preamble = TextField()
    # The full LaTeX document preamble (everything before \begin{document}).
    # Stored in DB so the admin can edit it from the UI without a code deployment.
    # Includes: documentclass, usepackage, geometry, font settings, custom commands.
```

---

### 3.5 `Resume`

**What it is:** A single resume document belonging to a user. Ties together a template (structure), a visual theme (presentation), and the user's content.

```python
class Resume(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Globally unique identifier. Used in all API URLs.

    owner = ForeignKey(User, on_delete=CASCADE, related_name="resumes")
    # The user this resume belongs to.

    title = CharField(max_length=255)
    # User-defined name for this resume.
    # Example: "IITB Placements 2026", "Google Internship"

    template = ForeignKey(ResumeTemplate, on_delete=PROTECT, related_name="resumes")
    # The template this resume uses.
    # Determines: available sections, max pages, config options.
    # Cannot be changed after resume creation (would invalidate section structure).

    visual_theme = ForeignKey(VisualTheme, on_delete=PROTECT, related_name="resumes")
    # The visual aesthetic in use.
    # CAN be changed after creation — the content JSON stays the same,
    # only the converters and preamble change on the next render.

    pages = IntegerField(default=1)
    # How many pages this resume should target: 1 or 2.
    # Constrained by template.max_pages (e.g. consult = always 1).

    config_override = JSONField(default=dict)
    # User's choices for template-specific configuration options.
    # Validated against template.template_config at the serializer level.
    #
    # Example for iitb-general: {"header_style": "short"}
    # Example for external:     {}
    #
    # This replaces the old header_type and resume_type fields with a
    # flexible, template-aware key-value store.

    is_pinned = BooleanField(default=False)
    # Pinned resumes appear first in the resume list.

    cached_latex = TextField(null=True, blank=True)
    # The last fully assembled LaTeX document for this resume.
    # Used to avoid re-assembling on every PDF render if nothing has changed.
    # Set to null when any SectionEntry content changes or the visual theme changes.

    latex_cache_valid = BooleanField(default=False)
    # True if cached_latex reflects the current state of all entries.
    # False means cached_latex is stale and must be rebuilt before compiling.

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

---

### 3.6 `Section`

**What it is:** One section within a resume. A resume has multiple sections (education, experience, etc.). This is the container — the actual content lives in `SectionEntry` rows under it.

```python
class Section(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    resume = ForeignKey(Resume, on_delete=CASCADE, related_name="sections")
    # The resume this section belongs to.

    section_type = ForeignKey(SectionTypeDefinition, on_delete=PROTECT, related_name="instances")
    # What kind of section this is. The FK replaces the old CharField choices.
    # section_type.key is what the converter registry and LLM router use.

    order = IntegerField(default=0)
    # The user-defined display order of this section within the resume.
    # 0 = rendered first (top of resume).

    is_visible = BooleanField(default=True)
    # Hides the section from the PDF without deleting it.
    # The user can toggle sections on/off without losing their content.

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("resume", "section_type")]
        # A resume cannot have two sections of the same type.
        ordering = ["order"]
```

---

### 3.7 `SectionEntry`

**What it is:** One entry within a section. This is where content actually lives. For multi-entry sections (experience, projects), each row is one real-world item (one job, one project). For single-entry sections (header, skills), there is exactly one row per section.

This is the unit of LLM generation — each entry can be independently generated and regenerated.

```python
class SectionEntry(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    section = ForeignKey(Section, on_delete=CASCADE, related_name="entries")
    # The section this entry belongs to.

    order = IntegerField(default=0)
    # Display order of this entry within its section.
    # Example: two experience entries ordered by recency.

    raw_input = TextField(blank=True, default="")
    # The free-form text the user typed to describe this entry.
    # Always preserved — never overwritten by LLM output.
    # Example for experience: "Interned at Google on Search team, built a feature
    #   that improved engagement, worked with 5 engineers using Agile"
    #
    # When regenerating, this is included in the LLM prompt as the source material.
    # The LLM also receives `content` (current state) as context.

    content = JSONField(null=True, blank=True)
    # The current structured content for this entry.
    # Initially null (before any LLM generation).
    # After generation: contains the LLM's structured JSON output.
    # After user edits: contains the user's modified version.
    # This is the single source of truth — LLM output and user edits both land here.
    #
    # Shape per section type (one entry = one real-world item):
    #
    # professional_experience: {"title": "...", "organization": "...", "timeline": "...", "location": "...", "bullets": [...]}
    # key_projects:            {"title": "...", "organization": "...", "summary": "...", "timeline": "...", "bullets": [...]}
    # positions_of_resp:       {"role": "...", "organization": "...", "duration": "...", "summary": "...", "bullets": [...]}
    # education:               {"degree": "...", "institution": "...", "cpi": "...", "year": "..."}
    # technical_skills:        {"category": "Programming", "skills": ["Python", "C++"]}
    # courses:                 {"category": "Computer Science", "courses": ["DSA", "Operating Systems"]}
    # scholastic_achievements: "Secured AIR 3809 in JEE Advanced 2024"   ← a plain string
    #
    # allow_multiple_entries=False (header only):
    #   content = {"name": "...", "edu": "...", "contact": {"email": "...", "phone": "...", "linkedin": "...", "github": "..."}}
    #
    # The converter always receives the assembled list:
    #   [entry.content for entry in section.entries.order_by("order")]
    # For header (allow_multiple_entries=False): converter receives entry.content directly.

    last_sent_prompt = TextField(blank=True, default="")
    # The full prompt string sent to the LLM on the most recent generation call.
    # Stored for debugging, auditing, and understanding what context the LLM had.
    # Updated every time a generation is triggered for this entry.
    # Useful when investigating why the LLM produced a certain output.

    generation_status = CharField(
        max_length=16,
        choices=[
            ("pending",    "Pending"),    # not yet generated
            ("generating", "Generating"), # LLM call in flight
            ("done",       "Done"),       # content is populated and valid
            ("failed",     "Failed"),     # last generation attempt failed
        ],
        default="pending"
    )
    # Tracks the LLM generation lifecycle for this specific entry.
    # Used by the frontend to show loading states per entry.

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
```

---

### 3.8 `Version`

**What it is:** A server-side snapshot of a resume's complete JSON state at a point in time. Used for viewing and restoring prior states.

Client-side undo/redo (within a browser session) is handled by the frontend (Redux/Zustand history stack) and is NOT stored in the DB. `Version` records are written only on meaningful save events (e.g. user explicitly saves, or after a generation completes).

```python
class Version(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    resume = ForeignKey(Resume, on_delete=CASCADE, related_name="versions")
    # The resume this version belongs to.

    snapshot = JSONField(default=dict)
    # Complete assembled JSON of the resume at save time.
    # Format: { "sections": { "professional_experience": [...], "header": {...}, ... } }
    # This is the same JSON that gets passed to the LaTeX assembler.
    # Sufficient to fully reconstruct the resume's content at this point.

    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    # Who triggered this version snapshot.

    created_at = DateTimeField(auto_now_add=True)
    # When this version was saved.
```

---

## 4. Data Flow

### 4.1 LLM Generation Pipeline (per entry)

```
1. User types raw_input for a SectionEntry
        ↓
2. Frontend sends: POST /api/generate/
   { resume_id, section_id, entry_id }
        ↓
3. Backend sets entry.generation_status = "generating"
        ↓
4. Build LLM prompt:
   - BASE_SYSTEM_PROMPT (from prompts.py)
   - section_type.llm_prompt_instructions (from SectionTypeDefinition)
   - section_type.json_schema (from SectionTypeDefinition)
   - entry.raw_input
   - entry.content (current state, if re-generating — gives LLM context of prior output)
        ↓
5. Store full prompt in entry.last_sent_prompt
        ↓
6. Call LLM → returns raw JSON string
        ↓
7. Validate against section_type.json_schema
        ↓
8. Store in entry.content
   Set entry.generation_status = "done"
   Set resume.latex_cache_valid = False  ← invalidate cached LaTeX
        ↓
9. Trigger PDF re-render (see 4.2)
```

---

### 4.2 LaTeX / PDF Rendering Pipeline

```
1. PDF render triggered (save event or user clicks regenerate)
        ↓
2. Check resume.latex_cache_valid
   - True  → skip to step 5 (use cached_latex)
   - False → continue to step 3
        ↓
3. Assemble full resume JSON:
   For each Section (ordered by section.order, is_visible=True):
     If section_type.allow_multiple_entries = True:   ← all section types except header
       section_data = [entry.content for entry in section.entries.order_by("order")
                       if entry.generation_status == "done"]
     Else:                                            ← header only
       section_data = section.entries.first().content
        ↓
4. Convert each section to LaTeX:
   converter_set = CONVERTER_REGISTRY[resume.visual_theme.converter_set_key]
   converter_fn  = converter_set[section_type.key]
   section_latex = converter_fn(section_data)

   Assemble full document:
   full_latex = visual_theme.latex_preamble
              + "\\begin{document}"
              + header_latex (if header section exists)
              + section_latex for each section
              + "\\end{document}"

   Store in resume.cached_latex
   Set resume.latex_cache_valid = True
        ↓
5. Compile: pdflatex(resume.cached_latex) → PDF bytes
        ↓
6. Stream PDF back to client
```

The cache means pdflatex only runs when something actually changed. Switching visual themes → `latex_cache_valid = False` → LaTeX rebuilt with new preamble + new converters → compiled → new PDF. The content JSON never changes; only the presentation does.

**Important edge case — IIT Bombay header:**
In the IITB visual theme, the "header" converter does NOT render the content JSON. It outputs only `\vspace{Xcm}` (where X depends on `resume.config_override["header_style"]`). The placement portal fills in the actual header. The `header` SectionEntry still exists and stores the user's name/contact details — but the IITB converter ignores it. This is correct behaviour: the same header content can be rendered fully if the user ever switches to an external theme.

The IITB header converter receives `(content, config_override)` instead of just `(content)`. All converters accept an optional `config_override` dict; most ignore it.

---

## 5. How to Define a Template

Adding a new template requires three things:

1. **Register section types** — ensure all section types used by the template exist in `SectionTypeDefinition`
2. **Register converters** — add a converter function (or reuse existing) in the converter registry
3. **Seed DB records** — create `ResumeTemplate`, `VisualTheme`, and `TemplateSectionType` rows

No model migrations are needed unless you're adding a completely new section type. Section types share the same model — you just add a new row.

---

## 6. Seed Data: Current Templates

These are the records to seed for the two templates in the system right now.

---

### `SectionTypeDefinition` seed

| key | display_name | allow_multiple_entries | default_converter_key |
|---|---|---|---|
| `header` | Header | `False` | `convert_header` |
| `education` | Education | `True` | `convert_education` |
| `scholastic_achievements` | Scholastic Achievements | `True` | `convert_scholastic_achievements` |
| `courses` | Relevant Courses Undertaken | `True` | `convert_courses` |
| `professional_experience` | Professional Experience | `True` | `convert_experience` |
| `key_projects` | Key Projects | `True` | `convert_key_project` |
| `positions_of_responsibility` | Positions of Responsibility | `True` | `convert_pors` |
| `technical_skills` | Technical Skills | `True` | `convert_technical_skills` |

*(llm_prompt_instructions and json_schema for each row come from the existing prompts.py and jsonschema.py — migrated verbatim)*

---

### `VisualTheme` seed

```python
VisualTheme(
    key="iitb-classic",
    display_name="Classic (IIT Bombay)",
    compatible_families=["iitb"],
    converter_set_key="iitb-classic",   # maps to existing converters in code
    latex_preamble="...",               # existing LaTeX preamble from the IITB template
)

VisualTheme(
    key="external-standard",
    display_name="Standard (External)",
    compatible_families=["external"],
    converter_set_key="external-standard",
    latex_preamble="...",               # external template preamble
)
```

---

### `ResumeTemplate` seed

```python
# Template 1: IIT Bombay General
ResumeTemplate(
    key="iitb-general",
    display_name="IIT Bombay",
    family="iitb",
    domain="general",
    max_pages=None,                      # 1 or 2 pages allowed
    template_config={
        "header_style_options": ["short", "long"],
        "header_style_default": "short"
    },
    is_active=True,
)

# Template 2: External
ResumeTemplate(
    key="external-standard",
    display_name="External",
    family="external",
    domain="general",
    max_pages=None,
    template_config={},
    is_active=True,
)
```

---

### `TemplateSectionType` seed

**Template: `iitb-general`**

| order | section_type_key | is_default | is_required |
|---|---|---|---|
| 0 | `header` | True | True |
| 1 | `education` | True | True |
| 2 | `scholastic_achievements` | True | False |
| 3 | `courses` | True | False |
| 4 | `professional_experience` | True | False |
| 5 | `key_projects` | True | False |
| 6 | `positions_of_responsibility` | True | False |
| 7 | `technical_skills` | True | False |

**Template: `external-standard`**

| order | section_type_key | is_default | is_required |
|---|---|---|---|
| 0 | `header` | True | True |
| 1 | `education` | True | True |
| 2 | `professional_experience` | True | False |
| 3 | `key_projects` | True | False |
| 4 | `technical_skills` | True | False |
| 5 | `positions_of_responsibility` | False | False |
| 6 | `courses` | False | False |
| 7 | `scholastic_achievements` | False | False |

*Note: `positions_of_responsibility`, `courses`, and `scholastic_achievements` are `is_default=False` for external — they're in the pool but not added automatically. User can add them if needed.*

---

### Adding `iitb-consult` in the future (example)

1. Add a `case_studies` row to `SectionTypeDefinition` with its own prompt + schema
2. Write `convert_case_studies()` and register it in the converter registry
3. Create the `ResumeTemplate` record:

```python
ResumeTemplate(
    key="iitb-consult",
    display_name="IIT Bombay — Consulting",
    family="iitb",
    domain="consult",
    max_pages=1,           # hard constraint: consult = 1 page only
    template_config={
        "header_style_options": ["short", "long"],
        "header_style_default": "short"
    },
)
```

4. Seed its `TemplateSectionType` rows (same as `iitb-general` but swap `key_projects` for `case_studies`)

No migration. No code change outside of the new converter function and the seed script.

---

## 7. What Changes From Current Code

| Current | New |
|---|---|
| `Section.section_type = CharField(choices=[...])` | `Section.section_type = FK(SectionTypeDefinition)` |
| `Section.content = JSONField(list)` — stores all entries | `SectionEntry.content` — one row per entry |
| Section types defined in Python choices | `SectionTypeDefinition` rows in DB |
| LLM prompts in `prompts.py` | Migrated to `SectionTypeDefinition.llm_prompt_instructions` |
| JSON schemas in `jsonschema.py` | Migrated to `SectionTypeDefinition.json_schema` |
| `Resume.header_type + resume_type` CharField | `Resume.template FK` + `Resume.config_override JSONField` |
| `Resume.meta` JSONField | Removed — frontend manages its own UI state |
| No template concept | `ResumeTemplate` + `TemplateSectionType` |
| No visual theme concept | `VisualTheme` |
| Raw user input not persisted | `SectionEntry.raw_input` |
| No per-entry LLM status | `SectionEntry.generation_status` |
| No prompt audit trail | `SectionEntry.last_sent_prompt` |
| `scholastic_achievements`, `technical_skills`, `courses` stored as single blob | Each entry is one row (`allow_multiple_entries=True`) |

---

## 8. What Is Not Changing

- All converter functions in `resume_renderer/schemas/converters/` — they are registered, not rewritten
- The `LLMClient` — same interface, just called once per entry
- The `Version` model — same structure, snapshot format updated
- The `build_resume_prompt` function — updated to read from DB instead of hardcoded dicts
- pdflatex compilation — server-side, unchanged
