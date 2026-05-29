from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

TIMES = ['18:00', '18:30', '19:00', '19:30', '20:00', '20:30', '21:00']


def build_mock(target_id: str, event_datetime: str, *, source_note: str = 'mock') -> dict[str, Any]:
    slots = [
        {
            'time': t,
            'partySize': [2, 4],
            'available': (i * 7) % 3 != 0,
        }
        for i, t in enumerate(TIMES)
    ]
    return {
        'site': 'catchtable',
        'externalEventId': target_id,
        'eventDatetime': event_datetime,
        'capturedAt': datetime.now(timezone.utc).isoformat(),
        'title': f'식당 {target_id}',
        'venue': '캐치테이블',
        'maxCapacity': 6,
        'timeSlots': slots,
    }
