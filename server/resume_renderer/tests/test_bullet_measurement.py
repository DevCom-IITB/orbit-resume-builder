"""Real TeX measurements, with final PDF line-placement checks."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.cache import cache
from django.core.management import call_command

from resume_renderer.services.line_fitter import measure_entries, measure_summaries
from resume_renderer.services.renderer import (
    _get_latex_container,
    assemble_resume_latex,
    compile_latex,
    compile_latex_job,
)
from resumes.models import (
    Resume,
    ResumeTemplate,
    Section,
    SectionEntry,
    SectionTypeDefinition,
)

MATRIX = [
    (template, font)
    for template in [
        "iitb-general",
        "external-standard",
        "jake-general",
        "awesome-cv-general",
    ]
    for font in (
        ["sourcesans", "helvetica", "lmodern"]
        if template == "awesome-cv-general"
        else ["lmodern", "times", "palatino"]
    )
]


@pytest.fixture
def probe_resume(db, django_user_model):
    try:
        _get_latex_container()
    except RuntimeError as exc:
        pytest.skip(str(exc))
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="probeuser")
    template = ResumeTemplate.objects.get(key="jake-general")
    resume = Resume.objects.create(
        owner=user,
        title="Probe",
        template=template,
        visual_theme=template.available_themes.first(),
    )
    section = Section.objects.create(
        resume=resume,
        section_type=SectionTypeDefinition.objects.get(key="key_projects"),
    )
    content = [
        {
            "title": "Build",
            "organization": "Acme",
            "timeline": "2024",
            "summary": "",
            "bullets": [
                "FitprobeAlpha **Python** and *Docker* improved _builds_ by 20%.",
                "FitprobeAlpha **Python** and *Docker* improved _builds_ by 20%.",
                "FitprobeLong " + "delivery workflows " * 24 + "LongEnd",
            ],
        }
    ]
    entry = SectionEntry.objects.create(
        section=section, content=content, generation_status="done", content_origin="ai"
    )
    return resume, entry


@pytest.mark.docker
@pytest.mark.parametrize("template_key,font", MATRIX)
def test_real_measurement_matches_pdf_for_all_templates_and_fonts(
    probe_resume, template_key, font
):
    import fitz

    resume, entry = probe_resume
    resume.template = ResumeTemplate.objects.get(key=template_key)
    resume.visual_theme = resume.template.available_themes.first()
    resume.config_override = {"style": {"font": font, "word_spacing": "1.15"}}
    resume.save()
    normal = assemble_resume_latex(resume)
    saved_cache = resume.cached_latex
    original = copy.deepcopy(entry.content)
    entries = {str(entry.id): ("key_projects", entry.content)}
    measured = measure_entries(resume, entries)
    short, duplicate, long = [
        measured[(str(entry.id), 0, "bullets", i)] for i in range(3)
    ]
    assert short == duplicate
    assert short["line_measurement"] == "rendered_pdf"
    assert long["line_measurement"] == "rendered_pdf"
    assert len(long["line_widths_pt"]) == long["lines"]
    assert short["lines"] == 1 and short["ratio"] < 1
    assert long["lines"] > 1 and long["ratio"] > 1
    resume.refresh_from_db()
    entry.refresh_from_db()
    assert resume.cached_latex == saved_cache and resume.latex_cache_valid
    assert entry.content == original
    assert "ResumeFitProbe" not in normal
    with fitz.open(stream=compile_latex(normal), filetype="pdf") as doc:
        assert all(
            not link.get("uri", "").startswith("resumefit:")
            for page in doc
            for link in page.get_links()
        )
        lines = [
            line
            for page in doc
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
        ]
        texts = ["".join(span["text"] for span in line["spans"]) for line in lines]
        starts = [i for i, text in enumerate(texts) if "FitprobeAlpha" in text]
        assert len(starts) == 2
        assert all("20%" in texts[i] for i in starts)
        begin = next(i for i, text in enumerate(texts) if "FitprobeLong" in text)
        end = next(i for i, text in enumerate(texts) if "LongEnd" in text)
        assert end - begin + 1 == long["lines"]
    # Changing actual font/spacing must change the measured width; no stale probe cache.
    resume.config_override["style"]["word_spacing"] = "1.00"
    unspaced = measure_entries(resume, entries)
    assert unspaced[(str(entry.id), 0, "bullets", 0)]["width_pt"] < short["width_pt"]
    # Identical probe documents use the measurement cache, without recompilation.
    assert measure_entries(resume, entries) == unspaced


@pytest.mark.docker
def test_measurement_jobs_are_isolated(probe_resume):
    resume, entry = probe_resume
    ids = {(str(entry.id), 0, "bullets", i): i for i in range(3)}
    source = assemble_resume_latex(resume, probe_ids=ids)
    with ThreadPoolExecutor(max_workers=2) as pool:
        logs = list(
            pool.map(lambda _: compile_latex_job(source, read_pdf=False)[1], range(2))
        )
    assert all("RF-W:0:" in log and "RF-L:2:" in log for log in logs)


@pytest.mark.docker
@pytest.mark.parametrize(
    "template_key",
    ["iitb-general", "external-standard", "jake-general", "awesome-cv-general"],
)
def test_project_summary_probe_matches_pdf_line_count(probe_resume, template_key):
    import fitz

    resume, entry = probe_resume
    resume.template = ResumeTemplate.objects.get(key=template_key)
    resume.visual_theme = resume.template.available_themes.first()
    resume.save()
    long_summary = (
        "SummaryProbeStart " + "document retrieval workflow " * 13 + "SummaryProbeEnd"
    )
    entry.content[0]["summary"] = long_summary
    entry.save(update_fields=["content"])
    entries = {str(entry.id): ("key_projects", entry.content)}
    measured = measure_summaries(resume, entries)[(str(entry.id), 0, "summary")]
    assert measured["lines"] > 1
    with fitz.open(
        stream=compile_latex(assemble_resume_latex(resume)), filetype="pdf"
    ) as doc:
        lines = [
            line
            for page in doc
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
        ]
        texts = ["".join(span["text"] for span in line["spans"]) for line in lines]
        start = next(i for i, text in enumerate(texts) if "SummaryProbeStart" in text)
        end = next(i for i, text in enumerate(texts) if "SummaryProbeEnd" in text)
        assert end - start + 1 == measured["lines"]
        if template_key in {"iitb-general", "external-standard"}:
            heading = next(
                i for i, text in enumerate(texts) if text.startswith("Build")
            )
            assert lines[start]["bbox"][1] >= lines[heading]["bbox"][3] - 1
            first_bullet = next(
                i for i, text in enumerate(texts) if "FitprobeAlpha" in text
            )
            assert lines[first_bullet]["bbox"][1] >= lines[end]["bbox"][3] - 1
    entry.content[0]["summary"] = "A document retrieval workflow"
    short = measure_summaries(resume, {str(entry.id): ("key_projects", entry.content)})
    assert short[(str(entry.id), 0, "summary")]["lines"] == 1


@pytest.mark.docker
def test_iitb_project_separator_starts_at_heading_margin(probe_resume):
    import fitz

    resume, _ = probe_resume
    resume.template = ResumeTemplate.objects.get(key="iitb-general")
    resume.visual_theme = resume.template.available_themes.first()
    resume.save()
    with fitz.open(
        stream=compile_latex(assemble_resume_latex(resume)), filetype="pdf"
    ) as doc:
        page = doc[0]
        title = next(
            span
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
            for span in line["spans"]
            if span["text"] == "Build"
        )
        rules = [
            item[1]
            for drawing in page.get_drawings()
            for item in drawing["items"]
            if item[0] == "l"
            and abs(item[1].y - item[2].y) < 0.5
            and item[2].x - item[1].x > 300
            and title["bbox"][1] <= item[1].y <= title["bbox"][3] + 15
        ]
        assert rules
        assert min(abs(point.x - title["bbox"][0]) for point in rules) < 2


def test_measurement_cache_uses_document_and_missing_output_is_failure(monkeypatch):
    from resume_renderer.services import renderer

    cache.clear()
    assembler = MockAssembler()
    monkeypatch.setattr(renderer, "assemble_resume_latex", assembler)
    from unittest.mock import Mock

    compiler = Mock(return_value=(b"", "RF-W:0:380.0pt:400.0pt\nRF-L:0:1"))
    monkeypatch.setattr(renderer, "compile_latex_job", compiler)
    entries = {"e": ("key_projects", [{"bullets": ["text"]}])}
    assert measure_entries(None, entries)[("e", 0, "bullets", 0)]["ratio"] == 0.95
    measure_entries(None, entries)
    assert compiler.call_count == 1
    other_entries = {"another-entry": entries["e"]}
    assert ("another-entry", 0, "bullets", 0) in measure_entries(None, other_entries)
    assert compiler.call_count == 1  # IDs are rebound on cache hits
    assembler.document = "different style"
    compiler.return_value = (b"", "missing marker")
    with pytest.raises(ValueError):
        measure_entries(None, entries)


class MockAssembler:
    document = "document"

    def __call__(self, *args, **kwargs):
        return self.document


@pytest.mark.docker
@pytest.mark.parametrize(
    "template_key",
    ["iitb-general", "external-standard", "jake-general", "awesome-cv-general"],
)
def test_supported_sections_and_unselected_duplicates(probe_resume, template_key):
    resume, project = probe_resume
    resume.template = ResumeTemplate.objects.get(key=template_key)
    resume.visual_theme = resume.template.available_themes.first()
    resume.save()
    entries = {str(project.id): ("key_projects", project.content)}
    for section_key in [
        "professional_experience",
        "positions_of_responsibility",
        "scholastic_achievements",
    ]:
        section = Section.objects.create(
            resume=resume,
            section_type=SectionTypeDefinition.objects.get(key=section_key),
        )
        content = (
            [
                "Measured Python tools",
                {"text": "Untouched object achievement", "year": "2024"},
            ]
            if section_key == "scholastic_achievements"
            else [
                {
                    "title": "Engineer",
                    "role": "Lead",
                    "organization": "Acme",
                    "location": "Remote",
                    "timeline": "2024",
                    "duration": "2024",
                    "summary": "",
                    "bullets": ["Measured Python tools"],
                }
            ]
        )
        entry = SectionEntry.objects.create(
            section=section, content=content, generation_status="done"
        )
        entries[str(entry.id)] = (section_key, content)
    # An earlier unselected entry has identical bullet text. Its probe queue slots
    # must not steal measurements belonging to selected entries.
    SectionEntry.objects.create(
        section=project.section,
        order=-1,
        content=project.content,
        generation_status="done",
    )
    measured = measure_entries(resume, entries)
    assert len(measured) == 6  # 3 project bullets + one in each other supported field
    assert all(m["available_pt"] > 0 and m["lines"] >= 1 for m in measured.values())


@pytest.mark.docker
def test_generation_fitter_uses_real_tex_and_final_pdf(probe_resume, settings):
    settings.BULLET_FIT_MIN_RATIO = 0.92
    settings.BULLET_FIT_MAX_RATIO = 0.97
    import itertools
    from unittest.mock import Mock
    import fitz
    from resume_renderer.services.line_fitter import fit_bullets_in_content

    resume, entry = probe_resume
    resume.config_override = {"style": {"font": "times", "word_spacing": "1.10"}}
    resume.save()
    entry.generation_status = "generating"
    entry.save()
    original = (
        "Implemented automated checking for deployment activities using Python and Docker, resulting "
        "in a reduction of build time by 20% for a total of 12 services, and tracked failures in these deployments."
    )
    alternatives = [
        f"{a} deployment checks {b}, {c} build time by 20% {d} 12 services {e}"
        for a, b, c, d, e in itertools.product(
            ["Automated", "Built automation for"],
            ["using Python/Docker", "using Python and Docker"],
            ["cutting", "reducing"],
            ["for", "across"],
            ["and tracked failures.", "and monitored deployment failures."],
        )
    ]
    content = copy.deepcopy(entry.content)
    content[0]["bullets"] = alternatives
    measured = measure_entries(resume, {str(entry.id): ("key_projects", content)})
    fitting_candidates = [
        alternatives[i]
        for i in range(len(alternatives))
        if 0.92 <= measured[(str(entry.id), 0, "bullets", i)]["ratio"] <= 0.97
        and measured[(str(entry.id), 0, "bullets", i)]["lines"] == 1
    ]
    assert fitting_candidates, (
        "Fixture paraphrases must bracket the actual measured target."
    )
    candidate = fitting_candidates[0]
    content[0]["bullets"] = [original]
    llm = Mock()
    llm.generate_json.return_value = {
        "fixes": [
            {
                "index": 0,
                "bullets": [candidate],
                "action": "compress",
                "dropped": [],
                "added": [],
                "reason": "Equivalent phrasing",
                "facts": {
                    "claims": [original],
                    "protected": ["Python", "Docker", "20%", "12"],
                    "details": [],
                },
            }
        ]
    }
    fitted, report = fit_bullets_in_content(
        content, "key_projects", llm, resume=resume, entry_id=entry.id
    )
    assert fitted[0]["bullets"] == [candidate]
    assert report["bullets"][0]["status"] == "fitted"
    final_source = assemble_resume_latex(
        resume, content_overrides={str(entry.id): fitted}
    )
    with fitz.open(stream=compile_latex(final_source), filetype="pdf") as pdf:
        lines = [
            line
            for page in pdf
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
        ]
        bullet = [
            line
            for line in lines
            if "Python" in "".join(s["text"] for s in line["spans"])
        ]
        assert len(bullet) == 1
        assert "failures" in "".join(s["text"] for s in bullet[0]["spans"])


@pytest.mark.docker
def test_well_filled_two_line_bullet_keeps_wording_in_final_pdf(probe_resume, settings):
    from unittest.mock import Mock
    import fitz
    from resume_renderer.services.line_fitter import fit_bullets_in_content

    settings.BULLET_FIT_MIN_RATIO = 0.88
    settings.BULLET_FIT_MAX_RATIO = 1.0
    resume, entry = probe_resume
    base = "Twolineprobe automated deployment checks using Python and Docker for 12 services, reduced build time by 20% and tracked failures"
    candidates = [base + " checks" * n + "." for n in range(30)]
    content = copy.deepcopy(entry.content)
    content[0]["bullets"] = candidates
    measured = measure_entries(resume, {str(entry.id): ("key_projects", content)})
    suitable = [
        text
        for i, text in enumerate(candidates)
        if measured[(str(entry.id), 0, "bullets", i)]["lines"] == 2
        and 1.88 <= measured[(str(entry.id), 0, "bullets", i)]["ratio"] <= 2.0
    ]
    assert suitable
    content[0]["bullets"] = [suitable[0]]
    llm = Mock()
    llm.generate_json.return_value = {
        "fixes": [
            {
                "index": 0,
                "bullets": [suitable[0]],
                "action": "keep",
                "dropped": [],
                "added": [],
                "reason": "Cannot safely shorten the factual claim.",
                "facts": {
                    "claims": [suitable[0]],
                    "protected": ["Python", "Docker", "12", "20%"],
                    "details": [],
                },
            }
        ]
    }
    fitted, report = fit_bullets_in_content(
        content, "key_projects", llm, resume=resume, entry_id=entry.id
    )
    assert fitted == content
    assert report["bullets"][0]["status"] == "unchanged"
    assert report["bullets"][0]["measurement"]["lines"] == 2
    assert llm.generate_json.call_count == 2
    assert "two-line fallback" in report["bullets"][0]["reason"]
    source = assemble_resume_latex(resume, content_overrides={str(entry.id): fitted})
    with fitz.open(stream=compile_latex(source), filetype="pdf") as pdf:
        lines = [
            "".join(span["text"] for span in line["spans"])
            for page in pdf
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
        ]
    first = next(i for i, line in enumerate(lines) if "Twolineprobe" in line)
    assert "checks" in lines[first + 1]
    assert len([line for line in lines if "Twolineprobe" in line]) == 1


@pytest.mark.docker
def test_bracket_prefix_is_literal_in_probe_and_final_pdf(probe_resume):
    import fitz

    resume, entry = probe_resume
    resume.template = ResumeTemplate.objects.get(key="iitb-general")
    resume.visual_theme = resume.template.available_themes.first()
    resume.save()
    entry.content[0]["bullets"] = ["[WIP] Built Python tools for deployment checks"]
    entry.save()
    measured = measure_entries(resume, {str(entry.id): ("key_projects", entry.content)})
    assert measured[(str(entry.id), 0, "bullets", 0)]["lines"] == 1
    source = assemble_resume_latex(resume)
    assert r"\item {[WIP]" in source
    with fitz.open(stream=compile_latex(source), filetype="pdf") as pdf:
        assert "[WIP] Built Python tools" in pdf[0].get_text()


@pytest.mark.docker
def test_distinct_split_bullets_are_measured_in_final_pdf(probe_resume):
    from unittest.mock import Mock
    import fitz
    from resume_renderer.services.line_fitter import fit_bullets_in_content

    resume, entry = probe_resume
    original = (
        "Automated deployment checks using Python and Docker for a total of 12 services, "
        "reduced build time by 20% across those services, and tracked failures in these deployments."
    )
    first = "Automated deployment checks using Python and Docker for 12 services."
    second = "Reduced build time by 20% across those services and tracked deployment failures."
    content = copy.deepcopy(entry.content)
    content[0]["bullets"] = [original]
    llm = Mock()
    llm.generate_json.return_value = {
        "fixes": [
            {
                "index": 0,
                "bullets": [first, second],
                "action": "split",
                "dropped": [],
                "added": [],
                "reason": "Separated the build from its measured result.",
                "facts": {
                    "claims": [original],
                    "protected": ["Python", "Docker", "12", "20%"],
                    "details": [],
                },
            }
        ]
    }
    fitted, report = fit_bullets_in_content(
        content, "key_projects", llm, resume=resume, entry_id=entry.id
    )
    assert fitted[0]["bullets"] == [first, second]
    assert [m["lines"] for m in report["bullets"][0]["measurements"]] == [1, 1]
    assert llm.generate_json.call_count <= 2
    source = assemble_resume_latex(resume, content_overrides={str(entry.id): fitted})
    with fitz.open(stream=compile_latex(source), filetype="pdf") as pdf:
        lines = [
            "".join(span["text"] for span in line["spans"])
            for page in pdf
            for block in page.get_text("dict")["blocks"]
            if "lines" in block
            for line in block["lines"]
        ]
    assert sum("Automated deployment checks" in line for line in lines) == 1
    assert sum("Reduced build time" in line for line in lines) == 1


@pytest.mark.docker
def test_real_marker_maps_a_bullet_across_page_breaks(probe_resume):
    resume, entry = probe_resume
    # A short diagnostic page exercises a genuine page break without exceeding
    # TeX's maximum natural box dimension with an artificial giant bullet.
    resume.visual_theme.latex_preamble = resume.visual_theme.latex_preamble.replace(
        r"\begin{document}",
        r"\geometry{paperheight=10cm,top=1cm,bottom=1cm}\begin{document}",
    )
    content = copy.deepcopy(entry.content)
    content[0]["bullets"] = [
        "PageprobeStart " + "delivery workflows " * 120 + "PageprobeEnd",
        "Neighbor Python bullet.",
    ]
    measured = measure_entries(resume, {str(entry.id): ("key_projects", content)})
    long = measured[(str(entry.id), 0, "bullets", 0)]
    neighbor = measured[(str(entry.id), 0, "bullets", 1)]
    assert long["line_measurement"] == "rendered_pdf", long
    assert len(set(long["line_pages"])) >= 2
    assert len(long["line_widths_pt"]) == long["lines"]
    assert neighbor["line_measurement"] == "rendered_pdf"
    assert neighbor["lines"] == 1


@pytest.mark.docker
def test_real_unbreakable_text_reports_box_overflow_and_compile_warning(probe_resume):
    resume, entry = probe_resume
    content = copy.deepcopy(entry.content)
    content[0]["bullets"] = ["Overfullprobe" + "W" * 150]
    measured = measure_entries(resume, {str(entry.id): ("key_projects", content)})
    item = measured[(str(entry.id), 0, "bullets", 0)]
    assert item["line_measurement"] == "rendered_pdf"
    assert item["has_box_overflow"]
    assert item["overflow_pt"] > 0.5
    assert any(
        w["kind"] == "overfull" and w["scope"] == "document"
        for w in item["compilation_warnings"]
    )
