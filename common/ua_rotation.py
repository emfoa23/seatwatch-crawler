"""User-Agent rotation + base64 환경변수 우선 사용."""
from __future__ import annotations
import base64
import json
import os
import random

DEFAULT_UAS: list[str] = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
]

MOBILE_UAS: list[str] = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-S928N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
]


def _load_env_pool() -> list[str]:
    raw = os.environ.get('CRAWLER_USER_AGENT_POOL', '').strip()
    if not raw:
        return []
    try:
        decoded = base64.b64decode(raw).decode('utf-8')
        parsed = json.loads(decoded)
        if isinstance(parsed, list):
            return [str(x) for x in parsed if x]
    except Exception:
        pass
    return []


def pick(mobile: bool = False) -> str:
    pool = _load_env_pool()
    if not pool:
        pool = MOBILE_UAS if mobile else DEFAULT_UAS
    return random.choice(pool)
