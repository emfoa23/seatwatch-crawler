"""CGV 좌석 데이터 fetch.

실 endpoint:
  - 좌석 카운트: http://m.cgv.co.kr/WebApp/Reservation/RemainSeatCount.aspx
    (TheaterCd, ScreenCd, ShowDt, MovieCd, StartTime 파라미터 필요)
  - 좌석 상세: http://www.cgv.co.kr/ticket/... (ActiveX 잔재 + 인증 토큰)

운영 시 externalEventId 는 위 5개 파라미터를 합친 hash 가 아닌
실제 사이트의 식별자 조합이 되어야 함. 본 함수는 그 mapping 을 모르므로
endpoint 호출 자체가 어려움 → 현재는 mock fallback.

향후 운영자가 externalEventId 의 의미를 정해 (예: '0013_01_20260601_20029_1030')
fetch 호출 시 split 해서 실 endpoint 로.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import httpx

from common.backoff import fetch as http_fetch
from .parse import build_mock


def fetch_seats(target_id: str, event_datetime: str) -> dict[str, Any]:
    """target_id 의 좌석 snapshot.

    현재: 좌석 데이터 endpoint 가 인증 토큰 + 변동 high. mock fallback.
    """
    # 실 endpoint 시도 (예: 공개 page ping — IP/네트워크 확인용)
    try:
        r = http_fetch(
            'http://m.cgv.co.kr/',
            timeout=5.0,
            max_retries=1,
            mobile_ua=True,
        )
        # 응답 200 = 사이트 도달 가능. 단 좌석 raw data 아직 추출 불가.
        note = f'reachable status={r.status_code}'
    except httpx.HTTPStatusError as e:
        note = f'blocked status={e.response.status_code}'
    except Exception as e:
        note = f'unreachable {type(e).__name__}'
    return build_mock(target_id, event_datetime, source_note=note)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
