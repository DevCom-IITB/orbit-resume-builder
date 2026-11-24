"""Source-backed, advisory preprocessing for narrative resume generation.

This is a local rule-based extractor, not a semantic parser or fact verifier.
Every mention points into the original input. Missing entities/relationships must
be recovered from that input, not inferred from a vocabulary or another resume.
"""

import re
from itertools import chain


NARRATIVE_SECTIONS = frozenset(
    {"key_projects", "professional_experience", "positions_of_responsibility"}
)
MAX_RECORDS = 64

# Split conservative source units, not purported independent accomplishments.
# Decimal points, URLs, React.js, abbreviations and comma-separated tools survive.
_BOUNDARY = re.compile(r"[;\n]+|(?<=[.!?])\s+(?=[A-Z])")
_ACTION = re.compile(
    r"\b(?:built|developed|created|implemented|designed|trained|evaluated|compared"
    r"|reduced|increased|improved|optimized|analysed|analyzed|processed|tested"
    r"|validated|deployed|used|integrated|automated|led|coordinated|organized"
    r"|managed|presented|documented|researched|assisted|contributed|worked)\b",
    re.I,
)
_TECHNOLOGY = re.compile(
    r"(?<!\w)(?:Python|Pandas|GeoPandas|rasterio|NumPy|SciPy|scikit-learn"
    r"|XGBoost|LightGBM|PyTorch|TensorFlow|NLTK|spaCy|LangChain|LangGraph"
    r"|ChromaDB|OpenFEMA|OpenStreetMap|Census API|QGIS|PostgreSQL|MySQL"
    r"|MongoDB|Redis|Celery|Django(?: REST Framework)?|React(?:\.js|JS)?"
    r"|Node\.js|Docker|GitHub|JavaScript|TypeScript|C\+\+|Java|SQL"
    r"|natural[- ]language processing|NLP|neural networks?"
    r"|integer linear programming|machine learning|deep learning"
    r"|retrieval[- ]augmented generation|RAG)(?!\w)",
    re.I,
)
_NUMBER = re.compile(
    r"(?<!\w)\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:k|hundred|thousand|million|billion|lakh|crore)\b)?\+?(?:\s*(?:%|percent\b|°\s*C\b"
    r"|degrees?\s+Celsius\b|ms\b|milliseconds?\b|seconds?\b|users?\b"
    r"|members?\b|neighbou?rhoods?\b|counties\b|chunks?\b|students?\b))?",
    re.I,
)
_WORD_COUNT = re.compile(
    r"\b(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
    r"|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)"
    r"(?:[- ]|\s+and\s+))*"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
    r"|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
    r"|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)"
    r"\s+(?:users?|members?|neighbou?rhoods?|counties|chunks?|students?)\b",
    re.I,
)
_QUALIFICATION = re.compile(
    r"\b(?:not\s+(?:deployed|validated|tested|used|realized|realised)|never\s+deployed"
    r"|prototype|projected|projecting|projection|simulated|exploratory(?:\s+(?:study|research))?|synthetic(?:\s+data)?"
    r"|local(?:ly)?(?:\s+load)?\s+tests?|held[- ]out(?:\s+test\s+set)?"
    r"|geographically\s+separated(?:\s+training\s+and\s+test\s+areas)?"
    r"|random\s+split|median|mean absolute error|MAE|root mean squared? error|RMSE)\b",
    re.I,
)


def _mention(text, start, end):
    return {"text": text[start:end], "start": start, "end": end}


def _matches(pattern, text, start, end):
    return [
        _mention(text, m.start(), m.end()) for m in pattern.finditer(text, start, end)
    ]


def preprocess_input(user_input, *, max_records=MAX_RECORDS):
    """Extract bounded source units; preserve offsets and explicitly record limits.

    Relationships and importance are deliberately unassigned. A number's context
    is its complete source unit, not an invented metric label or causal claim.
    """
    if not isinstance(user_input, str):
        raise TypeError("user_input must be a string")
    if not 1 <= max_records <= MAX_RECORDS:
        raise ValueError(f"max_records must be between 1 and {MAX_RECORDS}")
    records = []
    start = 0
    truncated = False
    boundaries = (m.end() for m in _BOUNDARY.finditer(user_input))
    for end in chain(boundaries, (len(user_input),)):
        left = start
        while left < end and user_input[left].isspace():
            left += 1
        right = end
        while right > left and (
            user_input[right - 1].isspace() or user_input[right - 1] == ";"
        ):
            right -= 1
        start = end
        if left == right:
            continue
        if len(records) == max_records:
            truncated = True
            break
        numbers = _matches(_NUMBER, user_input, left, right)
        numbers.extend(_matches(_WORD_COUNT, user_input, left, right))
        records.append(
            {
                "id": len(records),
                "source": _mention(user_input, left, right),
                "action_mentions": _matches(_ACTION, user_input, left, right),
                "technology_mentions": _matches(_TECHNOLOGY, user_input, left, right),
                "numeric_mentions": sorted(numbers, key=lambda item: item["start"]),
                "qualification_mentions": _matches(
                    _QUALIFICATION, user_input, left, right
                ),
                "interpretation": "source_unit_not_verified_accomplishment",
                "relationships": "unassigned_use_source_context",
                "importance": "advisory_model_must_assess_in_context",
            }
        )
    return {
        "version": 1,
        "method": "local_rules_no_semantic_verification",
        "records": records,
        "truncated": truncated,
        "limitations": [
            "Technology vocabulary and qualification patterns are incomplete.",
            "Dates and versions may appear as numeric mentions; not every number is an outcome metric.",
            "Mentions in one unit do not prove a relationship; conditions may appear in neighboring units.",
            "Unknown wording, organizations and locations remain in the original input; absence is not permission to omit them.",
        ],
    }


def cleaned_generation_input(raw, organized):
    """Use cleaned assist notes without repeating the complete raw input.

    Only unresolved/unprocessed passages are carried through verbatim. The
    separate evidence block can still support the main model's factual checks.
    """
    local = preprocess_input(raw)
    unassigned = set(organized["unassigned_source_ids"])
    result = {
        "contributions": [
            {
                "id": index,
                "points": group["organized_points"],
                "qualifications": group["qualification_quotes"],
            }
            for index, group in enumerate(organized["contributions"])
        ],
        "global_qualifications": organized["global_qualification_quotes"],
        "ambiguities": organized["ambiguous_quotes"],
        "unresolved_source_notes": [
            record["source"]["text"]
            for record in local["records"]
            if record["id"] in unassigned
        ],
    }
    if local["truncated"]:
        result["unprocessed_source_tail"] = raw[local["records"][-1]["source"]["end"] :]
    return result
