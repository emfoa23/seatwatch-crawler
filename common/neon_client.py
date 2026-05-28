"""Neon Postgres — crawl_jobs · seat_events · events_meta · watch_targets 조회/적재."""
from __future__ import annotations
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator
import psycopg
from psycopg.rows import dict_row

from .env import require


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    url = require('DATABASE_URL')
    with psycopg.connect(url, row_factory=dict_row) as conn:
        yield conn


def start_job(conn: psycopg.Connection, site: str, run_id: str | None) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO crawl_jobs (site, run_id, status) VALUES (%s, %s, 'running') RETURNING id",
            (site, run_id),
        )
        row = cur.fetchone()
        conn.commit()
        return str(row['id'])


def finish_job(conn: psycopg.Connection, job_id: str, *, status: str, seats_fetched: int, error: str | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE crawl_jobs SET status=%s, seats_fetched=%s, error=%s, finished_at=now() WHERE id=%s",
            (status, seats_fetched, error, job_id),
        )
        conn.commit()


def upsert_event_meta(conn: psycopg.Connection, snapshot: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO events_meta (site, external_event_id, event_datetime, title, venue, last_crawl_at)
               VALUES (%s, %s, %s, %s, %s, now())
               ON CONFLICT (site, external_event_id, event_datetime)
               DO UPDATE SET title=EXCLUDED.title, venue=EXCLUDED.venue, last_crawl_at=now()""",
            (
                snapshot['site'],
                snapshot['externalEventId'],
                snapshot['eventDatetime'],
                snapshot.get('title'),
                snapshot.get('venue'),
            ),
        )
        conn.commit()


def insert_seat_events(conn: psycopg.Connection, site: str, event_id: str, event_datetime: str, diffs: list[dict[str, Any]]) -> None:
    if not diffs:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO seat_events (site, external_event_id, event_datetime, seat_id, old_status, new_status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [(site, event_id, event_datetime, d['seat_id'], d['old'], d['new']) for d in diffs],
        )
        conn.commit()


def get_active_watches(conn: psycopg.Connection, site: str, event_id: str, event_datetime: str) -> list[dict[str, Any]]:
    """해당 이벤트에 대한 활성 watch 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT wt.id as watch_id, wt.user_id, wt.seat_selector, u.email
               FROM watch_targets wt
               JOIN users u ON u.id = wt.user_id
               WHERE wt.site=%s AND wt.external_event_id=%s AND wt.event_datetime=%s
                 AND wt.status='active'""",
            (site, event_id, event_datetime),
        )
        return list(cur.fetchall())
