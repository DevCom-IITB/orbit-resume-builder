from django.core.management.base import BaseCommand

from resumes.models import (
    ResumeTemplate,
    SectionTypeDefinition,
    TemplateSectionType,
    VisualTheme,
)
from resume_renderer.JSONSchema.jsonschema import get_schema
from resume_renderer.services.prompts import SECTION_INSTRUCTIONS
from resume_renderer.services.styling import validate_template_style_config

IITB_PREAMBLE = r"""
\documentclass[a4paper,10.9pt]{article}
\usepackage[a4paper, bottom = 0.4mm, left = 14.11mm, right = 14.11mm, top = 0.6in]{geometry}
__FONT_SETUP__
\usepackage{graphicx}
\usepackage[table, svgnames]{xcolor}
\usepackage{wrapfig}
\usepackage{comment}
\usepackage{verbatim}
\usepackage{microtype}
\usepackage{colortbl}
\usepackage{enumitem}
\usepackage{array}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage[pdftex,colorlinks=false,pdfborder={0 0 0}]{hyperref}
\usepackage{hyphenat}
\usepackage{anyfontsize}
\usepackage{fontawesome}
\definecolor{myblue}{HTML}{__ACCENT_HEX__}
\hyphenpenalty 10000
\pagenumbering{gobble}
\setlength{\parindent}{0pt}
\newcommand\xfilll[2][1ex]{
  \dimen0=#2\advance\dimen0 by #1
  \leaders\hrule height \dimen0 depth -#1\hfill
}
\newenvironment{localsize}[1]{
  \begingroup
  \fontsize{#1}{\baselineskip}\selectfont
}{
  \endgroup
}
__SPACING_SETUP__\begin{document}
\parindent=0em
__CONTENT__
\end{document}
"""

AWESOME_PREAMBLE = r"""\documentclass[11pt,a4paper]{article}
\usepackage[a4paper,left=1.4cm,right=1.4cm,top=0.8cm,bottom=1.2cm]{geometry}
\usepackage[T1]{fontenc}
__FONT_SETUP__
\usepackage{anyfontsize}
\usepackage{xcolor}
\usepackage{array}
\usepackage{enumitem}
\usepackage{microtype}
\usepackage[pdftex,colorlinks=false,pdfborder={0 0 0}]{hyperref}

%%%%%%%%%% COLOURS %%%%%%%%%%
\definecolor{awesome}{HTML}{__ACCENT_HEX__}
\definecolor{darktext}{HTML}{414141}
\definecolor{graytext}{HTML}{5D5D5D}
\definecolor{rulegray}{HTML}{BBBBBB}

%%%%%%%%%% PAGE %%%%%%%%%%
\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\setlength{\emergencystretch}{3em}
\hyphenpenalty=10000

%%%%%%%%%% HEADER: \cvheader{first}{last}{position}{extra}{contact} %%%%%%%%%%
\newcommand{\cvsep}{\quad\textbar\quad}
\newcommand{\cvheader}[5]{%
  \begin{center}
    {\fontsize{28}{32}\selectfont {\color{graytext}#1}\ {\bfseries\color{darktext}#2}}\par\vspace{1ex}
    {\color{awesome}\small #3}\par\vspace{0.6ex}
    {\color{graytext}\small #4}\par\vspace{0.4ex}
    {\color{graytext}\small #5}\par
  \end{center}\vspace{-1ex}}

%%%%%%%%%% SECTION TITLE: first 3 letters in accent colour %%%%%%%%%%
\def\cvsecfirst#1#2#3{{\color{awesome}#1#2#3}}
\newcommand{\cvsection}[1]{%
  \par\vspace{1.4ex}\noindent
  {\Large\bfseries\color{darktext}\cvsecfirst #1}\par
  \vspace{-1.1ex}\noindent{\color{rulegray}\rule{\linewidth}{0.4pt}}\par\vspace{0.4ex}}

%%%%%%%%%% BULLETS %%%%%%%%%%
\newlist{cvitems}{itemize}{1}
\setlist[cvitems]{label=\textcolor{awesome}{\textbullet},leftmargin=1.2em,
  itemsep=0pt,topsep=2pt,parsep=0pt,partopsep=0pt}
\newcommand{\cvsummary}[1]{\par\noindent{\small\itshape #1}\par\vspace{1pt}}

%%%%%%%%%% ENTRIES: \cventry{role}{org}{location}{date}{description} %%%%%%%%%%
\newenvironment{cventries}{\par}{\par}
\newcommand{\cventry}[5]{%
  \par\vspace{1.2ex}\noindent
  {\bfseries\color{darktext}#1}\hfill{\small\itshape\color{graytext}#4}\par
  \vspace{-0.3ex}\noindent
  {\small\color{awesome}#2}\hfill{\small\itshape\color{graytext}#3}\par
  #5}

%%%%%%%%%% HONORS: \cvhonor{award}{event}{location}{date} %%%%%%%%%%
\newlength{\cvhonordatewidth}\setlength{\cvhonordatewidth}{2.4em}
\newenvironment{cvhonors}{\par}{\par}
\newcommand{\cvhonor}[4]{%
  \par\vspace{0.5ex}\noindent
  \ifx\relax#4\relax\else
    \hangindent=\dimexpr\cvhonordatewidth+0.6em\relax\hangafter=1\relax
    \makebox[\cvhonordatewidth][l]{\small\color{graytext}#4}\hspace{0.6em}%
  \fi
  \ifx\relax#1\relax\else{\bfseries #1}\ifx\relax#2\relax\else,\ \fi\fi
  #2%
  \ifx\relax#3\relax\else\hfill{\small\itshape\color{graytext}#3}\fi
  \par}

%%%%%%%%%% SKILLS: \cvskill{category}{items} %%%%%%%%%%
\newenvironment{cvskills}
  {\par\vspace{0.6ex}\noindent
   \begin{tabular}{@{}>{\raggedleft\arraybackslash}p{0.2\linewidth}@{\hspace{1em}}>{\raggedright\arraybackslash}p{0.76\linewidth}@{}}}
  {\end{tabular}\par}
\newcommand{\cvskill}[2]{{\bfseries #1} & #2\\[0.5ex]}

__SPACING_SETUP__\begin{document}
\parindent=0em

__CONTENT__

\end{document}
"""

JAKE_PREAMBLE = r"""\documentclass[a4paper,11pt]{article}

\usepackage[a4paper,left=0.5in,right=0.5in,top=0.5in,bottom=0.5in]{geometry}
\usepackage[T1]{fontenc}
__FONT_SETUP__
\usepackage{titlesec}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\input{glyphtounicode}

\definecolor{accent}{HTML}{__ACCENT_HEX__}

\pagestyle{empty}
\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

% Sections formatting (accent colour; default black = original)
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large\color{accent}
}{}{0em}{}[{\color{accent}\titlerule}\vspace{-5pt}]

% Machine readable / ATS parsable PDF
\pdfgentounicode=1

%-------------------------
% Header: \resumeHeader{name}{extra line (may be empty)}{contact line}
\newcommand{\resumeSep}{\ $|$\ }
\newcommand{\resumeHeader}[3]{%
  \begin{center}
    \textbf{\Huge \scshape #1} \\ \vspace{1pt}
    \ifx\relax#2\relax\else\small #2 \\ \vspace{1pt}\fi
    \small #3
  \end{center}}

%-------------------------
% Jake's commands (unchanged)
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}

\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

%-------------------------
% Technical skills / courses block: rows joined with " \\" by the converter
\newcommand{\resumeSkillsListStart}{\begin{itemize}[leftmargin=0.15in, label={}]\small\item}
\newcommand{\resumeSkillsListEnd}{\end{itemize}}
\newcommand{\resumeSkill}[2]{\textbf{#1}{: #2}}

%-------------------------
% Scholastic achievements: \resumeAchievement{text}{year (may be empty)}
\newcommand{\resumeAchievementListStart}{\begin{itemize}[leftmargin=0.15in, label={$\vcenter{\hbox{\tiny$\bullet$}}$}]}
\newcommand{\resumeAchievementListEnd}{\end{itemize}\vspace{-5pt}}
\newcommand{\resumeAchievement}[2]{\resumeItem{#1\ifx\relax#2\relax\else\hfill\textit{#2}\fi}}

%-------------------------------------------
__SPACING_SETUP__\begin{document}

__CONTENT__

\end{document}
"""


SECTION_TYPES = [
    {
        "key": "header",
        "display_name": "Header",
        "allow_multiple_entries": False,
        "default_converter_key": "convert_header",
        "entry_hint_text": "Your full name, degree, and contact details (email, phone, LinkedIn, GitHub).",
    },
    {
        "key": "education",
        "display_name": "Education",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_education",
        "entry_hint_text": "Degree, institution, CPI/percentage, and year.",
    },
    {
        "key": "scholastic_achievements",
        "display_name": "Scholastic Achievements",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_scholastic_achievements",
        "entry_hint_text": "One academic achievement, rank, scholarship, or award.",
    },
    {
        "key": "courses",
        "display_name": "Relevant Courses Undertaken",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_courses",
        "entry_hint_text": "A category of courses (e.g. Computer Science: DSA, OS, Networks).",
    },
    {
        "key": "professional_experience",
        "display_name": "Professional Experience",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_experience",
        "entry_hint_text": "Describe your role, company, and what you worked on.",
    },
    {
        "key": "key_projects",
        "display_name": "Key Projects",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_key_project",
        "entry_hint_text": "Describe the project, its goal, your contribution, and technologies used.",
    },
    {
        "key": "positions_of_responsibility",
        "display_name": "Positions of Responsibility",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_pors",
        "entry_hint_text": "Your role, the organisation, duration, and what you did.",
    },
    {
        "key": "technical_skills",
        "display_name": "Technical Skills",
        "allow_multiple_entries": True,
        "default_converter_key": "convert_technical_skills",
        "entry_hint_text": "A category of skills (e.g. Programming: Python, C++, JavaScript).",
    },
]

IITB_MANIFEST = [
    ("header",                      True,  True,  0),
    ("education",                   True,  True,  1),
    ("scholastic_achievements",     True,  False, 2),
    ("courses",                     True,  False, 3),
    ("professional_experience",     True,  False, 4),
    ("key_projects",                True,  False, 5),
    ("positions_of_responsibility", True,  False, 6),
    ("technical_skills",            True,  False, 7),
]

EXTERNAL_MANIFEST = [
    ("header",                      True,  True,  0),
    ("education",                   True,  True,  1),
    ("professional_experience",     True,  False, 2),
    ("key_projects",                True,  False, 3),
    ("technical_skills",            True,  False, 4),
    ("positions_of_responsibility", False, False, 5),
    ("courses",                     False, False, 6),
    ("scholastic_achievements",     False, False, 7),
]

AWESOME_MANIFEST = [
    ("header",                      True,  True,  0),
    ("education",                   True,  True,  1),
    ("professional_experience",     True,  False, 2),
    ("key_projects",                True,  False, 3),
    ("technical_skills",            True,  False, 4),
    ("positions_of_responsibility", False, False, 5),
    ("courses",                     False, False, 6),
    ("scholastic_achievements",     False, False, 7),
]

JAKE_MANIFEST = [
    ("header",                      True,  True,  0),
    ("education",                   True,  True,  1),
    ("professional_experience",     True,  False, 2),
    ("key_projects",                True,  False, 3),
    ("technical_skills",            True,  False, 4),
    ("positions_of_responsibility", False, False, 5),
    ("courses",                     False, False, 6),
    ("scholastic_achievements",     False, False, 7),
]


DEFAULT_SPACING_CONFIG = {
    "line_spacing_options": ["0.90", "0.95", "1.00", "1.05", "1.10", "1.15", "1.20"],
    "line_spacing_default": "1.00",
    "word_spacing_options": ["0.90", "0.95", "1.00", "1.05", "1.10", "1.15", "1.20"],
    "word_spacing_default": "1.00",
}

IITB_STYLE_OPTIONS = {
    "font_default": "lmodern",
    "font_options": ["lmodern", "times", "palatino"],
    "accent_default": "#4B41C8",
    "accent_options": [
        "#4B41C8",
        "#1A6B3C",
        "#8B1A1A",
        "#1A4B8C",
        "#5C3A9C",
        "#2E6B8B",
        "#8B5C00",
    ],
    **DEFAULT_SPACING_CONFIG,
}

EXTERNAL_STYLE_OPTIONS = {
    "font_default": "lmodern",
    "font_options": ["lmodern", "times", "palatino"],
    "accent_default": "#4B41C8",
    "accent_options": [
        "#4B41C8",
        "#1A6B3C",
        "#8B1A1A",
        "#1A4B8C",
        "#5C3A9C",
        "#2E6B8B",
        "#8B5C00",
    ],
    **DEFAULT_SPACING_CONFIG,
}

AWESOME_STYLE_OPTIONS = {
    "font_default": "sourcesans",
    "font_options": ["sourcesans", "helvetica", "lmodern"],
    "accent_default": "#DC3522",
    "accent_options": [
        "#00A388",
        "#0395DE",
        "#DC3522",
        "#EF4089",
        "#131A28",
    ],
    **DEFAULT_SPACING_CONFIG,
}

JAKE_STYLE_OPTIONS = {
    "font_default": "lmodern",
    "font_options": ["lmodern", "times", "palatino"],
    "accent_default": "#000000",
    "accent_options": [
        "#000000",
        "#1F3A5F",
        "#0B6E4F",
        "#8B1E3F",
        "#4B41C8",
    ],
    **DEFAULT_SPACING_CONFIG,
}


class Command(BaseCommand):
    help = "Seed SectionTypeDefinitions, VisualThemes, ResumeTemplates, and TemplateSectionTypes"

    def handle(self, *args, **options):
        created_counts = {"stdef": 0, "themes": 0, "templates": 0, "tst": 0}
        updated_counts = {"stdef": 0}

        # 1. SectionTypeDefinitions
        stdef_map = {}
        for defn in SECTION_TYPES:
            schema = get_schema(defn["key"])
            instructions = SECTION_INSTRUCTIONS.get(defn["key"], "")

            stdef, created = SectionTypeDefinition.objects.update_or_create(
                key=defn["key"],
                defaults={
                    "display_name": defn["display_name"],
                    "allow_multiple_entries": defn["allow_multiple_entries"],
                    "default_converter_key": defn["default_converter_key"],
                    "entry_hint_text": defn["entry_hint_text"],
                    "llm_prompt_instructions": instructions,
                    "json_schema": schema,
                },
            )
            stdef_map[defn["key"]] = stdef
            if created:
                created_counts["stdef"] += 1
            else:
                updated_counts["stdef"] += 1

        # 2. VisualThemes
        iitb_theme, created = VisualTheme.objects.update_or_create(
            key="iitb-classic",
            defaults={
                "display_name": "Classic (IIT Bombay)",
                "compatible_families": ["iitb"],
                "converter_set_key": "iitb-classic",
                "latex_preamble": IITB_PREAMBLE,
            },
        )
        if created:
            created_counts["themes"] += 1

        external_theme, created = VisualTheme.objects.update_or_create(
            key="external-standard",
            defaults={
                "display_name": "Standard (External)",
                "compatible_families": ["external"],
                "converter_set_key": "external-standard",
                "latex_preamble": IITB_PREAMBLE,
            },
        )
        if created:
            created_counts["themes"] += 1

        awesome_theme, created = VisualTheme.objects.update_or_create(
            key="awesome-cv-classic",
            defaults={
                "display_name": "Classic (Awesome CV)",
                "compatible_families": ["awesome"],
                "converter_set_key": "awesome-cv",
                "latex_preamble": AWESOME_PREAMBLE,
            },
        )
        if created:
            created_counts["themes"] += 1

        jake_theme, created = VisualTheme.objects.update_or_create(
            key="jake-classic",
            defaults={
                "display_name": "Classic (Jake)",
                "compatible_families": ["jake"],
                "converter_set_key": "jake-classic",
                "latex_preamble": JAKE_PREAMBLE,
            },
        )
        if created:
            created_counts["themes"] += 1

        # 3. ResumeTemplates
        iitb_cfg = {
            "header_style_options": ["short", "long"],
            "header_style_default": "short",
            **IITB_STYLE_OPTIONS,
        }
        validate_template_style_config(iitb_cfg)
        iitb_template, created = ResumeTemplate.objects.update_or_create(
            key="iitb-general",
            defaults={
                "display_name": "IIT Bombay",
                "family": "iitb",
                "domain": "general",
                "max_pages": None,
                "template_config": iitb_cfg,
                "is_active": True,
            },
        )
        iitb_template.available_themes.add(iitb_theme)
        if created:
            created_counts["templates"] += 1

        external_cfg = {**EXTERNAL_STYLE_OPTIONS}
        validate_template_style_config(external_cfg)
        external_template, created = ResumeTemplate.objects.update_or_create(
            key="external-standard",
            defaults={
                "display_name": "External",
                "family": "external",
                "domain": "general",
                "max_pages": None,
                "template_config": external_cfg,
                "is_active": True,
            },
        )
        external_template.available_themes.add(external_theme)
        if created:
            created_counts["templates"] += 1

        awesome_cfg = {**AWESOME_STYLE_OPTIONS}
        validate_template_style_config(awesome_cfg)
        awesome_template, created = ResumeTemplate.objects.update_or_create(
            key="awesome-cv-general",
            defaults={
                "display_name": "Awesome CV",
                "family": "awesome",
                "domain": "general",
                "max_pages": None,
                "template_config": awesome_cfg,
                "is_active": True,
            },
        )
        awesome_template.available_themes.add(awesome_theme)
        if created:
            created_counts["templates"] += 1

        jake_cfg = {**JAKE_STYLE_OPTIONS}
        validate_template_style_config(jake_cfg)
        jake_template, created = ResumeTemplate.objects.update_or_create(
            key="jake-general",
            defaults={
                "display_name": "Jake's Resume",
                "family": "jake",
                "domain": "general",
                "max_pages": None,
                "template_config": jake_cfg,
                "is_active": True,
            },
        )
        jake_template.available_themes.add(jake_theme)
        if created:
            created_counts["templates"] += 1

        # 4. TemplateSectionTypes
        for template, manifest in [
            (iitb_template, IITB_MANIFEST),
            (external_template, EXTERNAL_MANIFEST),
            (awesome_template, AWESOME_MANIFEST),
            (jake_template, JAKE_MANIFEST),
        ]:
            for stkey, is_default, is_required, order in manifest:
                _, created = TemplateSectionType.objects.update_or_create(
                    template=template,
                    section_type=stdef_map[stkey],
                    defaults={
                        "is_default": is_default,
                        "is_required": is_required,
                        "default_order": order,
                    },
                )
                if created:
                    created_counts["tst"] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created_counts['stdef']} section types "
            f"({updated_counts['stdef']} updated), "
            f"{created_counts['themes']} themes, "
            f"{created_counts['templates']} templates, "
            f"{created_counts['tst']} TemplateSectionType rows."
        ))
