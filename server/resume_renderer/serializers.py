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
    pors = serializers.ListField(child=serializers.DictField(), required=False)
    scholastic_achievements = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    courses = serializers.ListField(child=serializers.DictField(), required=False)
    technical_skills = serializers.ListField(
        child=serializers.DictField(), required=False
    )
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

    def validate_pors(self, pors: list) -> None:
        if not isinstance(pors, list):
            raise serializers.ValidationError(
                "Positions of responsibility must be a list."
            )

        for idx, item in enumerate(pors):
            bullets = item.get("bullets") if isinstance(item, dict) else None
            if not isinstance(bullets, list) or not all(
                isinstance(b, str) for b in bullets
            ):
                raise serializers.ValidationError(
                    f"Positions of responsibility[{idx}].bullets must be a list of strings."
                )

    def validate_scholastic_achievements(self, achievements: list) -> None:
        if not isinstance(achievements, list):
            raise serializers.ValidationError("Scholastic achievements must be a list.")

        if not all(isinstance(a, str) for a in achievements):
            raise serializers.ValidationError(
                "All scholastic achievements must be strings."
            )

    def validate_courses(self, courses: list) -> None:
        if not isinstance(courses, list):
            raise serializers.ValidationError("Courses must be a list.")

        for idx, item in enumerate(courses):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f"Courses[{idx}] must be an object with 'category' and 'courses'."
                )
            course_list = item.get("courses")
            if not isinstance(course_list, list) or not all(
                isinstance(c, str) for c in course_list
            ):
                raise serializers.ValidationError(
                    f"Courses[{idx}].courses must be a list of strings."
                )

    def validate_technical_skills(self, skills: list) -> None:
        if not isinstance(skills, list):
            raise serializers.ValidationError("Technical skills must be a list.")

        for idx, item in enumerate(skills):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f"Technical_skills[{idx}] must be an object with 'category' and 'skills'."
                )
            skill_list = item.get("skills")
            if not isinstance(skill_list, list) or not all(
                isinstance(s, str) for s in skill_list
            ):
                raise serializers.ValidationError(
                    f"Technical_skills[{idx}].skills must be a list of strings."
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


class ResumeSectionRefineSerializer(serializers.Serializer):
    user_input = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        max_length=5000,
    )
