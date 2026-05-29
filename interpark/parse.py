from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def build_mock(target_id: str, event_datetime: str, *, source_note: str = 'mock') -> dict[str, Any]:
    seats: list[dict[str, Any]] = []
    rows, cols = 10, 14
    for r in range(rows):
        row_label = chr(ord('A') + r)
        for c in range(1, cols + 1):
            grade = 'VIP' if r < 2 else ('R' if r < 5 else 'S')
            price = {'VIP': 190000, 'R': 150000, 'S': 110000}[grade]
            occupied = (r * cols + c) % 9 == 0
            seats.append({
                'id': f'{row_label}{c}',
                'row': row_label,
                'col': c,
                'grade': grade,
                'price': price,
                'status': 'occupied' if occupied else 'available',
            })
    return {
        'site': 'interpark',
        'externalEventId': target_id,
        'eventDatetime': event_datetime,
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'title': f'공연 {target_id}',
        'venue': '인터파크 공연',
        'seats': seats,
    }
