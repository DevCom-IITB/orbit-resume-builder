from rest_framework import serializers
from .models import Resume, Section, Version


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "section_type", "order", "content"]

    def validate_content(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("content must be a list")
        return value

    def validate_section_type(self, value):
        valid = {c[0] for c in Section.SECTION_TYPE_CHOICES}
        if value not in valid:
            raise serializers.ValidationError(f"invalid section_type: {value}")
        return value


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = ["id", "snapshot", "created_by", "created_at"]


class ResumeSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, required=False)
    versions = VersionSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = [
            "id",
            "title",
            "resume_type",
            "header_type",
            "meta",
            "is_pinned",
            "sections",
            "versions",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        sections_data = validated_data.pop("sections", [])
        owner = self.context["request"].user
        resume = Resume.objects.create(owner=owner, **validated_data)
        for idx, s in enumerate(sections_data):
            Section.objects.create(
                resume=resume,
                order=s.get("order", idx),
                section_type=s.get("section_type"),
                content=s.get("content", []),
            )
        return resume

    def update(self, instance, validated_data):
        sections_data = validated_data.pop("sections", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if sections_data is not None:
            # Replace sections for simplicity
            instance.sections.all().delete()
            for idx, s in enumerate(sections_data):
                Section.objects.create(
                    resume=instance,
                    order=s.get("order", idx),
                    section_type=s.get("section_type"),
                    content=s.get("content", []),
                )
        return instance

    def validate_title(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("title cannot be empty")
        if len(value) > 255:
            raise serializers.ValidationError("title too long")
        return value

    def validate_meta(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("meta must be an object")
        return value
