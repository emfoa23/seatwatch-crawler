"""CGV 좌석 데이터 fetch.

현재 endpoint 는 변동 가능 + 봇 차단 우려가 있어, 운영 도입 전 DevTools Network 로 확정 후 patch 필요.
지금은 골격 + Mock fallback 으로 다른 파이프라인 (Valkey 적재 · diff · 큐 push) 을 먼저 검증.
"""
from __future__ import annotations
import random
from datetime import datetime, timezone
from typing import Any
import httpx

from .parse import normalize, build_mock

UA_POOL = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
]


def fetch_seats(target_id: str, *, allow_mock_fallback: bool = True) -> dict[str, Any]:
    """target_id 의 좌석 snapshot 을 가져옴. 실패 시 mock fallback (allow_mock_fallback=True 일 때).

    target_id 포맷: '<theater_code>:<movie_code>:<screen>:<datetime>' (운영 시 확정).
    MVP 에서는 endpoint 미확정이므로 mock fallback 로 통과.
    """
    headers = {
        'User-Agent': random.choice(UA_POOL),
        'Accept': 'application/json,text/javascript,*/*;q=0.9',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Referer': 'http://www.cgv.co.kr/',
    }

    try:
        with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as client:
            r = client.get('http://www.cgv.co.kr/common/showtimes/iframeTheater.aspx')
            r.raise_for_status()
        raise NotImplementedError('endpoint not finalized for raw seat data')
    except Exception as exc:
        if not allow_mock_fallback:
            raise
        return build_mock(target_id, source_note=f'mock_fallback: {type(exc).__name__}')


def make_target_event_id(target_id: str) -> str:
    """target_id 그대로 사용하되, 향후 변환 로직 추가 시 여기서 정규화."""
    return target_id


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
