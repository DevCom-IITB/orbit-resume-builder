# Template-aware bullet fitting

Bullet fitting is an explicit generation/refit operation. Saving JSON, rendering a
PDF, changing style, and switching templates never rewrite saved wording.

## Generation and fitter preferences

The generation base and section instructions retain the wording restored from
commit `908a557`, with unchanged schema passing and no added short word-count
target. Narrative generation now also receives the advisory preprocessing and
bounded editing authority described below. Italic project summary fitting behavior
is unchanged.

- One well-filled line is the preferred bullet outcome. Every wrapping bullet
  enters optimization, including an already full two-line point. The target is
  the selected template/font's actual available width, using the configured
  88–100% fill band.
- The repair prompt explicitly authorizes rewriting the sentence, changing verbs,
  compressing phrases and omitting secondary details. Its aim is a concise bullet
  preserving the core accomplishment and important technical meaning, not every
  input word or implementation detail. Two tailored NLP/campus performance examples
  show safe removal of hype and rewriting/splitting while retaining useful evidence.
- Subjective adjectives (robust, reliable, seamless, etc.) are expendable even when
  supplied by the user or mistakenly marked protected by the same-call fact list.
  Only unmistakable filler is overridden; defining labels and factual qualifiers
  retain their protection. Optional support phrases may be paraphrased without an
  exact substring match. Optional capitalized library names are no longer treated
  as essential merely because they are capitalized.
- Primary metrics, dataset/population counts and truth qualifications (prototype,
  synthetic/local tests, etc.) remain protected. Explicitly ranked, omitted technical
  versions/model identifiers may lose their secondary numbers; new or changed
  numeric values are rejected. Known equivalent abbreviations (e.g. natural language
  processing/NLP, neural networks/NN) and percentage/thousands formatting are allowed.
- Secondary `details` and `dropped` annotations are advisory. Case, punctuation,
  known abbreviations and equivalent numeric formats are normalized. Unmatched
  secondary annotations are ignored with `metadata_notes`, not used as rejection
  gates. Core action paraphrases are not mistaken for deletions, even if the model
  marks their original wording T1 or puts it in dropped.
- Protected phrases contribute defining labels/concepts rather than freezing a
  whole sentence, generic verb or word order. Source-backed named technologies and
  important numeric values remain guarded independently of optional metadata.
  Missing/changed metrics, core-label loss and qualification loss have specific
  rejection reasons, so the retry receives actionable feedback.
- Equivalent forms such as twenty four/24 neighborhoods, eight/8 members, held out/
  held-out, mean absolute error/MAE and degrees Celsius/°C are supported. This does
  not permit changing their values, evaluation method or units. JSON response types
  remain validated; advisory matching does not excuse malformed response structure.
- Semantic equivalence still depends on the model's core-meaning instructions,
  not an independent verifier. Already acceptable bullets incur no new cleanup calls.
- When a wrapping point has two distinct actions or a build/result pair, it may
  become two separately measured one-line bullets. Facts and metrics must stay tied
  to the correct action and must not be duplicated. Already short, single-purpose
  bullets cannot be split. `BULLET_FIT_MAX_BULLETS_PER_ITEM=0` leaves the total
  uncapped; a positive value is enforced across simultaneous proposals and retries.
- Selection prefers full one-line results (including two separate full one-line
  bullets), then a nearly full two-line fallback, then unresolved sparse lines.
  Ties retain earlier wording. Original or improved two-line wording may be retained
  after the bounded one-line attempts, but a short spillover is not marked fitted.
- Diagnostic jobs compile a PDF with invisible per-bullet URI markers. pdfTeX
  creates rectangles for each rendered line, including across page breaks. PyMuPDF
  maps text within these regions by marker ID, not by matching repeated strings.
  Normal resume PDFs contain none of these markers.
- Measurements retain natural width, available width and ratio, and add actual
  `line_widths_pt`, `line_fill_ratios`, `line_pages`, actual line count and box
  overflow. PDF coordinates are converted to TeX points. A half-point ink-overhang
  tolerance applies to fit decisions; raw widths and overflow remain available.
- Both actual lines must reach the configured fill range for a two-line fallback.
  A short second-line spillover remains unresolved even when the natural total
  width suggests two full lines. Optimization requests include these measurements
  and a layout status, without increasing the number of model calls.
- Missing, overlapping, rotated or unextractable marker regions are explicitly
  labeled `line_measurement=estimated` with a reason. Only these cases retain the
  conservative natural-width estimate. Measurement cache version v3 prevents
  older estimates being reused as rendered measurements.
- Compilation warnings are parsed into bounded structured diagnostics with explicit
  document scope; they are not falsely attributed to individual bullets. Per-bullet
  overflow uses its own rendered text extents. Raw logs are not persisted.
- Current template/font/spacing measurements, Docker isolation and caches remain.
  Every locally valid candidate is measured again; local fact checks and model
  fact lists are not independent semantic verification.
- By default calls remain bounded to one request plus at most one retry per frozen batch of
  up to three mixed bullet/summary items. Resolved one-liners leave the retry.
  Summaries still shorten only when wrapping, never split and never expand merely
  to fill space. A full two-line bullet fallback can be reported as a successful
  layout after optimization; operational model/measurement errors still surface.
  `ITERATION_CALLS` changes the maximum retries independently of Lite preprocessing.
- Manual JSON edits, ordinary rendering, style changes and template switches do not
  invoke fitting. Explicit refit preview/select/apply and manual-content protection
  remain intact. Existing saved content changes only on generation or accepted refit.

## Deterministic editing guidance

Before each existing optimization invocation, local Python helpers in
`services/fitter_guidance.py` compute per-candidate point budgets and source-positioned
filler/abbreviation suggestions. Supported abbreviation expansion references the
original item. Guidance includes the existing normalized numeric inventory and
selected qualification spans, retaining original/current text as context.
It is recomputed from the best current candidate and measurements on retry.

The engineered fitter prompt separates role, context, task, constraints, examples
and output format. It directs contextual filler removal and equivalent abbreviation
before broader rewriting, with supported expansion for underfill and existing split
policy for dense bullets. Suggestions never automatically delete or rewrite wording;
Python still validates, measures and ranks each returned revision. A detected filler
word is not proof it is expendable in every technical phrase. Qualification matching
is a conservative pattern list, not a complete semantic extractor.

These helpers run in the backend, not through model tool-calling round trips. The
internal response schema and public content schemas are unchanged. The batch budget
is one initial call plus `ITERATION_CALLS` retries (default 1). Accepted one-line
items still make zero optimization calls. These fitter
helpers introduce no NLP model dependency, automatic saved-content rewrite or
independent semantic verification. Main-generation preprocessing is separate.

## Main-generation input preprocessing

### Optional Lite experiment

Set `RESUME_LLM_LITE_PREPROCESSING=true` and `ASSIST_MODEL` to a model
available through the existing resume provider. `GeminiLLMClient(purpose="preprocessing")`
uses the same provider, key and endpoint, overriding only the model/deployment.
`GOOGLE_MODEL` selects the main generation/fitter model (with `GEMINI_MODEL` as a
legacy fallback). `ASSIST_MODEL` selects only the preprocessing model (for example, `gemini-2.0-flash`).
No second credential is required. Restart the Django process after configuration.

The generation endpoint calls `services/lite_preprocessing.py` once for a narrative
input, before building the main prompt. The assist model writes concise, organized
plain-English `organized_points`, correcting grammar and removing conversational
noise, filler and repetition. It may paraphrase these points while preserving
important facts, metrics and qualifications; it does not fit PDF widths or impose
a final resume word count. Role, organization, location and timeline remain context.
Lite returns only contributions (`source_ids` and `organized_points`),
`unassigned_source_ids`, and freely worded `ambiguities`. It no longer supplies
`core_action_quote`, quote inventories, or qualification metadata. Python builds
source-position references, numeric evidence and qualification context directly
from the referenced original units. No exact-copy task is imposed on the model.

On success, cleaned points become the main model's working `user_input`, alongside
compact evidence and qualifications. Complete raw input and duplicate local source
records are not resent. Unassigned/ambiguous passages and any source tail beyond
the local extraction limit are retained as explicitly unresolved source notes.
When Lite is disabled or fails, the previous raw-input/local-record path remains.
Original raw input is never overwritten and still drives retrieval.

Python validates the internal schema, source IDs, source coverage, nonempty cleaned
points and genuinely unsupported numeric values. Shared quantity normalization
handles lowercase/uppercase `k`, decimal magnitudes and explicit scale words such
as thousand/million, without float truncation. Lite additionally recognizes written
quantities and attached dates/versions before comparison. Thus `5k+` and `5,000+`
do not cause a false rejection; `5k` and `50,000` still differ.

Numbers are checked against the entire input's extracted source units. When a
reorganized point uses a quantity from a different unit than its primary IDs,
`numeric_context_source_ids` records the additional evidence explicitly. Its source
references, numeric evidence and qualifications are carried into main generation.
This trusts Lite's grouping instead of treating imperfect grouping metadata as a
new numeric fact. It does not independently verify that the value describes the
correct action, unit or metric.

The backend trusts Lite's rewriting and grouping;
the previous exact-quote and model-declared-essential-number gates are removed.
Omitted numbers remain available as source numeric evidence for main generation.
Existing numeric normalization supports equivalent forms where recognized. These
checks do not establish semantic equivalence, correct metric association, or full
factual preservation. Source qualifications are supplied as explicit context even
if the cleaned notes omitted their wording. Main generation must honor that context.
Extraction/cache version 6 invalidates earlier responses. The raw model response
is cached separately from locally built context, then revalidated and materialized
on cache hits. Public content schemas and response types do not change.

Successful organization is cached for one hour, keyed by owner-bound resume/entry
scope, raw text, section, provider, model and extraction version. Cache hits make no
extraction model call. Invalid output, missing configuration or provider failure
falls back to the existing local-only context without an extraction retry. Logs
identify the fallback without source text, credentials or provider response bodies.
Fallback logs include a controlled stage, reason code and numeric HTTP status.
For example, `stage=response_validation reason=invalid_source_ids` means
source references were invalid; `stage=provider_request
reason=provider_unavailable http_status=503` means a provider request failed.
Other local reasons distinguish missing coverage, unsupported numeric values and
empty points. Diagnostics include the field/contribution where available. These logs
never include raw exception messages, rejected quotes or provider response bodies.

`ITERATION_CALLS` independently controls optimizer retries per frozen batch,
including mixed bullet/summary batches and explicit refits. `0` allows just the
initial call; `1` allows one retry (two calls total); `2` allows two retries, etc.
The default is `1`. Values must be non-negative integers. Failures and malformed
responses consume invocations; resolved items stop early. This budget does not
change when Lite extraction succeeds, fails or hits cache. Candidate validation,
LaTeX measurement, best-candidate retention and unresolved reporting remain intact.
Fitting still makes zero calls for accepted content. Disabling the Lite flag
restores Python-only preprocessing without changing the retry setting.
It is not always a one-for-one call exchange: extraction runs once per input,
whereas retries previously applied per batch. Existing SDK transport retry behavior
is unchanged; these budgets count application invocations.

For the three comparison modes, set the following and restart Django:

| Mode                                                           | `RESUME_LLM_LITE_PREPROCESSING` | `ITERATION_CALLS` |
| -------------------------------------------------------------- | ------------------------------- | ----------------- |
| Main generation + optimizer with one retry                     | `false`                         | `1`               |
| Main generation + optimizer without retry                      | `false`                         | `0`               |
| Lite preprocessing + main generation + optimizer without retry | `true`                          | `0`               |

`ASSIST_MODEL` is used only with Lite enabled; `GOOGLE_MODEL` remains the main model.
Lite cache hits may affect latency comparisons; use comparable cache conditions
when measuring the three modes. Neither retry configuration nor preprocessing
rewrites existing saved content without generation or an explicit accepted refit.

`services/input_preprocessing.py` adds a deterministic, local extraction step when
building prompts for projects, professional experience and positions of
responsibility. It adds no model call, dependency or database/schema change.
The raw input still drives retrieval and remains the factual source for generation.

The extractor identifies conservative source units plus action mentions, known
technologies/datasets, numeric mentions (including some written counts) and selected
qualification/negation phrases. Each mention includes exact original character
offsets. Numeric mentions retain their complete source unit; the extractor does
not invent metric labels, causal links, core meanings or priority classifications.
Technology matching uses a deliberately limited vocabulary. Unknown entities,
organizations and locations remain available in the original input. At most 64
units are emitted; incomplete extraction is explicitly flagged as truncated.

The generation prompt includes these advisory records and the full original input
in separately labeled JSON data blocks. Literal tag delimiters in source text are
escaped in these blocks. Runtime guidance allows narrative regrouping, paraphrasing,
filler removal and omission of secondary implementation details, overriding older
requirements to preserve every detail literally. It requires preserving core
meaning, important results/counts/units and qualifications, including ones in other
source units. A matched entity is not automatically mandatory, and absence from the
extractor does not make a fact unimportant. Prior output and RAG examples remain
context/style data. The response still uses the existing section schema only.

This version uses Python rules, not spaCy or another extraction model. It is not a
full semantic parser: ambiguous relationships are left unassigned for interpretation
against the raw source. Header, education, skills, coursework and achievements keep
their existing prompts. JSON edits, ordinary rendering, style changes and refit
apply do not invoke this generation preprocessing path.

## Explicit refit review

**Refit to current style** is beside the style controls. It previews visible,
completed entries and excludes manual/unknown content by default. Existing rows
receive protected `unknown` provenance through migration `0007`.

The unchecked **Include manually edited and existing content** option explicitly
includes protected entries. Changing that option clears the previous preview.
The dialog shows original/proposed wording, measurements, and unresolved fitting
statuses, including unresolved targets and any reported wording changes. Acceptance
checkboxes start unchecked; only selected changes are saved.
Accepted refits preserve manual/unknown protection for future refits.

- `POST /api/resumes/{id}/refit/preview/` accepts `include_manual` and returns
  proposals, reports, an excluded-entry count, and a signed token. It never saves
  wording or modifies the resume's LaTeX/PDF caches.
- `POST /api/resumes/{id}/refit/apply/` accepts `token` and `selected_ids`. Tokens
  expire after 15 minutes and bind owner, resume, layout, content, and inclusion
  choice. Changed content/layout, invalid selections, or expired tokens return
  `409`; compilation failures return `422` and roll back accepted changes.
- Apply performs no measurement or LLM calls. It uses the existing assembly and
  PDF cache flow and preserves fitting status for accepted proposals.

Measurement jobs share the renderer's isolated Docker compilation implementation.
Successful probe results use a separate content-addressed cache; cached positions
are rebound to the current entry IDs. Normal PDF caching remains independent.
The shared Markdown parser also fixes escaped underline delimiters, which
previously generated invalid LaTeX after sanitization. IITB bullets beginning
with `[` are protected from LaTeX's optional item-label parsing, keeping literal
text and measured text consistent.
IITB entry headings end their paragraph before drawing a left-aligned separator;
the following italic summary starts its own paragraph. This fixes the separator's
left gap without changing saved wording. The generation prompt asks for a compact
project-purpose summary rather than a second list of tools.

## Layout limits

Short factual bullets may not reach 88% without unsupported padding. Dense mandatory facts or
long indivisible identifiers may exceed the available width. Forced breaks,
unrenderable text, hidden sections with no rendered context, missing fonts, or
unavailable LaTeX measurements may prevent a reliable one- or two-line fit. In these
cases the fitter keeps locally checked wording and reports an unresolved status; it does
not discard facts or block valid generation. Semantic preservation relies on prompt constraints and local checks; a same-call
factual inventory or self-check is not independent verification. Tests stub model
responses and exercise the existing LaTeX/PDF measurement path.

## Workflow files (including prior implementation)

Backend:

- `server/resume_renderer/services/line_fitter.py`
- `server/resume_renderer/services/llm_client.py`
- `server/resume_renderer/services/bullet_probe.py` (new)
- `server/resume_renderer/services/renderer.py`
- `server/resume_renderer/services/markdown_parser.py`
- `server/resume_renderer/schemas/converters/convert_experience.py`
- `server/resume_renderer/schemas/converters/convert_key_project.py`
- `server/resume_renderer/schemas/converters/convert_pors.py`
- `server/resume_renderer/schemas/converters/convert_scholastic_achievements.py`
- `server/resume_renderer/schemas/converters/jake.py`
- `server/resume_renderer/schemas/converters/awesome_cv.py`
- `server/resumes/models.py`
- `server/resumes/serializers.py`
- `server/resumes/views.py`
- `server/resumes/urls.py`
- `server/resumes/services/refit.py` (new)
- `server/resumes/migrations/0007_entry_fitting_provenance.py` (new)
- `server/resume_builder/settings.py`
- `server/.env.example`
- `server/pytest.ini`
- `server/resume_renderer/tests/test_line_fitter.py` (new)
- `server/resume_renderer/tests/test_llm_client_errors.py` (new)
- `server/resume_renderer/tests/test_bullet_measurement.py` (new)
- `server/resume_renderer/tests/test_services.py`
- `server/resumes/tests/test_refit.py` (new)

Frontend:

- `client/src/components/editor-panel/RefitControl.tsx` (new)
- `client/src/components/editor-panel/editor-layout.tsx`
- `client/src/components/editor-panel/editor-layout.css`
- `client/src/components/editor-panel/section-item.tsx`
- `client/src/components/editor-panel/generated-textarea.tsx`
- `client/src/lib/api.ts`
- `client/src/types/resume.ts`
- `client/src/components/editor-panel/fitting.test.tsx` (new)
- `client/src/lib/api.test.ts` (new)
- `client/src/test-setup.ts` (new)
- `client/vitest.config.ts` (new)
- `client/package.json`
- `client/package-lock.json`

Documentation: this file. Pre-existing changes to `AuthProvider.tsx` and
`token_dec.py` were preserved. PDF viewer files were not changed.

## Verification

Regression tests cover advisory unmatched annotations, core phrase/verb rewriting,
normalized count/temperature/abbreviation references, unchanged critical metrics,
core-technology loss, unsupported proposed labels and held-out/test qualification
loss. Existing fitter, rendered-PDF, call-budget, manual-edit and refit tests remain.
No live model calls are used for verification.

Advisory-metadata verification: **131 focused backend tests passed** and **3 real
Docker PDF fitting tests passed**. The added regressions reproduce the research
entry's count/unit/reference normalization and optional-metadata rejection cases.
Ruff and whitespace checks passed; no live model calls or saved-entry rewrites
were performed during verification.
