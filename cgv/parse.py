"""CGV 응답 → SeatSnapshot 정규화. 현재는 mock 빌더만 활용 (운영 endpoint 미확정)."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def build_mock(target_id: str, *, source_note: str = 'mock') -> dict[str, Any]:
    """web/lib/seat-mock.ts 의 mockSnapshot 와 동일 schema."""
    seats: list[dict[str, Any]] = []
    rows, cols = 8, 12
    for r in range(rows):
        row = chr(ord('A') + r)
        for c in range(1, cols + 1):
            grade = 'STANDARD' if r < 2 or r >= rows - 2 else 'STANDARD'
            if r >= rows - 2:
                grade = 'PREMIUM'
            price = 17000 if grade == 'PREMIUM' else 14000
            occupied = (r * cols + c) % 7 == 0 or (r * 31 + c * 13) % 11 == 0
            seats.append({
                'id': f'{row}{c}',
                'row': row,
                'col': c,
                'grade': grade,
                'price': price,
                'status': 'occupied' if occupied else 'available',
            })

    return {
        'site': 'cgv',
        'externalEventId': target_id,
        'eventDatetime': '2026-06-15T19:30:00+09:00',
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'title': f'CGV 영화 {target_id} (parser: {source_note})',
        'venue': 'CGV 용산아이파크몰 4DX 1관',
        'seats': seats,
    }


def normalize(raw: dict[str, Any], target_id: str) -> dict[str, Any]:
    """실제 CGV ajax response 를 받았을 때의 정규화 — 운영 endpoint 확정 후 채움."""
    raise NotImplementedError('CGV response parser — endpoint 확정 후 구현')
