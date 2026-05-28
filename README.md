# seatwatch-crawler

[seatwatch](https://github.com/emfoa23/seatwatch) 의 좌석 데이터 수집 컴포넌트. CGV·인터파크 티켓·캐치테이블에서 좌석/시간대 가용성을 정기적으로 fetch 해서 Aiven Valkey snapshot + Neon `seat_events` 에 적재. 빈자리 감지 시 Valkey 알림 큐에 push.

**public repo 인 이유**: GitHub Actions 무료 분 무제한 사용 (private repo 는 월 2,000분 한도). 수집 코드 자체는 영업비밀 아님.

## 트리거

- **cron-job.org → workflow_dispatch** (Brian/monitor-infra 패턴 답습). GitHub Actions schedule 은 신뢰도 낮아 사용 안 함.
- 사이트별 별도 workflow + watch-poll workflow.

| Workflow | 주기 (cron-job.org) | 용도 |
|---|---|---|
| crawl-cgv.yml | 15분 | CGV 좌석 스냅샷 |
| crawl-interpark.yml | 15분 | 인터파크 좌석 (Playwright) |
| crawl-catchtable.yml | 15분 | 캐치테이블 시간대 가용성 |
| crawl-watch-poll.yml | 3분 | 활성 watch 등록된 마감 자리 빠른 폴링 |

## 구조

```
seatwatch-crawler/
├── main.py                     # CLI 진입점 (--site cgv --target ...)
├── cgv/                        # 사이트별 fetch + parse
├── interpark/                  # Playwright 기반
├── catchtable/                 # 공개 JSON API
├── common/
│   ├── valkey_client.py        # snapshot read/write (prefix seatwatch:prod:)
│   ├── neon_client.py          # seat_events insert · watch 매칭
│   ├── diff.py                 # 직전 snapshot diff → 빈자리 감지 → 큐 push
│   ├── ua_rotation.py          # UA 풀
│   └── backoff.py              # 429/403 백오프
├── requirements.txt
└── .github/workflows/
```

## 환경변수 (GitHub Secrets)

| 키 | 출처 |
|---|---|
| `DATABASE_URL` | Neon (seatwatch repo 와 공유) |
| `VALKEY_URL` | Aiven Valkey |
| `VALKEY_KEY_PREFIX` | `seatwatch:prod` (dev: `seatwatch:dev`) |
| `CRAWLER_USER_AGENT_POOL` | base64(JSON array of UAs) |
| `SENTRY_DSN` | (선택) Sentry |

GitHub PAT (cron-job.org 인증용) 은 cron-job.org 측에 등록, 본 repo 에는 보관 안 함.

## 봇 차단 대응

- UA rotation (Chrome 최신 5종)
- 요청 사이 jitter 0.5~2.0s
- 429/403 시 exponential backoff
- IP 차단 시 외부 proxy fallback (선택, 무료 trial)

## 법적 리스크

각 사이트 ToS 가 "자동화된 수단 접근 금지" 일반 조항 포함. **IP 차단·계정 차단·cease&desist 수신 위험** 인지하고 운영. cease&desist 수신 시 즉시 해당 사이트 크롤 중단.

## 데이터 스키마

`shared/types/seat.ts` (seatwatch repo) 와 일치하는 정규화된 JSON 으로 Valkey snapshot 적재:

```json
{
  "site": "cgv",
  "external_event_id": "<theater>:<movie>:<screen>",
  "event_datetime": "2026-06-01T19:30:00+09:00",
  "captured_at": "2026-06-01T17:15:23+09:00",
  "seats": [
    {"id": "A1", "row": "A", "col": 1, "grade": "STANDARD", "price": 14000, "status": "available"}
  ]
}
```

상세 설계는 seatwatch repo plan 문서 참조.
