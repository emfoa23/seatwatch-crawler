"""Crawler 가 어떤 target 을 호출할지 결정.

기본 정책: watch_targets 의 active 인 자리만 호출 (중복 minimize, IP 부담 최소).
인자 targets 있으면 그것만.
"""
from __future__ import annotations
import psycopg
from psycopg.rows import dict_row


def active_watch_targets(conn: psycopg.Connection, site: str) -> list[dict[str, str]]:
    """active 인 (externalEventId, eventDatetime) 중복 제거."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """SELECT DISTINCT external_event_id, event_datetime
               FROM watch_targets
               WHERE site=%s AND status='active'""",
            (site,),
        )
        rows = cur.fetchall()
    return [
        {'externalEventId': r['external_event_id'], 'eventDatetime': r['event_datetime'].isoformat()}
        for r in rows
    ]
