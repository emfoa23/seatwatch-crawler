"""환경변수 로드 — .env.local 또는 process env."""
from __future__ import annotations
import os
from pathlib import Path


def load_env(path: str | Path = '.env.local') -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())


def require(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f'env var {name} is not set')
    return v
