import json
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from resumes.models import UserSecurityState, SecurityEvent
from resume_renderer.services.llm_rate_limiter import rate_limiter


class Command(BaseCommand):
    help = "Displays LLM usage quotas, abuse violations, and cooldown status for a user."

    def add_arguments(self, parser):
        parser.add_argument("ldap_id", type=str, nargs="?", default="25b2285", help="LDAP ID to check")
        parser.add_argument("--reset", action="store_true", help="Reset Redis usage counters and unblock user")

    def handle(self, *args, **options):
        ldap_id = options["ldap_id"].strip().lower()

        if options["reset"]:
            rate_limiter.reset_for_user(ldap_id)
            state = UserSecurityState.objects.filter(ldap_id=ldap_id).first()
            if state:
                state.unblock()
                state.violation_count = 0
                state.abuse_score = 0
                state.save()
            self.stdout.write(self.style.SUCCESS(f"Successfully reset usage quotas and cleared abuse for user '{ldap_id}'."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== Security & LLM Usage Status: {ldap_id} ==="))

        # 1. Redis Usage Quota
        usage = rate_limiter.get_usage(ldap_id)
        ttl_30m_min = round(usage["ttl_30m"] / 60, 1) if usage["ttl_30m"] > 0 else 0
        ttl_daily_hr = round(usage["ttl_daily"] / 3600, 1) if usage["ttl_daily"] > 0 else 0

        self.stdout.write(f"\n[Redis Quotas]")
        self.stdout.write(
            f"  30-Min Window : {usage['count_30m']}/{usage['limit_30m']} used "
            f"(resets in {usage['ttl_30m']}s ~ {ttl_30m_min} min)"
        )
        self.stdout.write(
            f"  Daily Window  : {usage['count_daily']}/{usage['limit_daily']} used "
            f"(resets in {usage['ttl_daily']}s ~ {ttl_daily_hr} hrs)"
        )

        # 2. MySQL UserSecurityState
        state = UserSecurityState.objects.filter(ldap_id=ldap_id).first()
        self.stdout.write(f"\n[Abuse & Cooldown State (MySQL)]")
        if not state:
            self.stdout.write("  No abuse record found (User has 0 violations).")
        else:
            is_blocked = state.is_restricted()
            blocked_str = self.style.ERROR(f"BLOCKED until {state.blocked_until}") if is_blocked else self.style.SUCCESS("Active (Not blocked)")
            self.stdout.write(f"  Restriction Status : {blocked_str}")
            self.stdout.write(f"  Violation Count    : {state.violation_count} (Tier 1 block triggers at 3)")
            self.stdout.write(f"  Abuse Score        : {state.abuse_score}")
            self.stdout.write(f"  Last Violation At  : {state.last_violation_at}")

        # 3. Recent Security Events
        events = SecurityEvent.objects.filter(ldap_id=ldap_id).order_by("-created_at")[:5]
        self.stdout.write(f"\n[Recent Security Events (Last 5)]")
        if not events.exists():
            self.stdout.write("  None")
        else:
            for ev in events:
                snippet = ev.metadata.get("input_snippet") or ev.metadata.get("error") or ""
                if len(snippet) > 60:
                    snippet = snippet[:57] + "..."
                self.stdout.write(
                    f"  - {ev.created_at.strftime('%Y-%m-%d %H:%M:%S')} | [{ev.severity.upper()}] {ev.event_type} | {snippet}"
                )
        self.stdout.write("\n")
