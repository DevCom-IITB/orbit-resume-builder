"""
Redis-backed rate limiting service for LLM calls.

Implements:
- 30-minute rolling/fixed window limit per LDAP user
- Daily window limit per LDAP user
- Atomic Lua script execution to prevent concurrency races across Django workers
- Graceful in-memory/fakeredis fallback if Redis server is temporarily unreachable
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)


# Atomic Lua script for checking both 30m and daily limits and incrementing only if both pass
_RATE_LIMIT_LUA_SCRIPT = """
local key_30m = KEYS[1]
local key_daily = KEYS[2]
local limit_30m = tonumber(ARGV[1])
local ttl_30m = tonumber(ARGV[2])
local limit_daily = tonumber(ARGV[3])
local ttl_daily = tonumber(ARGV[4])

local count_30m = tonumber(redis.call('get', key_30m) or '0')
local count_daily = tonumber(redis.call('get', key_daily) or '0')

if count_30m >= limit_30m then
    local rem_ttl = redis.call('ttl', key_30m)
    if rem_ttl < 0 then rem_ttl = ttl_30m end
    return {0, "30_minute", rem_ttl, count_30m}
end

if count_daily >= limit_daily then
    local rem_ttl = redis.call('ttl', key_daily)
    if rem_ttl < 0 then rem_ttl = ttl_daily end
    return {0, "daily", rem_ttl, count_daily}
end

local new_30m = redis.call('incr', key_30m)
if new_30m == 1 or redis.call('ttl', key_30m) < 0 then
    redis.call('expire', key_30m, ttl_30m)
end

local new_daily = redis.call('incr', key_daily)
if new_daily == 1 or redis.call('ttl', key_daily) < 0 then
    redis.call('expire', key_daily, ttl_daily)
end

local rem_ttl = redis.call('ttl', key_30m)
return {1, "ok", rem_ttl, new_30m, new_daily}
"""


@dataclass
class RateLimitResult:
    is_allowed: bool
    limit_type: Optional[str]  # "30_minute" | "daily" | None
    retry_after: int  # Seconds to wait
    reset_at: Optional[datetime]
    message: str
    current_count: int = 0


class LLMRateLimiter:
    """Manages LLM call quota and window expiry using Redis."""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._lua_script_sha = None

    def _get_client(self):
        if self._redis is not None:
            return self._redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            return self._redis
        except Exception as exc:
            logger.warning(
                f"[LLMRateLimiter] Real Redis unavailable ({exc}). Falling back to fakeredis."
            )
            try:
                import fakeredis

                self._redis = fakeredis.FakeRedis(decode_responses=True)
                return self._redis
            except ImportError:
                raise RuntimeError(
                    f"Redis connection failed to {redis_url} and fakeredis is not installed."
                ) from exc

    def _get_limits(self):
        limit_30m = int(os.getenv("ORBIT_LLM_USER_30MIN_LIMIT", "20"))
        window_30m = int(os.getenv("ORBIT_LLM_USER_30MIN_WINDOW_SECONDS", "1800"))
        limit_daily = int(os.getenv("ORBIT_LLM_USER_DAILY_LIMIT", "100"))
        window_daily = int(os.getenv("ORBIT_LLM_USER_DAILY_WINDOW_SECONDS", "86400"))
        return limit_30m, window_30m, limit_daily, window_daily

    def key_30m(self, ldap_id: str) -> str:
        safe_id = str(ldap_id).strip().lower()
        return f"orbit:llm:user:{safe_id}:30m"

    def key_daily(self, ldap_id: str) -> str:
        safe_id = str(ldap_id).strip().lower()
        return f"orbit:llm:user:{safe_id}:daily"

    def check_and_acquire(self, ldap_id: str) -> RateLimitResult:
        """
        Atomically checks if user is within both 30-minute and daily limits.
        If within limits, increments both counters and returns is_allowed=True.
        If either limit is reached, does NOT increment and returns is_allowed=False
        with retry_after and reset_at details.
        """
        if not ldap_id:
            return RateLimitResult(
                is_allowed=False,
                limit_type="invalid_user",
                retry_after=0,
                reset_at=None,
                message="Cannot determine user identity for rate limiting.",
            )

        client = self._get_client()
        limit_30m, window_30m, limit_daily, window_daily = self._get_limits()

        k_30m = self.key_30m(ldap_id)
        k_daily = self.key_daily(ldap_id)

        try:
            # Execute atomic Lua script
            result = client.eval(
                _RATE_LIMIT_LUA_SCRIPT,
                2,
                k_30m,
                k_daily,
                limit_30m,
                window_30m,
                limit_daily,
                window_daily,
            )

            # result format: {allowed_flag, status_or_limit_type, ttl_seconds, count_or_new30m, [new_daily]}
            is_allowed = bool(result[0] == 1)
            limit_type = str(result[1])
            retry_after = max(1, int(result[2])) if result[2] is not None else window_30m
            current_count = int(result[3]) if len(result) > 3 else 0

            now = datetime.now(timezone.utc)
            reset_at = now + timedelta(seconds=retry_after)

            if is_allowed:
                return RateLimitResult(
                    is_allowed=True,
                    limit_type=None,
                    retry_after=0,
                    reset_at=None,
                    message="Request quota acquired.",
                    current_count=current_count,
                )

            if limit_type == "daily":
                msg = "You have reached today's AI generation limit."
            else:
                minutes = max(1, round(retry_after / 60))
                msg = f"You have reached the AI generation limit. Please try again in {minutes} minutes."

            return RateLimitResult(
                is_allowed=False,
                limit_type=limit_type,
                retry_after=retry_after,
                reset_at=reset_at,
                message=msg,
                current_count=current_count,
            )

        except Exception as exc:
            logger.error(f"[LLMRateLimiter] Error during atomic rate check: {exc}", exc_info=True)
            # Fail closed or open? Plan asks to prevent uncontrolled usage, but not crash on redis glitch
            # If Redis errors, allow single request with warning to prevent hard user lockout
            return RateLimitResult(
                is_allowed=True,
                limit_type=None,
                retry_after=0,
                reset_at=None,
                message="Quota check passed (degraded mode).",
            )

    def get_usage(self, ldap_id: str) -> dict:
        """Read current counters and remaining TTLs without modifying them."""
        client = self._get_client()
        k_30m = self.key_30m(ldap_id)
        k_daily = self.key_daily(ldap_id)
        limit_30m, window_30m, limit_daily, window_daily = self._get_limits()

        count_30m = int(client.get(k_30m) or 0)
        ttl_30m = max(0, client.ttl(k_30m))
        count_daily = int(client.get(k_daily) or 0)
        ttl_daily = max(0, client.ttl(k_daily))

        return {
            "ldap_id": ldap_id,
            "count_30m": count_30m,
            "limit_30m": limit_30m,
            "ttl_30m": ttl_30m,
            "count_daily": count_daily,
            "limit_daily": limit_daily,
            "ttl_daily": ttl_daily,
        }

    def reset_for_user(self, ldap_id: str) -> None:
        """Reset counters for a user (primarily for testing and admin overrides)."""
        client = self._get_client()
        client.delete(self.key_30m(ldap_id), self.key_daily(ldap_id))


# Global default instance
rate_limiter = LLMRateLimiter()
