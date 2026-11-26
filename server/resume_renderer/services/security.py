"""
Security and audit service layer for LLM generation.

Handles:
- Durable security event logging in MySQL/Django
- User restriction enforcement and progressive violation escalation
- Prompt injection heuristic detection
- Schema validation with extra-key rejection
- Empty / off-topic content classification
"""

import logging
import re
from typing import Any, Dict, Optional, Tuple

from django.utils import timezone
import jsonschema

from resumes.models import SecurityEvent, UserSecurityState

logger = logging.getLogger(__name__)

# Heuristic prompt injection patterns in student resume inputs
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above)\s+(instructions|directives|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+|everything\s+)?(previous|prior|above)", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+|your\s+)?(system|developer|hidden)\s+(prompt|instructions)", re.IGNORECASE),
    re.compile(r"(show|output|print|display)\s+(the\s+|your\s+)?(system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+|a\s+)?(developer|jailbreak|god|dan)\s+mode", re.IGNORECASE),
    re.compile(r"(system|assistant)\s*:\s*ignore", re.IGNORECASE),
]


def detect_prompt_injection(text: str) -> bool:
    """Return True if text contains clear prompt injection signals."""
    if not text:
        return False
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def get_client_ip(request) -> Optional[str]:
    """Extract client IP address from Django request."""
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_security_event(
    ldap_id: str,
    event_type: str,
    severity: str = "info",
    resume_id: Optional[str] = None,
    section_type: Optional[str] = None,
    endpoint: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SecurityEvent:
    """Record a persistent security event in MySQL."""
    try:
        event = SecurityEvent.objects.create(
            ldap_id=str(ldap_id).strip().lower(),
            event_type=event_type,
            severity=severity,
            resume_id=str(resume_id) if resume_id else None,
            section_type=str(section_type) if section_type else None,
            endpoint=str(endpoint) if endpoint else None,
            ip_address=ip_address,
            metadata=metadata or {},
        )
        return event
    except Exception as exc:
        logger.error(f"[Security] Failed to write SecurityEvent to DB: {exc}", exc_info=True)
        return None


def get_user_security_state(ldap_id: str) -> UserSecurityState:
    """Get or create persistent UserSecurityState for LDAP user."""
    safe_id = str(ldap_id).strip().lower()
    state, _ = UserSecurityState.objects.get_or_create(ldap_id=safe_id)
    return state


def check_user_restriction(ldap_id: str) -> Optional[UserSecurityState]:
    """
    Check if user is currently restricted.
    Returns the UserSecurityState instance if restricted, otherwise None.
    If restriction timestamp has passed, user is automatically no longer restricted.
    """
    if not ldap_id:
        return None
    state = get_user_security_state(ldap_id)
    if state.is_restricted():
        return state
    return None


def record_user_violation(
    ldap_id: str,
    event_type: str,
    severity: str = "warning",
    resume_id: Optional[str] = None,
    section_type: Optional[str] = None,
    endpoint: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> UserSecurityState:
    """
    Record a violation in MySQL:
    1. Log a SecurityEvent record.
    2. Increment user violation count and abuse score.
    3. Apply progressive temporary block if threshold reached.
    """
    log_security_event(
        ldap_id=ldap_id,
        event_type=event_type,
        severity=severity,
        resume_id=resume_id,
        section_type=section_type,
        endpoint=endpoint,
        ip_address=ip_address,
        metadata=metadata,
    )
    state = get_user_security_state(ldap_id)
    was_restricted = state.is_restricted()
    state.record_violation(event_type=event_type, severity=severity)

    if not was_restricted and state.is_restricted():
        # User just became restricted, log restriction event
        log_security_event(
            ldap_id=ldap_id,
            event_type="ACCOUNT_RESTRICTED",
            severity="high",
            resume_id=resume_id,
            section_type=section_type,
            endpoint=endpoint,
            ip_address=ip_address,
            metadata={
                "trigger_event": event_type,
                "blocked_until": state.blocked_until.isoformat() if state.blocked_until else None,
                "violation_count": state.violation_count,
                "abuse_score": state.abuse_score,
            },
        )
    return state


def validate_and_classify_llm_output(
    data: Any,
    schema: Dict[str, Any],
    section_type: str,
) -> Tuple[bool, bool, Optional[str]]:
    """
    Validate LLM output against the JSON schema and classify if it is empty/off-topic.

    Returns:
        (is_valid, is_empty, error_message)
        - is_valid: True if schema conforms and no forbidden keys
        - is_empty: True if content represents an empty response (e.g. [] or all-blank fields)
        - error_message: Validation error details if invalid
    """
    try:
        # Standard schema validation
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        return False, False, f"Schema validation error: {exc.message}"
    except Exception as exc:
        return False, False, f"Unexpected validation error: {str(exc)}"

    # Check for empty response (off-topic input indicator)
    if isinstance(data, list):
        if len(data) == 0:
            return True, True, None

        # Check if all items in the list are empty dicts or have only empty strings/lists
        all_empty = True
        for item in data:
            if isinstance(item, dict):
                has_content = any(
                    bool(v and (isinstance(v, str) and v.strip() or isinstance(v, list) and len(v) > 0))
                    for v in item.values()
                )
                if has_content:
                    all_empty = False
                    break
            elif bool(item):
                all_empty = False
                break
        if all_empty:
            return True, True, None

    elif isinstance(data, dict):
        # E.g. Header
        substantive_keys = [k for k in ["name", "email", "roll_no", "department", "degree"] if k in data]
        if substantive_keys:
            has_substantive = any(bool(str(data[k]).strip()) for k in substantive_keys)
            if not has_substantive:
                return True, True, None
        else:
            has_content = any(bool(v and str(v).strip()) for v in data.values())
            if not has_content:
                return True, True, None

    return True, False, None
