"""Megabox 좌석 fetch.

실 endpoint:
  - https://www.megabox.co.kr/on/oh/ohh/Brand/movieByTheater.do (POST JSON)
  - https://www.megabox.co.kr/on/oh/ohb/SimpleReservation/ScheduleSeats.do (좌석)
  운영 시 endpoint 확정 + 토큰/세션 분석 후 활성화. 현재는 mock fallback.
"""
from __future__ import annotations
from typing import Any
import httpx

from common.backoff import fetch as http_fetch
from .parse import build_mock


def fetch_seats(target_id: str, event_datetime: str) -> dict[str, Any]:
    try:
        r = http_fetch('https://www.megabox.co.kr/', timeout=5.0, max_retries=1)
        note = f'reachable status={r.status_code}'
    except httpx.HTTPStatusError as e:
        note = f'blocked status={e.response.status_code}'
    except Exception as e:
        note = f'unreachable {type(e).__name__}'
    return build_mock(target_id, event_datetime, source_note=note)
