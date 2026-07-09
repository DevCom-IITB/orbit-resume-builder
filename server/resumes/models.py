import uuid
from django.db import models
from django.contrib.auth.models import User


class SectionTypeDefinition(models.Model):
    key = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128)
    llm_prompt_instructions = models.TextField()
    json_schema = models.JSONField()
    entry_hint_text = models.TextField(blank=True, default="")
    allow_multiple_entries = models.BooleanField(default=True)
    default_converter_key = models.CharField(max_length=64, default="default_projects")

    def __str__(self):
        return self.display_name


class VisualTheme(models.Model):
    key = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128)
    compatible_families = models.JSONField(default=list)
    converter_set_key = models.CharField(max_length=64)
    latex_preamble = models.TextField()

    def __str__(self):
        return self.display_name


class ResumeTemplate(models.Model):
    key = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=128)
    family = models.CharField(max_length=32)
    domain = models.CharField(max_length=32)
    max_pages = models.IntegerField(null=True, blank=True)
    template_config = models.JSONField(default=dict)
    available_themes = models.ManyToManyField(VisualTheme, related_name="templates", blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name


class TemplateSectionType(models.Model):
    template = models.ForeignKey(
        ResumeTemplate, on_delete=models.CASCADE, related_name="section_manifest"
    )
    section_type = models.ForeignKey(
        SectionTypeDefinition, on_delete=models.PROTECT, related_name="template_usages"
    )
    is_default = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    default_order = models.IntegerField(default=0)

    class Meta:
        unique_together = [("template", "section_type")]
        ordering = ["default_order"]

    def __str__(self):
        return f"{self.template.key} / {self.section_type.key}"


class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=255)
    template = models.ForeignKey(
        ResumeTemplate, on_delete=models.PROTECT, related_name="resumes"
    )
    visual_theme = models.ForeignKey(
        VisualTheme, on_delete=models.PROTECT, related_name="resumes"
    )
    pages = models.IntegerField(default=1)
    config_override = models.JSONField(default=dict)
    is_pinned = models.BooleanField(default=False)
    cached_latex = models.TextField(null=True, blank=True)
    latex_cache_valid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.owner.username})"


class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="sections")
    section_type = models.ForeignKey(
        SectionTypeDefinition, on_delete=models.PROTECT, related_name="instances"
    )
    order = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("resume", "section_type")]
        ordering = ["order"]

    def __str__(self):
        return f"{self.resume.title} / {self.section_type.key}"


class SectionEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="entries")
    order = models.IntegerField(default=0)
    raw_input = models.TextField(blank=True, default="")
    content = models.JSONField(null=True, blank=True)
    last_sent_prompt = models.TextField(blank=True, default="")
    generation_status = models.CharField(
        max_length=16,
        choices=[
            ("pending", "Pending"),
            ("generating", "Generating"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.section} entry #{self.order}"


class Version(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name="versions")
    snapshot = models.JSONField(default=dict)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Version of {self.resume.title} at {self.created_at}"
