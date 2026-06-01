from pathlib import Path

from resume_renderer.services.renderer import compile_latex

from resume_renderer.schemas.converters.convert_header import convert_header
from resume_renderer.schemas.converters.convert_education import convert_education
from resume_renderer.schemas.converters.convert_experience import convert_experience
from resume_renderer.schemas.converters.convert_key_project import convert_key_project
from resume_renderer.schemas.converters.convert_technical_skills import convert_technical_skills
from resume_renderer.schemas.converters.convert_courses import convert_courses
from resume_renderer.schemas.converters.convert_pors import convert_pors
from resume_renderer.schemas.converters.convert_scholastic_achievements import (
    convert_scholastic_achievements,
)


def test_renderer_with_sample_inputs():
    sample_resume = {
        "header": {
            "name": "Kushagra Misra",
            "edu": "B.Tech. in Computer Science and Engineering",
            "contact": {
                "email": "kushagra@example.com",
                "phone": "+91 9876543210",
                "linkedin": "kushagra-misra",
                "github": "kushagramisra06",
            },
        },
        "education": [
            {
                "degree": "Bachelor of Technology in Computer Science and Engineering",
                "institution": "Indian Institute of Technology Bombay",
                "cpi": "9.22/10",
                "year": "2025 - 2029",
            }
        ],
        "professional_experience": [
            {
                "title": "Frontend Intern",
                "organization": "Awaasdhan",
                "location": "Remote",
                "timeline": "May 2025 - Jul 2025",
                "bullets": [
                    "Developed responsive website pages using React and Tailwind CSS to improve interface structure and visual consistency across key sections.",
                    "Improved frontend layouts and fixed responsiveness issues to deliver a cleaner user experience across desktop and mobile screens.",
                ],
            }
        ],
        "key_projects": [
            {
                "title": "AI Resume Builder",
                "organization": "DevCom, IIT Bombay",
                "summary": "AI-assisted resume generation platform using React, Django, Gemini API, and LaTeX.",
                "timeline": "May 2026",
                "bullets": [
                    "Built a resume builder using React, Django, Gemini API, and LaTeX to convert rough student inputs into structured resume content.",
                    "Designed schema-based JSON validation to ensure generated resume sections were compatible with the LaTeX rendering pipeline.",
                ],
            }
        ],
        "technical_skills": [
            {
                "category": "Programming",
                "skills": ["Python", "C++", "JavaScript"],
            },
            {
                "category": "Web Development",
                "skills": ["React.js", "Django", "Tailwind CSS"],
            },
            {
                "category": "Tools",
                "skills": ["Git", "GitHub", "Docker", "Figma"],
            },
        ],
        "courses": [
            {
                "category": "Computer Science",
                "courses": [
                    "Data Structures and Algorithms",
                    "Database Management Systems",
                    "Operating Systems",
                ],
            },
            {
                "category": "Mathematics",
                "courses": ["Linear Algebra", "Probability and Statistics"],
            },
        ],
        "positions_of_responsibility": [
            {
                "role": "Developer",
                "organization": "DevCom, IIT Bombay",
                "duration": "Mar 2025 - Present",
                "summary": "Contributing to student-focused digital infrastructure projects at IIT Bombay.",
                "bullets": [
                    "Developed features for an AI Resume Builder to streamline resume preparation for students applying to internships, placements, and research roles.",
                    "Contributed to the Career and Research Portal to support centralized project discovery and collaboration workflows for students and professors.",
                ],
            }
        ],
        "scholastic_achievements": [
            "Secured 99.5 percentile in JEE Main.",
            "Achieved All India Rank 3809 in JEE Advanced.",
            "Scored 92.3% in Class 12 CBSE board examinations.",
        ],
    }

    latex_parts = []

    latex_parts.append(convert_header(sample_resume["header"]))
    latex_parts.append(convert_education(sample_resume["education"]))
    latex_parts.append(convert_experience(sample_resume["professional_experience"]))
    latex_parts.append(convert_key_project(sample_resume["key_projects"]))
    latex_parts.append(convert_technical_skills(sample_resume["technical_skills"]))
    latex_parts.append(convert_courses(sample_resume["courses"]))
    latex_parts.append(convert_pors(sample_resume["positions_of_responsibility"]))
    latex_parts.append(
        convert_scholastic_achievements(sample_resume["scholastic_achievements"])
    )

    latex_content = "\n\n".join(latex_parts)

    pdf_bytes = compile_latex(latex_content)

    output_path = Path("resume_renderer/tests/test_resume.pdf")
    output_path.write_bytes(pdf_bytes)

    assert output_path.exists()
    assert output_path.stat().st_size > 0