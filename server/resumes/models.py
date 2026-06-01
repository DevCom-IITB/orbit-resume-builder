import uuid
from django.db import models
from django.contrib.auth.models import User


class Resume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    title = models.CharField(max_length=255)
    RESUME_TYPE_CHOICES = [("ONE", "One-pager"), ("TWO", "Two-pager")]
    resume_type = models.CharField(
        max_length=3, choices=RESUME_TYPE_CHOICES, default="ONE"
    )
    HEADER_TYPE_CHOICES = [("SHORT", "Short"), ("LONG", "Long")]
    header_type = models.CharField(
        max_length=10, choices=HEADER_TYPE_CHOICES, default="SHORT"
    )
    meta = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.owner.username})"


class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="sections"
    )
    SECTION_TYPE_CHOICES = [
        ("KEY_PROJECTS", "Key Projects"),
        ("EXPERIENCE", "Experience"),
        ("SKILLS", "Skills"),
        ("EDUCATION", "Education"),
        ("POR", "Positions of Responsibility"),
        ("OTHER", "Other"),
    ]
    section_type = models.CharField(max_length=32, choices=SECTION_TYPE_CHOICES)
    order = models.IntegerField(default=0)
    content = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]


class Version(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resume = models.ForeignKey(
        Resume, on_delete=models.CASCADE, related_name="versions"
    )
    snapshot = models.JSONField(default=dict)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
