"""seatwatch-crawler CLI.

사용:
  python main.py --site cgv --targets test
  python main.py --site cgv --targets test,duneXpart3

흐름:
  1. .env.local 로드
  2. crawl_jobs insert (status=running)
  3. 각 target 에 대해:
     - fetch seats (실패 시 mock fallback)
     - Valkey 직전 snapshot 조회 → diff
     - Valkey snapshot 갱신
     - Neon seat_events 적재
     - 활성 watch 매칭 → 빈자리 발생 시 notify queue push
  4. crawl_jobs finish (status=success/partial/failed)
"""
from __future__ import annotations
import argparse
import os
import sys
import traceback
from typing import Any

from common.env import load_env
from common import valkey_client, neon_client
from common.diff import diff_snapshots


def crawl_cgv(targets: list[str]) -> int:
    from cgv.fetch import fetch_seats

    rc = valkey_client.make_client()
    total_seats = 0
    seen_errors: list[str] = []

    with neon_client.connect() as conn:
        job_id = neon_client.start_job(conn, 'cgv', os.environ.get('GITHUB_RUN_ID'))
        try:
            for target in targets:
                try:
                    snap = fetch_seats(target)
                    old = valkey_client.get_snapshot(rc, 'cgv', target, snap['eventDatetime'])
                    result = diff_snapshots(old, snap)

                    valkey_client.set_snapshot(rc, snap)
                    neon_client.upsert_event_meta(conn, snap)
                    neon_client.insert_seat_events(conn, 'cgv', target, snap['eventDatetime'], result['changes'])

                    if result['newly_available']:
                        watches = neon_client.get_active_watches(conn, 'cgv', target, snap['eventDatetime'])
                        for seat in result['newly_available']:
                            for w in watches:
                                if _seat_matches(w['seat_selector'], seat):
                                    valkey_client.push_notification(rc, {
                                        'watch_id': str(w['watch_id']),
                                        'user_id': str(w['user_id']),
                                        'email': w['email'],
                                        'site': 'cgv',
                                        'event_id': target,
                                        'event_datetime': snap['eventDatetime'],
                                        'seat': seat,
                                        'dedupe_key': f"{w['watch_id']}:{seat['id']}",
                                    })
                    total_seats += len(snap.get('seats') or [])
                    print(f'[ok] cgv {target} — {len(snap.get("seats") or [])} seats, {len(result["changes"])} changes, {len(result["newly_available"])} newly_available')
                except Exception as exc:
                    seen_errors.append(f'{target}: {exc}')
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
    """watch_targets.seat_selector matching.

    selector 예:
      {"type": "any"} — 아무 빈자리 발생 시 알림
      {"type": "seat", "id": "A1"} — 특정 자리
      {"type": "grade", "grade": "PREMIUM"} — 등급
      {"type": "row", "row": "A"} — 행
    """
    if not isinstance(selector, dict):
        return False
    t = selector.get('type')
    if t == 'any':
        return True
    if t == 'seat':
        return selector.get('id') == seat.get('id')
    if t == 'grade':
        return selector.get('grade') == seat.get('grade')
    if t == 'row':
        return selector.get('row') == seat.get('row')
    return False


def main(argv: list[str]) -> int:
    load_env('.env.local')

    p = argparse.ArgumentParser(prog='seatwatch-crawler')
    p.add_argument('--site', required=True, choices=['cgv', 'interpark', 'catchtable'])
    p.add_argument('--targets', default='', help='Comma-separated target IDs (empty = all active watches)')
    args = p.parse_args(argv)

    targets = [t.strip() for t in args.targets.split(',') if t.strip()]
    if not targets:
        targets = ['test']  # MVP fallback

    if args.site == 'cgv':
        return crawl_cgv(targets)
    print(f'site {args.site} not yet implemented')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
