from django.contrib import admin

from .models import (
    Resume,
    ResumeTemplate,
    Section,
    SectionEntry,
    SectionTypeDefinition,
    TemplateSectionType,
    Version,
    VisualTheme,
)


@admin.register(SectionTypeDefinition)
class SectionTypeDefinitionAdmin(admin.ModelAdmin):
    list_display = ["key", "display_name", "allow_multiple_entries", "default_converter_key"]
    list_filter = ["allow_multiple_entries"]
    search_fields = ["key", "display_name"]


@admin.register(VisualTheme)
class VisualThemeAdmin(admin.ModelAdmin):
    list_display = ["key", "display_name", "converter_set_key"]
    search_fields = ["key", "display_name"]


@admin.register(ResumeTemplate)
class ResumeTemplateAdmin(admin.ModelAdmin):
    list_display = ["key", "display_name", "family", "domain", "max_pages", "is_active"]
    list_filter = ["family", "domain", "is_active"]
    filter_horizontal = ["available_themes"]


@admin.register(TemplateSectionType)
class TemplateSectionTypeAdmin(admin.ModelAdmin):
    list_display = ["template", "section_type", "is_default", "is_required", "default_order"]
    list_filter = ["template", "is_default", "is_required"]


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "template", "visual_theme", "pages", "is_pinned", "updated_at"]
    list_filter = ["template", "visual_theme", "is_pinned"]
    search_fields = ["title", "owner__username"]
    raw_id_fields = ["owner"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["resume", "section_type", "order", "is_visible"]
    list_filter = ["section_type", "is_visible"]
    raw_id_fields = ["resume"]


@admin.register(SectionEntry)
class SectionEntryAdmin(admin.ModelAdmin):
    list_display = ["section", "order", "generation_status", "updated_at"]
    list_filter = ["generation_status"]
    raw_id_fields = ["section"]


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ["resume", "created_by", "created_at"]
    raw_id_fields = ["resume", "created_by"]
