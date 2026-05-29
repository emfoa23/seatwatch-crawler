from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def build_mock(target_id: str, event_datetime: str, *, source_note: str = 'mock') -> dict[str, Any]:
    seats: list[dict[str, Any]] = []
    rows, cols = 8, 12
    for r in range(rows):
        row_label = chr(ord('A') + r)
        for c in range(1, cols + 1):
            grade = 'PREMIUM' if r >= rows - 2 else 'STANDARD'
            price = 16000 if grade == 'PREMIUM' else 13000
            occupied = (r * cols + c) % 7 == 0
            seats.append({
                'id': f'{row_label}{c}',
                'row': row_label,
                'col': c,
                'grade': grade,
                'price': price,
                'status': 'occupied' if occupied else 'available',
            })
    return {
        'site': 'megabox',
        'externalEventId': target_id,
        'eventDatetime': event_datetime,
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'title': f'메가박스 {target_id}',
        'venue': '메가박스',
        'seats': seats,
    }
