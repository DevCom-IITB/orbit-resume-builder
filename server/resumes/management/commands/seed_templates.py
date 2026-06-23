from django.core.management.base import BaseCommand

from resumes.models import (
    ResumeTemplate,
    SectionTypeDefinition,
    TemplateSectionType,
    VisualTheme,
)
from resume_renderer.JSONSchema.jsonschema import get_schema
from resume_renderer.services.prompts import SECTION_INSTRUCTIONS
from resume_renderer.services.renderer import TEMPLATE


SECTION_TYPES = [
    {
        "key": "header",
        "display_name": "Header",
        "allow_multiple_entries": False,
        "default_converter_key": "convert_header",
        "entry_hint_text": "Your full name, degree, and contact details (email, phone, LinkedIn, GitHub).",
    },
    {
        "key": "education",
        "display_name": "Education",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_education",
        "entry_hint_text": "Degree, institution, CPI/percentage, and year.",
    },
    {
        "key": "scholastic_achievements",
        "display_name": "Scholastic Achievements",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_scholastic_achievements",
        "entry_hint_text": "One academic achievement, rank, scholarship, or award.",
    },
    {
        "key": "courses",
        "display_name": "Relevant Courses Undertaken",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_courses",
        "entry_hint_text": "A category of courses (e.g. Computer Science: DSA, OS, Networks).",
    },
    {
        "key": "professional_experience",
        "display_name": "Professional Experience",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_experience",
        "entry_hint_text": "Describe your role, company, and what you worked on.",
    },
    {
        "key": "key_projects",
        "display_name": "Key Projects",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_key_project",
        "entry_hint_text": "Describe the project, its goal, your contribution, and technologies used.",
    },
    {
        "key": "positions_of_responsibility",
        "display_name": "Positions of Responsibility",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_pors",
        "entry_hint_text": "Your role, the organisation, duration, and what you did.",
    },
    {
        "key": "technical_skills",
        "display_name": "Technical Skills",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_technical_skills",
        "entry_hint_text": "A category of skills (e.g. Programming: Python, C++, JavaScript).",
    },
]

IITB_MANIFEST = [
    ("header",                      True,  True,  0),
    ("education",                   True,  True,  1),
    ("scholastic_achievements",     True,  False, 2),
    ("courses",                     True,  False, 3),
    ("professional_experience",     True,  False, 4),
    ("key_projects",                True,  False, 5),
    ("positions_of_responsibility", True,  False, 6),
    ("technical_skills",            True,  False, 7),
]

EXTERNAL_MANIFEST = [
    ("header",                      True,  True,  0),
    ("education",                   True,  True,  1),
    ("professional_experience",     True,  False, 2),
    ("key_projects",                True,  False, 3),
    ("technical_skills",            True,  False, 4),
    ("positions_of_responsibility", False, False, 5),
    ("courses",                     False, False, 6),
    ("scholastic_achievements",     False, False, 7),
]


class Command(BaseCommand):
    help = "Seed SectionTypeDefinitions, VisualThemes, ResumeTemplates, and TemplateSectionTypes"

    def handle(self, *args, **options):
        created_counts = {"stdef": 0, "themes": 0, "templates": 0, "tst": 0}
        updated_counts = {"stdef": 0}

        # 1. SectionTypeDefinitions
        stdef_map = {}
        for defn in SECTION_TYPES:
            schema = get_schema(defn["key"])
            instructions = SECTION_INSTRUCTIONS.get(defn["key"], "")

            stdef, created = SectionTypeDefinition.objects.update_or_create(
                key=defn["key"],
                defaults={
                    "display_name": defn["display_name"],
                    "allow_multiple_entries": defn["allow_multiple_entries"],
                    "default_converter_key": defn["default_converter_key"],
                    "entry_hint_text": defn["entry_hint_text"],
                    "llm_prompt_instructions": instructions,
                    "json_schema": schema,
                },
            )
            stdef_map[defn["key"]] = stdef
            if created:
                created_counts["stdef"] += 1
            else:
                updated_counts["stdef"] += 1

        # 2. VisualThemes
        iitb_theme, created = VisualTheme.objects.update_or_create(
            key="iitb-classic",
            defaults={
                "display_name": "Classic (IIT Bombay)",
                "compatible_families": ["iitb"],
                "converter_set_key": "iitb-classic",
                "latex_preamble": TEMPLATE,
            },
        )
        if created:
            created_counts["themes"] += 1

        external_theme, created = VisualTheme.objects.update_or_create(
            key="external-standard",
            defaults={
                "display_name": "Standard (External)",
                "compatible_families": ["external"],
                "converter_set_key": "external-standard",
                "latex_preamble": TEMPLATE,
            },
        )
        if created:
            created_counts["themes"] += 1

        # 3. ResumeTemplates
        iitb_template, created = ResumeTemplate.objects.update_or_create(
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
        iitb_template.available_themes.add(iitb_theme)
        if created:
            created_counts["templates"] += 1

        external_template, created = ResumeTemplate.objects.update_or_create(
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
        external_template.available_themes.add(external_theme)
        if created:
            created_counts["templates"] += 1

        # 4. TemplateSectionTypes
        for template, manifest in [(iitb_template, IITB_MANIFEST), (external_template, EXTERNAL_MANIFEST)]:
            for stkey, is_default, is_required, order in manifest:
                _, created = TemplateSectionType.objects.update_or_create(
                    template=template,
                    section_type=stdef_map[stkey],
                    defaults={
                        "is_default": is_default,
                        "is_required": is_required,
                        "default_order": order,
                    },
                )
                if created:
                    created_counts["tst"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_counts['stdef']} section types "
            f"({updated_counts['stdef']} updated), "
            f"{created_counts['themes']} themes, "
            f"{created_counts['templates']} templates, "
            f"{created_counts['tst']} TemplateSectionType rows."
        ))
