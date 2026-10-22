from rest_framework import serializers

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


class VisualThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisualTheme
        fields = ["key", "display_name", "compatible_families"]


class SectionTypeDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionTypeDefinition
        fields = ["key", "display_name", "allow_multiple_entries", "entry_hint_text"]


class ResumeTemplateSerializer(serializers.ModelSerializer):
    available_themes = VisualThemeSerializer(many=True, read_only=True)
    default_theme_key = serializers.SerializerMethodField()
    fonts = serializers.SerializerMethodField()
    font_default = serializers.SerializerMethodField()
    accents = serializers.SerializerMethodField()
    accent_default = serializers.SerializerMethodField()
    line_spacings = serializers.SerializerMethodField()
    line_spacing_default = serializers.SerializerMethodField()
    word_spacings = serializers.SerializerMethodField()
    word_spacing_default = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    class Meta:
        model = ResumeTemplate
        fields = [
            "key",
            "display_name",
            "family",
            "domain",
            "max_pages",
            "template_config",
            "available_themes",
            "default_theme_key",
            "fonts",
            "font_default",
            "accents",
            "accent_default",
            "line_spacings",
            "line_spacing_default",
            "word_spacings",
            "word_spacing_default",
            "sections",
        ]

    def _get_opts(self, obj):
        if not hasattr(obj, "_cached_style_opts"):
            from resume_renderer.services.styling import get_style_options
            obj._cached_style_opts = get_style_options(obj)
        return obj._cached_style_opts

    def get_default_theme_key(self, obj):
        first_theme = obj.available_themes.first()
        return first_theme.key if first_theme else None

    def get_fonts(self, obj):
        return self._get_opts(obj)["fonts"]

    def get_font_default(self, obj):
        return self._get_opts(obj)["font_default"]

    def get_accents(self, obj):
        return self._get_opts(obj)["accents"]

    def get_accent_default(self, obj):
        return self._get_opts(obj)["accent_default"]

    def get_line_spacings(self, obj):
        return self._get_opts(obj)["line_spacings"]

    def get_line_spacing_default(self, obj):
        return self._get_opts(obj)["line_spacing_default"]

    def get_word_spacings(self, obj):
        return self._get_opts(obj)["word_spacings"]

    def get_word_spacing_default(self, obj):
        return self._get_opts(obj)["word_spacing_default"]

    def get_sections(self, obj):
        manifest = obj.section_manifest.select_related("section_type").order_by("default_order")
        return [
            {
                "key": tst.section_type.key,
                "display_name": tst.section_type.display_name,
                "is_default": tst.is_default,
                "is_required": tst.is_required,
                "default_order": tst.default_order,
            }
            for tst in manifest
        ]


class SectionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionEntry
        fields = ["id", "order", "raw_input", "content", "generation_status"]
        read_only_fields = ["id", "generation_status"]


class SectionSerializer(serializers.ModelSerializer):
    section_type = SectionTypeDefinitionSerializer(read_only=True)
    entries = SectionEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = ["id", "section_type", "order", "is_visible", "entries"]
        read_only_fields = ["id", "section_type"]


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = ["id", "snapshot", "created_by", "created_at"]


class ResumeListSerializer(serializers.ModelSerializer):
    template = serializers.SerializerMethodField()
    visual_theme = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            "id",
            "title",
            "template",
            "visual_theme",
            "pages",
            "is_pinned",
            "created_at",
            "updated_at",
        ]

    def get_template(self, obj):
        return {"key": obj.template.key, "display_name": obj.template.display_name}

    def get_visual_theme(self, obj):
        return {"key": obj.visual_theme.key, "display_name": obj.visual_theme.display_name}


class ResumeDetailSerializer(serializers.ModelSerializer):
    template = serializers.SerializerMethodField()
    template_key = serializers.SerializerMethodField()
    visual_theme = serializers.SerializerMethodField()
    sections = SectionSerializer(many=True, read_only=True)
    versions = VersionSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = [
            "id",
            "title",
            "template",
            "template_key",
            "visual_theme",
            "pages",
            "config_override",
            "is_pinned",
            "sections",
            "versions",
            "created_at",
            "updated_at",
        ]

    def get_template(self, obj):
        from resume_renderer.services.styling import get_style_options
        if not obj.template:
            return {
                "key": "iitb-general",
                "display_name": "IIT Bombay",
                "font_default": "lmodern",
                "accent_default": "#4B41C8",
            }
        opts = get_style_options(obj.template)
        return {
            "key": obj.template.key,
            "display_name": obj.template.display_name,
            "font_default": opts["font_default"],
            "accent_default": opts["accent_default"],
        }

    def get_template_key(self, obj):
        if not obj.template:
            return "iitb-general"
        return obj.template.key

    def get_visual_theme(self, obj):
        if not obj.visual_theme:
            return {"key": "iitb-classic", "display_name": "Classic (IIT Bombay)"}
        return {"key": obj.visual_theme.key, "display_name": obj.visual_theme.display_name}


class ResumeCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    template_key = serializers.CharField(max_length=64)
    visual_theme_key = serializers.CharField(max_length=64)
    pages = serializers.IntegerField(default=1, min_value=1, max_value=2)
    config_override = serializers.JSONField(default=dict)

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("title cannot be empty")
        return value.strip()

    def validate(self, data):
        try:
            template = ResumeTemplate.objects.get(key=data["template_key"], is_active=True)
        except ResumeTemplate.DoesNotExist:
            raise serializers.ValidationError({"template_key": "Template not found."})

        try:
            theme = VisualTheme.objects.get(key=data["visual_theme_key"])
        except VisualTheme.DoesNotExist:
            raise serializers.ValidationError({"visual_theme_key": "Visual theme not found."})

        if not template.available_themes.filter(key=theme.key).exists():
            raise serializers.ValidationError(
                {"visual_theme_key": "Theme is not compatible with the selected template."}
            )

        if template.max_pages and data["pages"] > template.max_pages:
            raise serializers.ValidationError(
                {"pages": f"Template allows at most {template.max_pages} page(s)."}
            )

        data["template"] = template
        data["visual_theme"] = theme
        return data

    def create(self, validated_data):
        owner = self.context["request"].user
        template = validated_data["template"]
        visual_theme = validated_data["visual_theme"]

        resume = Resume.objects.create(
            owner=owner,
            title=validated_data["title"],
            template=template,
            visual_theme=visual_theme,
            pages=validated_data["pages"],
            config_override=validated_data["config_override"],
        )

        # Auto-create default sections from the template manifest
        for tst in TemplateSectionType.objects.filter(
            template=template, is_default=True
        ).order_by("default_order"):
            section = Section.objects.create(
                resume=resume,
                section_type=tst.section_type,
                order=tst.default_order,
                is_visible=True,
            )
            # Create one empty entry for singleton sections (header)
            if not tst.section_type.allow_multiple_entries:
                SectionEntry.objects.create(
                    section=section,
                    order=0,
                    raw_input="",
                    content=None,
                    generation_status="pending",
                )

        return resume


class ResumePatchSerializer(serializers.ModelSerializer):
    visual_theme_key = serializers.CharField(max_length=64, required=False, write_only=True)

    class Meta:
        model = Resume
        fields = ["title", "pages", "config_override", "is_pinned", "visual_theme_key"]

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("title cannot be empty")
        return value.strip()

    def validate(self, data):
        if "visual_theme_key" in data:
            try:
                theme = VisualTheme.objects.get(key=data.pop("visual_theme_key"))
            except VisualTheme.DoesNotExist:
                raise serializers.ValidationError({"visual_theme_key": "Visual theme not found."})

            if not self.instance.template.available_themes.filter(key=theme.key).exists():
                raise serializers.ValidationError(
                    {"visual_theme_key": "Theme is not compatible with this resume's template."}
                )
            data["visual_theme"] = theme

        if "pages" in data and self.instance.template.max_pages:
            if data["pages"] > self.instance.template.max_pages:
                raise serializers.ValidationError(
                    {"pages": f"Template allows at most {self.instance.template.max_pages} page(s)."}
                )
        return data

    def update(self, instance, validated_data):
        if "visual_theme" in validated_data and validated_data["visual_theme"] != instance.visual_theme:
            instance.latex_cache_valid = False
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance


class StylePatchSerializer(serializers.Serializer):
    """Lightweight schema hint for the style PATCH endpoint.
    Real validation (whitelist check, WCAG, allowed spacing) is performed in styling.validate_style_patch.
    """
    font = serializers.CharField(max_length=32, required=False)
    accent = serializers.CharField(max_length=7, required=False)
    line_spacing = serializers.CharField(max_length=16, required=False)
    word_spacing = serializers.CharField(max_length=16, required=False)

    def validate(self, data):
        if not data:
            raise serializers.ValidationError(
                "Provide at least one of 'font', 'accent', 'line_spacing', or 'word_spacing'."
            )
        return data


class ResumeTemplateSwitchSerializer(serializers.Serializer):
    template_key = serializers.CharField(max_length=64)
    theme_key = serializers.CharField(max_length=64, required=False, allow_null=True)
    dry_run = serializers.BooleanField(default=False)


