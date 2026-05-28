"""Valkey snapshot read/write + 알림 큐 push.

키 prefix 는 환경변수 VALKEY_KEY_PREFIX (기본 seatwatch:dev).
모든 키에 자동 prefix wrap.
"""
from __future__ import annotations
import json
import os
from typing import Any
import redis

from .env import require


def make_client() -> redis.Redis:
    url = require('VALKEY_URL')
    return redis.Redis.from_url(url, decode_responses=True)


PREFIX = os.environ.get('VALKEY_KEY_PREFIX', 'seatwatch:dev')


def _k(key: str) -> str:
    return f'{PREFIX}:{key}'


def get_snapshot(client: redis.Redis, site: str, event_id: str, datetime_iso: str) -> dict[str, Any] | None:
    raw = client.get(_k(f'snapshot:{site}:{event_id}:{datetime_iso}'))
    return json.loads(raw) if raw else None


def set_snapshot(client: redis.Redis, snapshot: dict[str, Any]) -> None:
    site = snapshot['site']
    event_id = snapshot['externalEventId']
    dt = snapshot['eventDatetime']
    client.set(_k(f'snapshot:{site}:{event_id}:{dt}'), json.dumps(snapshot), ex=60 * 60 * 3)
    client.set(_k(f'freshness:{site}:{event_id}'), snapshot['capturedAt'])


def push_notification(client: redis.Redis, payload: dict[str, Any]) -> None:
    client.lpush(_k('notify:queue'), json.dumps(payload))


def set_freshness(client: redis.Redis, site: str, event_id: str, ts_iso: str) -> None:
    client.set(_k(f'freshness:{site}:{event_id}'), ts_iso)
