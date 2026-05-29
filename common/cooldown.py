"""중복 fetch 방지 — Valkey 의 freshness 키 기반 minimum_interval 체크.

같은 target 을 너무 자주 호출하지 않도록.
"""
from __future__ import annotations
from datetime import datetime, timezone
import redis


def _now() -> datetime:
    return datetime.now(timezone.utc)


def should_skip(rc: redis.Redis, site: str, event_id: str, min_interval_sec: int) -> bool:
    """직전 freshness timestamp 가 min_interval_sec 이내면 skip."""
    from .valkey_client import _k
    raw = rc.get(_k(f'freshness:{site}:{event_id}'))
    if not raw:
        return False
    try:
        last = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return False
    age = (_now() - last).total_seconds()
    return age < min_interval_sec
