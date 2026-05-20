"""
Stateless prompt builder for resume section refinement.

Every LLM call must include:
1. Base system prompt
2. Section-specific instructions
3. Exact JSON output structure
4. User input

This is stateless:
The LLM must not rely on previous messages or memory.
"""

import json
from typing import Any, Dict

from resume_renderer.JSONSchema.jsonschema import get_schema


BASE_SYSTEM_PROMPT = """
You are an expert resume refinement assistant for IIT Bombay students.

Your task is to convert rough, informal student-written resume input into polished,
concise, professional, resume-ready JSON.

General rules:
1. Return only valid JSON.
2. Do not include markdown, code fences, comments, explanation, or extra text.
3. Do not invent facts, numbers, dates, organizations, technologies, awards, roles, links, scores, or results.
4. Preserve all factual information explicitly provided by the user.
5. Improve grammar, clarity, structure, and professional tone.
6. Use concise, high-impact resume language suitable for IIT Bombay-style technical resumes.
7. Use strong action verbs where appropriate.
8. Do not output raw LaTeX commands.
9. Do not use LaTeX symbols or special formatting.
10. If a required field is missing from the user input, return an empty string "".
11. If a required list field is missing, return an empty list [].
12. Output must strictly match the provided JSON schema.
13. Do not add extra keys outside the schema.
14. Keep spelling consistent with the schema field names exactly.
15. The response should be directly usable by a JSON-to-LaTeX converter.
"""


SECTION_INSTRUCTIONS: Dict[str, str] = {
    "header": """
Section-specific instructions for HEADER:

Expected purpose:
- Extract the student's name, education line, and contact details.

Rules:
1. Use only information explicitly provided by the user.
2. Do not invent email, phone number, LinkedIn, or GitHub.
3. The "edu" field should be a short education line, for example:
   "B.Tech. in Electrical Engineering"
   "B.S. in Chemistry"
   "Dual Degree in Mechanical Engineering"
4. For LinkedIn, return only the username or profile slug if possible.
   Example: "kushagra-misra", not "https://linkedin.com/in/kushagra-misra".
5. For GitHub, return only the GitHub username if possible.
   Example: "kushagramisra06", not "https://github.com/kushagramisra06".
6. If any contact field is missing, keep it as an empty string.
7. Do not include IIT Bombay in the "edu" field unless the user explicitly wrote it.
""",

    "education": """
Section-specific instructions for EDUCATION:

Expected purpose:
- Extract academic education entries only.

Schema meaning:
- "degree": degree or qualification name.
- "institution": school, college, or university name.
- "cpi": CPI, CGPA, percentage, or score.
- "year": academic year, graduation year, or duration.

Rules:
1. Return a JSON array of education entries.
2. Preserve degree, institution, CPI/percentage, and year exactly as provided.
3. Do not invent CPI, CGPA, percentage, year, branch, or institution.
4. Expand abbreviations only when obvious.
   Example: "IITB" can become "Indian Institute of Technology Bombay".
5. Keep scores as strings.
   Example: "9.22/10", "92.3%", "96.6%".
6. If the user gives multiple education entries, return all of them.
7. If a field is missing, use an empty string.
8. Do not create bullet points for education.
""",

    "professional_experience": """
Section-specific instructions for PROFESSIONAL EXPERIENCE:

Expected purpose:
- Convert internships, jobs, research internships, industrial roles, startup work,
  lab work, and professional projects into polished resume entries.

Schema meaning:
- "title": role or project title.
- "organisation": company, lab, institute, professor, startup, club, or team name.
- "location": city, institute, remote, or empty string.
- "timeline": duration such as "May 2025 - Jul 2025", "Summer '24", or "Ongoing".
- "bullets": polished resume bullet points.

Rules:
1. Return a JSON array of experience entries.
2. Use the exact key "organisation", not "organization".
3. Write bullets in IIT Bombay resume style: concise, technical, impact-focused.
4. Each bullet should usually be 18-30 words.
5. Each bullet should be long enough to avoid excessive whitespace at the end of a resume line.
6. Do not make bullets artificially long by adding fake details.
7. Use strong action verbs such as:
   Developed, Designed, Built, Implemented, Optimized, Automated, Analyzed,
   Researched, Collaborated, Coordinated, Led, Executed, Assisted.
8. Preserve metrics if provided.
   Example: "2 million students", "1500+ schools", "60% profit", "5 member team".
9. Do not invent metrics, impact, scale, team size, location, company description, or tools.
10. If tools/technologies are mentioned, naturally include them in bullets.
11. Avoid weak phrases like:
   "worked on", "helped with", "was responsible for"
   unless rewritten professionally.
12. Do not create more than 3-4 bullets for one entry unless the input clearly contains many separate contributions.
13. If the input is very short, create 1-2 strong but factual bullets.
14. Keep the tone professional, not exaggerated.
""",

    "key_projects": """
Section-specific instructions for KEY PROJECTS:

Expected purpose:
- Convert technical, academic, research, self, course, club, and competition projects
  into polished resume entries.

Schema meaning:
- "title": project name.
- "guide": professor, mentor, club, course, lab, or project context.
- "location": institute, organization, remote, or empty string.
- "timeline": project duration such as "Jan 2024 - Apr 2024", "Summer '24", or "Ongoing".
- "bullets": polished project bullet points.

Rules:
1. Return a JSON array of project entries.
2. Use this section for projects, not internships or formal job roles.
3. If a professor, guide, mentor, course, club, or lab is mentioned, put it in "guide".
4. If no guide or context is mentioned, keep "guide" as an empty string.
5. Write bullets in IIT Bombay technical resume style.
6. Each bullet should usually be 18-30 words.
7. Each bullet should be long enough to avoid excessive whitespace at the end of a resume line.
8. Do not make bullets artificially long by adding fake details.
9. Focus on:
   - problem solved
   - implementation
   - algorithms/models/tools used
   - experiments/simulation/testing
   - performance/result only if provided
10. Use strong technical action verbs such as:
    Built, Developed, Implemented, Designed, Simulated, Trained, Evaluated,
    Integrated, Optimized, Validated, Analyzed, Deployed.
11. Preserve technical terms exactly where important.
    Example: PPO, DQN, LSTM, ROS, VHDL, OpenFOAM, NumPy, Databricks.
12. Do not invent technologies, GitHub links, demo links, results, or metrics.
13. Do not add a technology just because it sounds likely.
14. If the input is short, generate fewer but accurate bullets.
"""
}


def build_resume_prompt(section_type: str, user_input: str) -> str:
    """
    Build a complete stateless prompt for one resume section.

    Args:
        section_type:
            One of:
            - "header"
            - "education"
            - "professional_experience"
            - "key_projects"

        user_input:
            Rough text entered by the user.

    Returns:
        A complete prompt string containing:
        - base system instructions
        - section-specific instructions
        - expected JSON schema
        - user input
    """

    schema: Dict[str, Any] = get_schema(section_type)
    section_instruction = SECTION_INSTRUCTIONS.get(section_type)

    if section_instruction is None:
        raise ValueError(f"No prompt instructions found for section type: {section_type}")

    schema_text = json.dumps(schema, indent=2)

    return f"""
{BASE_SYSTEM_PROMPT}

{section_instruction}

Section type:
{section_type}

Expected JSON schema:
{schema_text}

User input:
{user_input}

Return only valid JSON matching the expected schema.
"""
