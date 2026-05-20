from typing import Any, Dict


HEADER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "edu", "contact"],
    "additionalProperties": False,
    "properties": {
        "name": {
            "type": "string"
        },
        "edu": {
            "type": "string"
        },
        "contact": {
            "type": "object",
            "required": ["email", "phone", "linkedin", "github"],
            "additionalProperties": False,
            "properties": {
                "email": {
                    "type": "string"
                },
                "phone": {
                    "type": "string"
                },
                "linkedin": {
                    "type": "string"
                },
                "github": {
                    "type": "string"
                },
            },
        },
    },
}


EDUCATION_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["degree", "institution", "cpi", "year"],
        "additionalProperties": False,
        "properties": {
            "degree": {
                "type": "string"
            },
            "institution": {
                "type": "string"
            },
            "cpi": {
                "type": "string"
            },
            "year": {
                "type": "string"
            },
        },
    },
}


PROFESSIONAL_EXPERIENCE_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["title", "organisation", "location", "timeline", "bullets"],
        "additionalProperties": False,
        "properties": {
            "title": {
                "type": "string"
            },
            "organisation": {
                "type": "string"
            },
            "location": {
                "type": "string"
            },
            "timeline": {
                "type": "string"
            },
            "bullets": {
                "type": "array",
                "items": {
                    "type": "string"
                },
            },
        },
    },
}


KEY_PROJECT_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["title", "guide", "location", "timeline", "bullets"],
        "additionalProperties": False,
        "properties": {
            "title": {
                "type": "string"
            },
            "guide": {
                "type": "string"
            },
            "location": {
                "type": "string"
            },
            "timeline": {
                "type": "string"
            },
            "bullets": {
                "type": "array",
                "items": {
                    "type": "string"
                },
            },
        },
    },
}
RESUME_SECTION_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "header": HEADER_SCHEMA,
    "education": EDUCATION_SCHEMA,
    "professional_experience": PROFESSIONAL_EXPERIENCE_SCHEMA,
    "key_projects": KEY_PROJECT_SCHEMA,
}


def get_schema(section_type: str) -> Dict[str, Any]:
    """
    Return the JSON schema for a given resume section type.

    Example:
        get_schema("professional_experience")
    """

    if section_type not in RESUME_SECTION_SCHEMAS:
        raise ValueError(f"Unsupported resume section type: {section_type}")

    return RESUME_SECTION_SCHEMAS[section_type]


def get_supported_section_types() -> list[str]:
    """
    Return all supported resume section names.
    """

    return list(RESUME_SECTION_SCHEMAS.keys())