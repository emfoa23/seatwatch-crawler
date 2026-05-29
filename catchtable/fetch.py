"""CatchTable 시간대 가용성 fetch.

실 endpoint (변동 가능):
  - https://api.catchtable.co.kr/shops/<id>/available-times?date=YYYY-MM-DD
  모바일 UA + Authorization (게스트 token) 필요할 수 있음.
"""
from __future__ import annotations
from typing import Any
import httpx

from common.backoff import fetch as http_fetch
from .parse import build_mock


def fetch_timeslots(target_id: str, event_datetime: str) -> dict[str, Any]:
    try:
        r = http_fetch(
            'https://app.catchtable.co.kr/',
            timeout=5.0,
            max_retries=1,
            mobile_ua=True,
        )
        note = f'reachable status={r.status_code}'
    except httpx.HTTPStatusError as e:
        note = f'blocked status={e.response.status_code}'
    except Exception as e:
        note = f'unreachable {type(e).__name__}'
    return build_mock(target_id, event_datetime, source_note=note)
