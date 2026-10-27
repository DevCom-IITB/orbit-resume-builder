import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
    improvement_suggestion = models.TextField(blank=True, default="")
    improvement_example = models.TextField(blank=True, default="")
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


class UserSecurityState(models.Model):
    """Tracks durable security and restriction state for LDAP users."""

    ldap_id = models.CharField(max_length=150, unique=True, db_index=True)
    blocked_until = models.DateTimeField(null=True, blank=True)
    abuse_score = models.IntegerField(default=0)
    violation_count = models.IntegerField(default=0)
    last_violation_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status_str = f"Blocked until {self.blocked_until}" if self.is_restricted() else "Active"
        return f"{self.ldap_id} ({status_str}, score: {self.abuse_score})"

    def is_restricted(self) -> bool:
        """Returns True if user currently has an active block timestamp."""
        if self.blocked_until is not None:
            return timezone.now() < self.blocked_until
        return False

    def record_violation(self, event_type: str, severity: str = "warning") -> None:
        """Increment counters and apply progressive temporary restriction if thresholds reached."""
        from django.conf import settings

        self.violation_count += 1
        delta = 1
        if severity == "high":
            delta = 2
        elif severity == "critical":
            delta = 4
        self.abuse_score += delta
        self.last_violation_at = timezone.now()

        # Escalation policy (configurable durations in seconds)
        b1 = getattr(settings, "ORBIT_ABUSE_FIRST_BLOCK_SECONDS", 600)
        b2 = getattr(settings, "ORBIT_ABUSE_SECOND_BLOCK_SECONDS", 3600)
        b3 = getattr(settings, "ORBIT_ABUSE_THIRD_BLOCK_SECONDS", 86400)

        # Conservative escalation:
        # Tier 3 (24hr): 7+ violations or abuse score >= 10
        # Tier 2 (1hr): 5+ violations or abuse score >= 6
        # Tier 1 (10min): 3+ violations or abuse score >= 3
        if self.violation_count >= 7 or self.abuse_score >= 10:
            self.blocked_until = timezone.now() + timedelta(seconds=b3)
        elif self.violation_count >= 5 or self.abuse_score >= 6:
            self.blocked_until = timezone.now() + timedelta(seconds=b2)
        elif self.violation_count >= 3 or self.abuse_score >= 3:
            self.blocked_until = timezone.now() + timedelta(seconds=b1)

        self.save()

    def unblock(self) -> None:
        """Manually clear restriction."""
        self.blocked_until = None
        self.save(update_fields=["blocked_until", "updated_at"])


class SecurityEvent(models.Model):
    """Durable audit trail for security and rate-limiting events."""

    EVENT_TYPES = [
        ("LLM_RATE_LIMIT_EXCEEDED", "LLM Rate Limit Exceeded"),
        ("LLM_DAILY_LIMIT_EXCEEDED", "LLM Daily Limit Exceeded"),
        ("OFF_TOPIC_INPUT", "Off-Topic Input"),
        ("PROMPT_INJECTION_SIGNAL", "Prompt Injection Signal"),
        ("ACCOUNT_RESTRICTED", "Account Restricted"),
        ("ACCOUNT_UNRESTRICTED", "Account Unrestricted"),
        ("INVALID_LLM_JSON", "Invalid LLM JSON"),
        ("LLM_PROVIDER_ERROR", "LLM Provider Error"),
        ("RENDERING_SECURITY_VIOLATION", "Rendering Security Violation"),
    ]

    ldap_id = models.CharField(max_length=150, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(max_length=32, default="info")  # info, warning, high, critical
    resume_id = models.CharField(max_length=64, null=True, blank=True)
    section_type = models.CharField(max_length=64, null=True, blank=True)
    endpoint = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.event_type} - {self.ldap_id} ({self.created_at})"
