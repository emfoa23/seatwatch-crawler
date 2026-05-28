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
                        all_seats = snap.get('seats') or []
                        for seat in result['newly_available']:
                            for w in watches:
                                sel = w['seat_selector']
                                if not _seat_matches(sel, seat):
                                    continue
                                if isinstance(sel, dict) and sel.get('type') == 'multi' and not _check_adjacency(sel, seat, all_seats):
                                    continue
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
    """watch_targets.seat_selector matching (단일 좌석 단위).

    selector 예:
      {"type": "any"} — 아무 빈자리 발생 시 알림
      {"type": "seat", "id": "A1"} — 특정 자리
      {"type": "grade", "grade": "PREMIUM"} — 등급
      {"type": "row", "row": "A"} — 행
      {"type": "multi", "values": [...], "adjacency": N, "mode": "seat"} — 다중 후보

    (multi + adjacency>1 은 단일 좌석 단위에서 'candidate 인지' 만 판정.
    실제 연속 자리 확인은 별도 함수.)
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
    if t == 'multi':
        return seat.get('id') in (selector.get('values') or [])
    return False


def _check_adjacency(selector: dict[str, Any], seat: dict[str, Any], all_seats: list[dict[str, Any]]) -> bool:
    """multi + adjacency>1 에서 실제 연속 자리 확인.

    seat (행 row, 열 col) 기준으로 같은 행에서 N 개 연속 available 한 sliding window 가 있고,
    그 window 안에 seat.id 가 포함되어야 알림.
    """
    adj = int(selector.get('adjacency', 1) or 1)
    if adj <= 1:
        return True

    row = seat.get('row')
    col = seat.get('col')
    if row is None or col is None:
        return False

    same_row = [s for s in all_seats if s.get('row') == row]
    same_row.sort(key=lambda x: x.get('col', 0))
    # available 한 자리들의 col 모음
    avail_cols = sorted(s.get('col') for s in same_row if s.get('status') == 'available')
    # seat.col 을 포함하는 길이 adj 의 연속 구간이 있는지
    for start in range(len(avail_cols) - adj + 1):
        window = avail_cols[start:start + adj]
        if window[-1] - window[0] == adj - 1 and col in window:
            return True
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
