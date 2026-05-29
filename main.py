"""seatwatch-crawler CLI.

사용:
  python main.py --site cgv [--targets <id1,id2>]

targets 미지정 시 watch_targets 의 active 인 자리만 crawl (IP 부담 최소).

흐름:
  1. .env.local 로드 (로컬), CI 에서는 환경변수 직접
  2. targets 결정 (active watches 또는 CLI 인자)
  3. crawl_jobs insert
  4. 각 target 에 대해 cooldown 체크 → fetch → snapshot + neon + diff + notify push
  5. crawl_jobs finish
"""
from __future__ import annotations
import argparse
import os
import sys
import traceback
from typing import Any, Callable

from common.env import load_env
from common import valkey_client, neon_client
from common.diff import diff_snapshots
from common.targets import active_watch_targets
from common.cooldown import should_skip


COOLDOWN_SEC = 120  # 같은 target 을 2분 안에 다시 호출하지 않음


def crawl(site: str, fetcher: Callable[[str, str], dict[str, Any]], targets: list[str] | None) -> int:
    rc = valkey_client.make_client()
    total_seats = 0
    seen_errors: list[str] = []

    with neon_client.connect() as conn:
        # 인자가 있으면 (externalEventId, eventDatetime='') 형식. 그러나 eventDatetime 없으면 정확히 fetch 못함.
        # → 인자 있을 때도 active watches 에서 매칭되는 row 의 eventDatetime 가져옴.
        watches = active_watch_targets(conn, site)
        if targets:
            allowed = set(targets)
            watches = [w for w in watches if w['externalEventId'] in allowed]
        if not watches:
            print(f'[skip] no active watches for site={site}')
            return 0

        job_id = neon_client.start_job(conn, site, os.environ.get('GITHUB_RUN_ID'))
        try:
            for w in watches:
                ext = w['externalEventId']
                dt = w['eventDatetime']
                try:
                    if should_skip(rc, site, ext, COOLDOWN_SEC):
                        print(f'[skip-cooldown] {site} {ext}')
                        continue
                    snap = fetcher(ext, dt)
                    old = valkey_client.get_snapshot(rc, site, ext, snap['eventDatetime'])
                    result = diff_snapshots(old, snap)

                    valkey_client.set_snapshot(rc, snap)
                    neon_client.upsert_event_meta(conn, snap)
                    neon_client.insert_seat_events(conn, site, ext, snap['eventDatetime'], result['changes'])

                    if result['newly_available']:
                        active = neon_client.get_active_watches(conn, site, ext, snap['eventDatetime'])
                        all_seats = snap.get('seats') or []
                        for seat in result['newly_available']:
                            for a in active:
                                sel = a['seat_selector']
                                if not _seat_matches(sel, seat):
                                    continue
                                if isinstance(sel, dict) and sel.get('type') == 'multi' and not _check_adjacency(sel, seat, all_seats):
                                    continue
                                valkey_client.push_notification(rc, {
                                    'watch_id': str(a['watch_id']),
                                    'user_id': str(a['user_id']),
                                    'email': a['email'],
                                    'site': site,
                                    'event_id': ext,
                                    'event_datetime': snap['eventDatetime'],
                                    'seat': seat,
                                    'dedupe_key': f"{a['watch_id']}:{seat.get('id', seat.get('time', 'na'))}",
                                })

                    total_seats += len(snap.get('seats') or snap.get('timeSlots') or [])
                    n = len(snap.get('seats') or snap.get('timeSlots') or [])
                    print(f'[ok] {site} {ext} — {n} items, {len(result["changes"])} changes, {len(result["newly_available"])} newly_available')
                except Exception as exc:
                    seen_errors.append(f'{ext}: {exc}')
                    traceback.print_exc()

            status = 'success' if not seen_errors else ('partial' if total_seats > 0 else 'failed')
            neon_client.finish_job(conn, job_id, status=status, seats_fetched=total_seats,
                                   error='; '.join(seen_errors) if seen_errors else None)
        except Exception as exc:
            neon_client.finish_job(conn, job_id, status='failed', seats_fetched=total_seats, error=str(exc))
            raise

    rc.close()
    return 0 if not seen_errors else 1


def _seat_matches(selector: Any, seat: dict[str, Any]) -> bool:
    if not isinstance(selector, dict):
        return False
    t = selector.get('type')
    if t == 'any':
        return True
    if t == 'seat':
        return selector.get('id') == seat.get('id')
    if t == 'time':
        return selector.get('time') == seat.get('time')
    if t == 'grade':
        return selector.get('grade') == seat.get('grade')
    if t == 'row':
        return selector.get('row') == seat.get('row')
    if t == 'multi':
        return seat.get('id', seat.get('time')) in (selector.get('values') or [])
    return False


def _check_adjacency(selector: dict[str, Any], seat: dict[str, Any], all_seats: list[dict[str, Any]]) -> bool:
    adj = int(selector.get('adjacency', 1) or 1)
    if adj <= 1 or selector.get('mode') != 'seat':
        return True
    row = seat.get('row')
    col = seat.get('col')
    if row is None or col is None:
        return False
    same_row = [s for s in all_seats if s.get('row') == row]
    avail_cols = sorted(s.get('col') for s in same_row if s.get('status') == 'available')
    for start in range(len(avail_cols) - adj + 1):
        window = avail_cols[start:start + adj]
        if window[-1] - window[0] == adj - 1 and col in window:
            return True
    return False


def main(argv: list[str]) -> int:
    load_env('.env.local')
    p = argparse.ArgumentParser(prog='seatwatch-crawler')
    p.add_argument('--site', required=True, choices=['cgv', 'megabox', 'lotte', 'interpark', 'catchtable'])
    p.add_argument('--targets', default='', help='Comma-separated externalEventId (empty = active watches)')
    args = p.parse_args(argv)

    targets = [t.strip() for t in args.targets.split(',') if t.strip()] or None

    if args.site == 'cgv':
        from cgv.fetch import fetch_seats as f
        return crawl('cgv', f, targets)
    if args.site == 'megabox':
        from megabox.fetch import fetch_seats as f
        return crawl('megabox', f, targets)
    if args.site == 'lotte':
        from lotte.fetch import fetch_seats as f
        return crawl('lotte', f, targets)
    if args.site == 'interpark':
        from interpark.fetch import fetch_seats as f
        return crawl('interpark', f, targets)
    if args.site == 'catchtable':
        from catchtable.fetch import fetch_timeslots as f
        return crawl('catchtable', f, targets)
    print(f'unknown site {args.site}')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
