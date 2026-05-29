"""HTTP 호출 + retry + jitter + backoff.

- 429 / 5xx → exponential backoff
- 403 / 404 → no retry (영구 차단·존재 안 함)
- network error → 3회 retry
"""
from __future__ import annotations
import random
import time
from typing import Any
import httpx

from . import ua_rotation


RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def jitter_sleep(base_sec: float, spread: float = 0.5) -> None:
    delay = base_sec + random.uniform(0, spread)
    time.sleep(delay)


def fetch(
    url: str,
    *,
    method: str = 'GET',
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 10.0,
    max_retries: int = 3,
    mobile_ua: bool = False,
) -> httpx.Response:
    """Retry + UA rotation + jitter. 영구 실패 status (403/404) 는 즉시 raise."""
    base_headers: dict[str, str] = {
        'User-Agent': ua_rotation.pick(mobile=mobile_ua),
        'Accept': 'application/json, text/html;q=0.9, */*;q=0.5',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.7',
    }
    if headers:
        base_headers.update(headers)

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.request(method, url, params=params, headers=base_headers, json=json_body)
            if r.status_code in (403, 404):
                # 영구 실패 — retry 안 함
                r.raise_for_status()
            if r.status_code in RETRYABLE_STATUS:
                last_exc = httpx.HTTPStatusError(
                    f'retryable status {r.status_code}', request=r.request, response=r
                )
                # exponential backoff: 2, 4, 8...
                jitter_sleep(2 ** (attempt + 1))
                # UA rotate before retry
                base_headers['User-Agent'] = ua_rotation.pick(mobile=mobile_ua)
                continue
            return r
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
            last_exc = e
            jitter_sleep(1 + attempt)
            continue
    assert last_exc is not None
    raise last_exc
