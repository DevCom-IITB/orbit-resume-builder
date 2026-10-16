"""
Stateless prompt builder for resume section refinement.

Every LLM call must include:
1. Base system prompt
2. Section-specific instructions
3. Exact JSON output structure
4. User input

This is stateless:
The LLM must not rely on previous messages or memory.

Important:
The prompts must match the JSON-to-LaTeX converter field names exactly.
"""

import json
from typing import Any, Dict, List, Optional

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
10. If a required string field is missing from the user input, return an empty string "".
11. If a required list field is missing, return an empty list [].
12. Output must strictly match the provided JSON schema.
13. Do not add extra keys outside the schema.
14. Keep spelling consistent with the schema field names exactly.
15. The response should be directly usable by a JSON-to-LaTeX converter.
Line-length rules for all bullet points:
The LaTeX text column is approximately 95 characters wide.
Each bullet must land cleanly on either 1 line (80–95 chars) or 2 lines (160–190 chars).
Bullets between 96–155 chars are forbidden — they create an ugly trailing half-line.
Before finalizing each bullet, mentally count its length and adjust accordingly.
To shorten: remove filler words, combine clauses, use abbreviations where natural.
To lengthen: add the method used, tool name, metric context, or outcome — only from provided facts.
"""


SECTION_INSTRUCTIONS: Dict[str, str] = {
    "header": """
Section-specific instructions for HEADER:

Expected purpose:
- Extract the student's personal and academic details for an IITB-format resume header.

Expected output:
- Return a JSON object.
- The object must contain:
  - "name"
  - "roll_no"
  - "department"
  - "degree"
  - "institution"
  - "gender"
  - "email"
  - "phone"

Schema meaning:
- "name": full name of the student.
- "roll_no": institute roll number or student ID.
- "department": department or programme name, e.g. "Department of Aerospace Engineering".
- "degree": degree programme, e.g. "B.Tech.", "Dual Degree (B.Tech. + M.Tech.)".
- "institution": institute name, default "Indian Institute of Technology Bombay".
- "gender": student's gender, e.g. "Male", "Female".
- "email": official email address.
- "phone": phone number with country code if provided.

Rules:
1. Use only information explicitly provided by the user.
2. Do not invent roll number, email, phone, department, or degree.
3. If "institution" is not provided, default to "Indian Institute of Technology Bombay".
4. If any field is missing, return an empty string for that field.
5. Do not create bullet points for this section.
""",
    "education": """
Section-specific instructions for EDUCATION:

Expected purpose:
- Extract academic education entries in IITB tabular format.

Expected output:
- Return a JSON array.
- Each item must contain:
  - "examination"
  - "university"
  - "institute"
  - "year"
  - "cpi"
- Each item may optionally contain:
  - "note"

Schema meaning:
- "examination": exam or degree name, e.g. "B.Tech.", "HSC (Class XII)", "SSC (Class X)".
- "university": university or board name, e.g. "IIT Bombay", "CBSE", "Maharashtra Board".
- "institute": school or college name where studied.
- "year": graduation year or exam year, e.g. "2027 (Expected)", "2022".
- "cpi": CPI, CGPA, percentage, or score as a string, e.g. "9.22/10", "92.3%".
- "note": optional note such as "* till 4th semester".

Rules:
1. Return a JSON array of education entries.
2. For IIT Bombay entries: "university" should be "IIT Bombay", "institute" should be "IIT Bombay".
3. For school entries: "university" is the board (CBSE/Maharashtra), "institute" is the school name.
4. Preserve scores exactly as provided — do not convert percentages to CPI or vice versa.
5. If the user gives multiple education entries, return all of them in reverse chronological order.
6. If a field is missing, use an empty string.
7. Do not create bullet points for education.
8. Omit "note" if there is nothing to note.
""",
    "professional_experience": """
Section-specific instructions for PROFESSIONAL EXPERIENCE:

Expected purpose:
- Convert internships, jobs, research internships, industrial roles, startup work,
  lab work, and professional roles into polished resume entries.

Expected output:
- Return a JSON array.
- Each item must contain:
  - "title"
  - "organization"
  - "location"
  - "timeline"
  - "summary"
  - "bullets"

Schema meaning:
- "title": role title or position name.
- "organization": company, lab, institute, professor, startup, club, or team name.
- "location": city, institute, remote, or empty string.
- "timeline": duration such as "May 2025 - Jul 2025", "Summer 2025", or "Ongoing".
- "summary": one short italicised context line about the role, company, or project scope.
- "bullets": polished resume bullet points.

Rules:
1. Return a JSON array of experience entries.
2. Use the exact key "organization", not "organisation".
3. Write a concise one-line "summary" describing the role or company context. Keep it factual.
4. Use this section for internships, jobs, research internships, industrial work, and professional roles.
4. Write bullets in IIT Bombay resume style: concise, technical, impact-focused.
5. Each bullet should usually be 15-35 words.
6. Each bullet should be long enough to avoid excessive whitespace at the end of a resume line.
7. Do not make bullets artificially long by adding fake details.
8. Use strong action verbs such as:
   Developed, Designed, Built, Implemented, Improved, Analyzed,
   Researched, Collaborated, Coordinated, Led, Executed, Assisted.
9. Preserve metrics if provided.
   Example: "2 million students", "1500+ schools", "60% profit", "5 member team".
10. Do not invent metrics, impact, scale, team size, location, company description, or tools.
11. If tools or technologies are mentioned, naturally include them in bullets.
12. Avoid weak phrases like:
   "worked on", "helped with", "was responsible for"
   unless rewritten professionally.
13. Do not create more than 3-4 bullets for one entry unless the input clearly contains many separate contributions.
14. If the input is very short, create 1-2 strong but factual bullets.
15. Keep the tone professional, not exaggerated.
16. Do not use words like deployed, optimized, automated, scaled, integrated, accessibility, state management, performance, or production unless the user explicitly mentions them.
17. If the input is vague, improve language but keep the bullet general and factual.
18. Prefer safe verbs like developed, created, improved, redesigned, assisted, collaborated, and contributed when the user gives limited details.
19. Do not convert a simple frontend task into advanced engineering claims.
""",
    "key_projects": """
Section-specific instructions for KEY PROJECTS:

Expected purpose:
- Convert technical, academic, research, self, course, club, and competition projects into polished resume entries.

Expected output:
- Return a JSON array.
- Each item must contain:
  - "title"
  - "organization"
  - "summary"
  - "timeline"
  - "bullets"

Schema meaning:
- "title": project name.
- "organization": professor, mentor, course, club, lab, institute, company, or self-project context.
- "summary": short one-line context or description of the project.
- "timeline": project duration such as "Jan 2024 - Apr 2024", "Summer 2025", or "Ongoing".
- "bullets": polished project bullet points.

Rules:
1. Return a JSON array of project entries.
2. Use this section for projects, not internships or formal job roles.
3. Use the exact key "organization", not "organisation".
4. If a professor, guide, mentor, course, club, or lab is mentioned, put it in "organization".
5. If no organization or context is mentioned, keep "organization" as an empty string.
6. Generate a concise "summary" only from facts provided by the user.
7. If summary information is missing, keep "summary" as an empty string or create a very general factual summary using only the provided information.
8. Do not invent project context, organization, mentor, technologies, links, results, or metrics.
9. Write bullets in IIT Bombay technical resume style.
10. Each bullet should usually be 15-35 words.
11. Each bullet should be long enough to avoid excessive whitespace at the end of a resume line.
12. Do not make bullets artificially long by adding fake details.
13. Focus on:
   - problem solved
   - implementation
   - algorithms, models, or tools used
   - experiments, simulation, testing, or validation
   - outcome only if provided
14. Use strong technical action verbs such as:
   Built, Developed, Implemented, Designed, Simulated, Trained, Evaluated,
   Integrated, Optimized, Validated, Analyzed.
15. Preserve technical terms exactly where important.
   Example: PPO, DQN, LSTM, ROS, VHDL, OpenFOAM, NumPy, Databricks.
16. Do not add a technology just because it sounds likely.
17. If the input is short, generate fewer but accurate bullets.
""",
    "technical_skills": """
Section-specific instructions for TECHNICAL SKILLS:

Expected purpose:
- Convert rough skill input into clean categorized technical skills.

Expected output:
- Return a JSON array.
- Each item must contain:
  - "category"
  - "skills"

Schema meaning:
- "category": broad technical category such as Programming, Web Development, Databases, Tools, AI and ML, Design, or Core Engineering.
- "skills": list of individual skills in that category.

Rules:
1. Return only a JSON array of skill category objects.
2. Do not create bullet points.
3. Do not invent skills.
4. Correct obvious spelling mistakes.
5. Standardize skill names.
   Example: "js" becomes "JavaScript", "py" becomes "Python", "reactjs" becomes "React.js".
6. Group skills into meaningful categories.
7. Keep category names concise and professional.
8. If a category has no skills, do not include that category.
9. Do not include soft skills unless explicitly asked and unless the schema supports them.
10. Preserve all technical skills explicitly provided by the user.
11. Do not add technologies just because they commonly go together.
12. Do not duplicate skills across multiple categories.
""",
    "courses": """
Section-specific instructions for COURSES UNDERTAKEN:

Expected purpose:
- Convert rough course input into categorized academic coursework.

Expected output:
- Return a JSON array.
- Each item must contain:
  - "category"
  - "courses"
- Each item may optionally contain:
  - "note"

Schema meaning:
- "category": academic area such as Computer Science, Mathematics, AI and Data Science, Electrical Engineering, Mechanical Engineering, Economics, or Core Courses.
- "courses": list of course names in that category.
- "note": optional note, only if the user explicitly provides one.

Rules:
1. Return only a JSON array of course category objects.
2. Do not create bullet points.
3. Do not invent courses.
4. Preserve course names explicitly provided by the user.
5. Standardize obvious abbreviations only when clear.
   Example: "DSA" can become "Data Structures and Algorithms".
6. Group courses into sensible academic categories.
7. If the user provides a note such as "to be completed by Nov 2025", put it in the "note" field.
8. If no note is provided, omit the "note" field unless the schema explicitly requires it.
9. Do not add grades, credits, professors, or course codes unless explicitly given.
10. Keep course names concise and resume-ready.
""",
    "positions_of_responsibility": """
Section-specific instructions for POSITIONS OF RESPONSIBILITY:

Expected purpose:
- Convert leadership roles, club roles, festival roles, coordinator roles, team roles,
  and student body positions into polished resume entries.

Expected output:
- Return a JSON array.
- Each item must contain:
  - "role"
  - "organization"
  - "duration"
  - "summary"
  - "bullets"

Schema meaning:
- "role": title of the responsibility position.
- "organization": club, body, festival, department, team, or institute organization.
- "duration": time period such as "Mar '25 - Present".
- "summary": one short context line about the role or organization.
- "bullets": polished responsibility bullet points.

Rules:
1. Return a JSON array of PoR entries.
2. Use the exact key "organization", not "organisation".
3. Use this section for leadership, responsibility, coordination, and organizational roles.
4. Do not use this section for internships or technical projects.
5. Focus on ownership, coordination, execution, leadership, communication, event management, operations, and team contribution.
6. Preserve numbers and scale only if provided.
   Example: "10,000+ students", "300+ professors", "40+ member team".
7. Do not invent team size, budget, footfall, event scale, institute impact, or metrics.
8. Write bullets in IIT Bombay resume style.
9. Each bullet should usually be 15-35 words.
10. If the user input is short, generate 1-2 factual bullets.
11. If the user gives role context, convert it into a concise "summary".
12. If summary information is missing, keep "summary" as an empty string.
13. Use strong action verbs such as Led, Coordinated, Managed, Organized, Executed, Developed, Represented, Handled, Supervised, Collaborated.
14. Do not exaggerate responsibility level beyond what the user provided.
""",
    "scholastic_achievements": """
Section-specific instructions for SCHOLASTIC ACHIEVEMENTS:

Expected purpose:
- Convert academic achievements, ranks, scholarships, exam scores, awards, and recognitions into polished resume achievement entries.

Expected output:
- Return a JSON array of objects.
- Each object must contain:
  - "text"
- Each object may optionally contain:
  - "year"

Schema meaning:
- "text": the achievement statement, concise and resume-ready.
- "year": the year of the achievement if mentioned, e.g. "2024". Omit if not provided.

Rules:
1. Return only a JSON array of objects with "text" and optional "year".
2. Do not return plain strings.
3. Preserve ranks, scores, percentiles, scholarship names, and awarding bodies exactly as provided.
4. Do not invent ranks, awards, scores, percentiles, years, or institutions.
5. Keep each "text" concise, factual, and resume-ready.
6. Use strong but not exaggerated wording.
7. If the user gives multiple achievements, return each as a separate object.
8. Do not add bullet symbols; the LaTeX converter will add bullets.
9. Do not convert scores or percentages into another format.
10. If a year is clearly associated with the achievement, extract it into the "year" field.
""",
}


def _format_retrieved_context(retrieved_context: Optional[List[Dict[str, Any]]]) -> str:
    """
    Serialize RAG-retrieved reference chunks into a prompt block.

    Framed explicitly as STYLE/STRUCTURE examples from other students'
    resumes — not the user's own facts. Critical: without this framing the
    LLM can bleed facts/numbers/tools from someone else's resume into the
    user's output, which is a fabrication risk on top of BASE_SYSTEM_PROMPT's
    "do not invent facts" rule (those reference chunks ARE facts, just not
    the user's).
    """
    if not retrieved_context:
        return ""

    lines = [
        "Retrieved reference examples (senior resumes, same section type):",
        "These illustrate STYLE, structure, phrasing, and bullet quality only.",
        "Do NOT copy facts, numbers, tools, organizations, or claims from these",
        "examples into the output. Only the user's own input below is the",
        "source of truth for what actually happened.",
        "",
    ]
    for i, item in enumerate(retrieved_context, start=1):
        entry_title = item.get("entry_title", "")
        chunk = item.get("chunk", "")
        lines.append(f"{i}. [{entry_title}] {chunk}")

    return "\n" + "\n".join(lines) + "\n"


def build_resume_prompt(
    section_type: str,
    user_input: str,
    current_content=None,
    stdef=None,
    query_embedding=None,
    retrieved_context: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Build a complete stateless prompt for one resume section.

    If stdef (a SectionTypeDefinition instance) is provided, reads instructions
    and schema from the DB record. Falls back to hardcoded dicts for backwards
    compatibility with legacy callers.

    retrieved_context: top-m chunks from the RAG pipeline
        ({"entry_title", "section_key", "chunk", "score"}), or None if this
        section_type has no retrieval repository (e.g. header, education).

    query_embedding: accepted for backwards compatibility / debug logging
        only — NOT used in prompt content. Do not thread it into the LLM
        call itself.
    """
    if stdef is not None and stdef.llm_prompt_instructions and stdef.json_schema:
        section_instruction = stdef.llm_prompt_instructions
        schema: Dict[str, Any] = stdef.json_schema
    else:
        schema = get_schema(section_type)
        section_instruction = SECTION_INSTRUCTIONS.get(section_type)
        if section_instruction is None:
            raise ValueError(f"No prompt instructions found for section type: {section_type}")

    schema_text = json.dumps(schema, indent=2)

    current_context = ""
    if current_content is not None:
        current_context = f"""
Current content (prior generation — use as context when regenerating):
{json.dumps(current_content, indent=2)}
"""

    retrieved_context_block = _format_retrieved_context(retrieved_context)

    return f"""
{BASE_SYSTEM_PROMPT}

{section_instruction}

Section type:
{section_type}

Expected JSON schema:
{schema_text}
{current_context}
{retrieved_context_block}
User input:
{user_input}

Return only valid JSON matching the expected schema.
"""