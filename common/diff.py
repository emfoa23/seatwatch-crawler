"""직전 snapshot 과 신규 snapshot 비교 → 변경 좌석 추출 + 빈자리(occupied→available) 식별."""
from __future__ import annotations
from typing import Any


def diff_snapshots(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """반환: {'changes': 모든 변경, 'newly_available': occupied → available}"""
    if not old or not new.get('seats'):
        return _from_timeslots(old, new)

    old_map = {s['id']: s for s in (old.get('seats') or [])}
    changes: list[dict[str, Any]] = []
    newly_available: list[dict[str, Any]] = []

    for s in new['seats']:
        prev = old_map.get(s['id'])
        prev_status = prev['status'] if prev else None
        if prev_status != s['status']:
            changes.append({'seat_id': s['id'], 'old': prev_status, 'new': s['status']})
            if prev_status == 'occupied' and s['status'] == 'available':
                newly_available.append(s)

    return {'changes': changes, 'newly_available': newly_available}


def _from_timeslots(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """캐치테이블 시간대용 — available 토글 감지."""
    if not new.get('timeSlots'):
        return {'changes': [], 'newly_available': []}
    old_map = {t['time']: t for t in (old.get('timeSlots') or [])} if old else {}
    changes: list[dict[str, Any]] = []
    newly_available: list[dict[str, Any]] = []
    for t in new['timeSlots']:
        prev = old_map.get(t['time'])
        prev_avail = prev['available'] if prev else None
        if prev_avail != t['available']:
            old_status = 'available' if prev_avail else 'occupied' if prev is not None else None
            new_status = 'available' if t['available'] else 'occupied'
            changes.append({'seat_id': t['time'], 'old': old_status, 'new': new_status})
            if prev_avail is False and t['available']:
                newly_available.append({'id': t['time'], **t})
    return {'changes': changes, 'newly_available': newly_available}
