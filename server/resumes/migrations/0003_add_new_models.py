import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0002_resume_is_pinned"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionTypeDefinition",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("key", models.CharField(max_length=64, unique=True)),
                ("display_name", models.CharField(max_length=128)),
                ("llm_prompt_instructions", models.TextField()),
                ("json_schema", models.JSONField()),
                ("entry_hint_text", models.TextField(blank=True, default="")),
                ("allow_multiple_entries", models.BooleanField(default=True)),
                ("default_converter_key", models.CharField(default="default_projects", max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="VisualTheme",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("key", models.CharField(max_length=64, unique=True)),
                ("display_name", models.CharField(max_length=128)),
                ("compatible_families", models.JSONField(default=list)),
                ("converter_set_key", models.CharField(max_length=64)),
                ("latex_preamble", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="ResumeTemplate",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("key", models.CharField(max_length=64, unique=True)),
                ("display_name", models.CharField(max_length=128)),
                ("family", models.CharField(max_length=32)),
                ("domain", models.CharField(max_length=32)),
                ("max_pages", models.IntegerField(blank=True, null=True)),
                ("template_config", models.JSONField(default=dict)),
                ("available_themes", models.ManyToManyField(
                    blank=True, related_name="templates", to="resumes.visualtheme"
                )),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="TemplateSectionType",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("is_default", models.BooleanField(default=True)),
                ("is_required", models.BooleanField(default=False)),
                ("default_order", models.IntegerField(default=0)),
                ("template", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="section_manifest",
                    to="resumes.resumetemplate",
                )),
                ("section_type", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="template_usages",
                    to="resumes.sectiontypedefinition",
                )),
            ],
            options={
                "ordering": ["default_order"],
                "unique_together": {("template", "section_type")},
            },
        ),
        # Add new FK fields to Resume (nullable during migration)
        migrations.AddField(
            model_name="resume",
            name="template",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="resumes",
                to="resumes.resumetemplate",
            ),
        ),
        migrations.AddField(
            model_name="resume",
            name="visual_theme",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="resumes",
                to="resumes.visualtheme",
            ),
        ),
        migrations.AddField(
            model_name="resume",
            name="pages",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="resume",
            name="config_override",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="resume",
            name="cached_latex",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="resume",
            name="latex_cache_valid",
            field=models.BooleanField(default=False),
        ),
        # Rename old section_type CharField to legacy name so we can add new FK
        migrations.RenameField(
            model_name="section",
            old_name="section_type",
            new_name="section_type_legacy",
        ),
        # Add new section_type FK (nullable during migration)
        migrations.AddField(
            model_name="section",
            name="section_type",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="instances",
                to="resumes.sectiontypedefinition",
            ),
        ),
        migrations.AddField(
            model_name="section",
            name="is_visible",
            field=models.BooleanField(default=True),
        ),
        # New SectionEntry model
        migrations.CreateModel(
            name="SectionEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("order", models.IntegerField(default=0)),
                ("raw_input", models.TextField(blank=True, default="")),
                ("content", models.JSONField(blank=True, null=True)),
                ("last_sent_prompt", models.TextField(blank=True, default="")),
                ("generation_status", models.CharField(
                    choices=[
                        ("pending", "Pending"),
                        ("generating", "Generating"),
                        ("done", "Done"),
                        ("failed", "Failed"),
                    ],
                    default="pending",
                    max_length=16,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("section", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="entries",
                    to="resumes.section",
                )),
            ],
            options={
                "ordering": ["order"],
            },
        ),
    ]
