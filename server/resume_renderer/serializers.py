import re

from rest_framework import serializers

BAD_PATTERNS = [
    r"\\renewcommand",
    r"\\def",
    r"\\newcommand",
    r"\\let",
    r"\\input",
    r"\\include",
    r"\\includeonly",
    r"\\catcode",
    r"\\openin",
    r"\\openout",
    r"\\write",
    r"\\write18",
    r"\\read",
    r"\\loop",
    r"\\repeat",
    r"\\csname",
    r"\\expandafter",
    r"\\usepackage",
]

COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in BAD_PATTERNS]


class LatexRenderSerializer(serializers.Serializer):
    """Serializer for validating LaTeX input for resume rendering."""

    header = serializers.DictField(required=False)
    education = serializers.ListField(child=serializers.DictField(), required=False)
    experience = serializers.ListField(child=serializers.DictField(), required=False)
    key_projects = serializers.ListField(child=serializers.DictField(), required=False)
    config = serializers.DictField(required=False)

    def validate_header(self, header: dict) -> None:
        if not isinstance(header, dict):
            raise serializers.ValidationError("Header must be a dictionary.")

    def validate_education(self, education: list) -> None:
        if not isinstance(education, list):
            raise serializers.ValidationError("Education must be a list.")

    def validate_experience(self, experience: list) -> None:
        if not isinstance(experience, list):
            raise serializers.ValidationError("Experience must be a list.")

        for idx, item in enumerate(experience):
            bullets = item.get("bullets") if isinstance(item, dict) else None
            if not isinstance(bullets, list) or not all(
                isinstance(b, str) for b in bullets
            ):
                raise serializers.ValidationError(
                    f"Experience[{idx}].bullets must be a list of strings."
                )

    def validate_key_projects(self, key_projects: list) -> None:
        if not isinstance(key_projects, list):
            raise serializers.ValidationError("Key projects must be a list.")

        for idx, item in enumerate(key_projects):
            bullets = item.get("bullets") if isinstance(item, dict) else None
            if not isinstance(bullets, list) or not all(
                isinstance(b, str) for b in bullets
            ):
                raise serializers.ValidationError(
                    f"Key projects[{idx}].bullets must be a list of strings."
                )

    def validate(self, attrs):
        self._validate_no_latex(attrs)
        return attrs

    def _validate_no_latex(self, data):
        if isinstance(data, dict):
            for value in data.values():
                self._validate_no_latex(value)
            return
        if isinstance(data, list):
            for item in data:
                self._validate_no_latex(item)
            return
        if isinstance(data, str):
            for pattern in COMPILED_PATTERNS:
                if pattern.search(data):
                    raise serializers.ValidationError("LaTeX commands are not allowed.")
