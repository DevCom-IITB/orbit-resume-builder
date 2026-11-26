from django.db import migrations


# Maps old Section.section_type_legacy values → new SectionTypeDefinition keys
LEGACY_KEY_MAP = {
    "KEY_PROJECTS": "key_projects",
    "EXPERIENCE": "professional_experience",
    "SKILLS": "technical_skills",
    "EDUCATION": "education",
    "POR": "positions_of_responsibility",
}

SECTION_TYPE_DEFINITIONS = [
    {"key": "header",                     "display_name": "Header",                          "allow_multiple_entries": False, "default_converter_key": "convert_header"},
    {"key": "education",                  "display_name": "Education",                        "allow_multiple_entries": True,  "default_converter_key": "convert_education"},
    {"key": "scholastic_achievements",    "display_name": "Scholastic Achievements",          "allow_multiple_entries": True,  "default_converter_key": "convert_scholastic_achievements"},
    {"key": "courses",                    "display_name": "Relevant Courses Undertaken",      "allow_multiple_entries": True,  "default_converter_key": "convert_courses"},
    {"key": "professional_experience",    "display_name": "Professional Experience",          "allow_multiple_entries": True,  "default_converter_key": "convert_experience"},
    {"key": "key_projects",               "display_name": "Key Projects",                    "allow_multiple_entries": True,  "default_converter_key": "convert_key_project"},
    {"key": "positions_of_responsibility","display_name": "Positions of Responsibility",      "allow_multiple_entries": True,  "default_converter_key": "convert_pors"},
    {"key": "technical_skills",           "display_name": "Technical Skills",                "allow_multiple_entries": True,  "default_converter_key": "convert_technical_skills"},
]


def migrate_forward(apps, schema_editor):
    SectionTypeDefinition = apps.get_model("resumes", "SectionTypeDefinition")
    VisualTheme = apps.get_model("resumes", "VisualTheme")
    ResumeTemplate = apps.get_model("resumes", "ResumeTemplate")
    TemplateSectionType = apps.get_model("resumes", "TemplateSectionType")
    Resume = apps.get_model("resumes", "Resume")
    Section = apps.get_model("resumes", "Section")
    SectionEntry = apps.get_model("resumes", "SectionEntry")

    # 1. Create SectionTypeDefinition rows (minimal — seed command fills prompts/schemas)
    stdef_map = {}
    for defn in SECTION_TYPE_DEFINITIONS:
        stdef, _ = SectionTypeDefinition.objects.get_or_create(
            key=defn["key"],
            defaults={
                "display_name": defn["display_name"],
                "allow_multiple_entries": defn["allow_multiple_entries"],
                "default_converter_key": defn["default_converter_key"],
                "llm_prompt_instructions": "",
                "json_schema": {},
            },
        )
        stdef_map[defn["key"]] = stdef

    # 2. Create default VisualTheme
    iitb_theme, _ = VisualTheme.objects.get_or_create(
        key="iitb-classic",
        defaults={
            "display_name": "Classic (IIT Bombay)",
            "compatible_families": ["iitb"],
            "converter_set_key": "iitb-classic",
            "latex_preamble": "",  # seed command fills this
        },
    )
    external_theme, _ = VisualTheme.objects.get_or_create(
        key="external-standard",
        defaults={
            "display_name": "Standard (External)",
            "compatible_families": ["external"],
            "converter_set_key": "external-standard",
            "latex_preamble": "",
        },
    )

    # 3. Create ResumeTemplates
    iitb_template, _ = ResumeTemplate.objects.get_or_create(
        key="iitb-general",
        defaults={
            "display_name": "IIT Bombay",
            "family": "iitb",
            "domain": "general",
            "max_pages": None,
            "template_config": {
                "header_style_options": ["short", "long"],
                "header_style_default": "short",
            },
            "is_active": True,
        },
    )
    external_template, _ = ResumeTemplate.objects.get_or_create(
        key="external-standard",
        defaults={
            "display_name": "External",
            "family": "external",
            "domain": "general",
            "max_pages": None,
            "template_config": {},
            "is_active": True,
        },
    )

    # 4. Link themes to templates
    iitb_template.available_themes.add(iitb_theme)
    external_template.available_themes.add(external_theme)

    # 5. TemplateSectionType rows for iitb-general
    iitb_manifest = [
        ("header",                      True,  True,  0),
        ("education",                   True,  True,  1),
        ("scholastic_achievements",     True,  False, 2),
        ("courses",                     True,  False, 3),
        ("professional_experience",     True,  False, 4),
        ("key_projects",                True,  False, 5),
        ("positions_of_responsibility", True,  False, 6),
        ("technical_skills",            True,  False, 7),
    ]
    for stkey, is_default, is_required, order in iitb_manifest:
        TemplateSectionType.objects.get_or_create(
            template=iitb_template,
            section_type=stdef_map[stkey],
            defaults={"is_default": is_default, "is_required": is_required, "default_order": order},
        )

    # TemplateSectionType rows for external-standard
    external_manifest = [
        ("header",                      True,  True,  0),
        ("education",                   True,  True,  1),
        ("professional_experience",     True,  False, 2),
        ("key_projects",                True,  False, 3),
        ("technical_skills",            True,  False, 4),
        ("positions_of_responsibility", False, False, 5),
        ("courses",                     False, False, 6),
        ("scholastic_achievements",     False, False, 7),
    ]
    for stkey, is_default, is_required, order in external_manifest:
        TemplateSectionType.objects.get_or_create(
            template=external_template,
            section_type=stdef_map[stkey],
            defaults={"is_default": is_default, "is_required": is_required, "default_order": order},
        )

    # 6. Migrate existing Resumes
    for resume in Resume.objects.filter(template__isnull=True):
        header_style = getattr(resume, "header_type", "SHORT")
        config_override = {"header_style": "long" if header_style == "LONG" else "short"}
        # `meta` is dropped in 0005; keep its contents rather than losing them.
        legacy_meta = getattr(resume, "meta", None)
        if legacy_meta:
            config_override["legacy_meta"] = legacy_meta
        resume.template = iitb_template
        resume.visual_theme = iitb_theme
        resume.config_override = config_override
        # `resume_type` is dropped in 0005; carry the page count over.
        resume.pages = 2 if getattr(resume, "resume_type", "ONE") == "TWO" else 1
        resume.save()

        # Create header section + empty entry (user fills in later)
        header_stdef = stdef_map["header"]
        header_section, created = Section.objects.get_or_create(
            resume=resume,
            section_type=header_stdef,
            defaults={"order": 0, "is_visible": True},
        )
        if created:
            SectionEntry.objects.create(
                section=header_section,
                order=0,
                raw_input="",
                content=None,
                generation_status="pending",
            )

    # 7. Migrate existing Sections.
    # Every legacy section must end up with a section_type or be deleted:
    # 0005 makes section_type NOT NULL, so a leftover NULL aborts the migration.
    kept_sections = {}  # (resume_id, new_key) -> Section; one per type (unique_together)
    legacy_sections = Section.objects.filter(section_type__isnull=True).order_by(
        "resume_id", "order"
    )
    for section in legacy_sections:
        legacy_key = getattr(section, "section_type_legacy", None)
        new_key = LEGACY_KEY_MAP.get(legacy_key)
        content = getattr(section, "content", None) or []
        items = content if isinstance(content, list) else [content]

        if not new_key:
            # "OTHER" or unknown: no matching section type. Keep the content on
            # the resume (config_override is a free-form JSON field) and drop
            # the section row.
            if items:
                resume = section.resume
                override = dict(resume.config_override or {})
                override.setdefault("legacy_other_sections", []).append(
                    {"legacy_key": legacy_key, "content": items}
                )
                resume.config_override = override
                resume.save(update_fields=["config_override"])
            section.delete()
            continue

        target = kept_sections.get((section.resume_id, new_key))
        if target is None:
            # First section of this type on the resume: convert it in place.
            section.section_type = stdef_map[new_key]
            section.is_visible = True
            section.save()
            kept_sections[(section.resume_id, new_key)] = section
            target = section
            start_order = 0
        else:
            # Duplicate type on the same resume: merge its items into the
            # first one, after the entries already there.
            start_order = SectionEntry.objects.filter(section=target).count()

        # Migrate content array → SectionEntry rows
        for idx, item in enumerate(items):
            SectionEntry.objects.create(
                section=target,
                order=start_order + idx,
                raw_input="",
                content=item,
                generation_status="done",
            )

        if target is not section:
            section.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0003_add_new_models"),
    ]

    operations = [
        # No reverse: 0005 drops the legacy columns, so the old data can't be
        # rebuilt. Without reverse_code Django raises IrreversibleError instead
        # of silently "succeeding" and leaving orphaned rows.
        migrations.RunPython(migrate_forward),
    ]
