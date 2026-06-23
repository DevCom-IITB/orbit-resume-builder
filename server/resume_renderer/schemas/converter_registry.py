from .converters.convert_courses import convert_courses
from .converters.convert_education import convert_education
from .converters.convert_experience import convert_experience
from .converters.convert_header import convert_header
from .converters.convert_key_project import convert_key_project
from .converters.convert_pors import convert_pors
from .converters.convert_scholastic_achievements import convert_scholastic_achievements
from .converters.convert_technical_skills import convert_technical_skills

CONVERTER_SETS = {
    "iitb-classic": {
        "header": convert_header,
        "education": convert_education,
        "scholastic_achievements": convert_scholastic_achievements,
        "courses": convert_courses,
        "professional_experience": convert_experience,
        "key_projects": convert_key_project,
        "positions_of_responsibility": convert_pors,
        "technical_skills": convert_technical_skills,
    },
    "external-standard": {
        "header": convert_header,
        "education": convert_education,
        "scholastic_achievements": convert_scholastic_achievements,
        "courses": convert_courses,
        "professional_experience": convert_experience,
        "key_projects": convert_key_project,
        "positions_of_responsibility": convert_pors,
        "technical_skills": convert_technical_skills,
    },
}


def get_converter(converter_set_key: str, section_type_key: str):
    try:
        return CONVERTER_SETS[converter_set_key][section_type_key]
    except KeyError:
        raise KeyError(
            f"No converter for set='{converter_set_key}', section='{section_type_key}'"
        )
