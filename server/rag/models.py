import uuid
from django.db import models


class ReferenceResume(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, default="ANONYMOUS")
    department = models.CharField(max_length=128, blank=True, default="")
    company = models.CharField(max_length=128, blank=True, default="")
    domain = models.CharField(max_length=128, blank=True, default="")
    season_year = models.CharField(max_length=32, blank=True, default="")
    resume_type = models.CharField(max_length=32, blank=True, default="")  # INTERNSHIP / PLACEMENT
    resume_file = models.FileField(upload_to="referenceResumes/", null=False, blank=False)
    resume_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company} ({self.season_year})"
