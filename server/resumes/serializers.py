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
        ]


class SectionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionEntry
        fields = [
            "id",
            "order",
            "raw_input",
            "content",
            "improvement_suggestion",
            "improvement_example",
            "generation_status",
        ]
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
    visual_theme = serializers.SerializerMethodField()
    sections = SectionSerializer(many=True, read_only=True)
    versions = VersionSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = [
            "id",
            "title",
            "template",
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
        return {"key": obj.template.key, "display_name": obj.template.display_name}

    def get_visual_theme(self, obj):
        return {"key": obj.visual_theme.key, "display_name": obj.visual_theme.display_name}


class ResumeCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    template_key = serializers.CharField(max_length=64)
    visual_theme_key = serializers.CharField(max_length=64)
    pages = serializers.IntegerField(default=1, min_value=1, max_value=2)
    config_override = serializers.JSONField(default=dict)
    import_content = serializers.CharField(required=False, allow_blank=True, default="")

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
        parsed_data = validated_data.get("_parsed_data")

        resume = Resume.objects.create(
            owner=owner,
            title=validated_data["title"],
            template=template,
            visual_theme=visual_theme,
            pages=validated_data["pages"],
            config_override=validated_data["config_override"],
        )

        if parsed_data and isinstance(parsed_data, dict):
            # Populate sections and entries from imported structured JSON
            for tst in TemplateSectionType.objects.filter(template=template).order_by("default_order"):
                st_key = tst.section_type.key
                items = parsed_data.get(st_key)
                has_content = False
                if not tst.section_type.allow_multiple_entries:
                    has_content = isinstance(items, dict) and any(items.values())
                else:
                    has_content = isinstance(items, list) and len(items) > 0

                # Only include non-default sections if they have imported content
                if not tst.is_default and not has_content:
                    continue

                section = Section.objects.create(
                    resume=resume,
                    section_type=tst.section_type,
                    order=tst.default_order,
                    is_visible=True,
                )

                if not tst.section_type.allow_multiple_entries:
                    if has_content and isinstance(items, dict):
                        raw_input = f"{items.get('name', '')} ({items.get('degree', '')})".strip()
                        SectionEntry.objects.create(
                            section=section,
                            order=0,
                            raw_input=raw_input,
                            content=items,
                            generation_status="done",
                        )
                    else:
                        SectionEntry.objects.create(
                            section=section,
                            order=0,
                            raw_input="",
                            content=None,
                            generation_status="pending",
                        )
                else:
                    if has_content and isinstance(items, list):
                        for idx, item in enumerate(items):
                            if not isinstance(item, dict):
                                continue
                            raw_input = ""
                            if "title" in item:
                                org = item.get("organization", "")
                                raw_input = f"{item['title']} - {org}" if org else item["title"]
                            elif "role" in item:
                                org = item.get("organization", "")
                                raw_input = f"{item['role']} - {org}" if org else item["role"]
                            elif "examination" in item:
                                inst = item.get("institute", "")
                                raw_input = f"{item['examination']} ({inst})" if inst else item["examination"]
                            elif "category" in item:
                                skills = item.get("skills") or item.get("courses") or []
                                raw_input = f"{item['category']}: {', '.join(skills)}"
                            elif "text" in item:
                                raw_input = item["text"]

                            SectionEntry.objects.create(
                                section=section,
                                order=idx,
                                raw_input=raw_input,
                                content=item,
                                generation_status="done",
                            )
        else:
            # Auto-create default sections from the template manifest (blank resume)
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
