# 카카오톡 선물하기 프로젝트 지침

## 필수 참조 파일
이 프로젝트에서 작업 시작 전 반드시 읽을 것:
- `PLAN.md` — 전체 프로젝트 계획, 스키마 설계, 분석 Phase 상세, KPI 체계 전부 포함
- `data_schema_template.md` — 테이블 설계 원칙 (정규화/정합성/무결성/택소노미)

## 프로젝트 한 줄 요약
카카오톡 선물하기 마케팅팀 어시스턴트 JD 기반 포트폴리오.
RFM 세그멘테이션 + LTV 코호트 + Viral Loop 분석 → CRM 캠페인 전략 도출.

## 데이터 구조 (5개 테이블)
| 테이블 | 행 수 | 역할 |
|---|---|---|
| `users` | 50,000 | 유저 프로필. 파생값(total_sent_count 등) 없음 — orders/gift_receipts에서 집계 |
| `orders` | ~200,000 | 선물 주문(발신 기준). RFM의 R·M 원천 |
| `gift_receipts` | ~200,000 | 선물 수신 기록. orders와 1:1 |
| `campaigns` | ~48 | CRM 캠페인 기획 정보 |
| `campaign_logs` | ~120,000 | 캠페인 이벤트 로그 (send/open/click/block/purchase) |

## 핵심 설계 원칙 (PLAN.md 스키마 작업 시 준수)
- `users`는 정규화 — 파생값 raw 테이블에 넣지 않음
- 발신자 추적: `orders.sender_user_id` / 수신자 추적: `gift_receipts.receiver_user_id`
- occasion 3단 계층: `occasion_category(special/daily)` → `occasion_subcategory` → `gift_occasion(21개)`
- `gift_receipts.sent_at` 없음 — `orders.created_at`과 중복이므로 제거
- `order_status` = 결제 관점 / `receipt_status` = 수신자 행동 관점

## 분석 기간 및 기술 스택
- 분석 기간: 2023-01-01 ~ 2024-12-31
- BigQuery 데이터셋: `ds-ysy.kakao_gift`
- Python (pandas, scipy) + Jupyter Notebook + matplotlib

## 현재 진행 상태
- [x] PLAN.md 작성 완료 (스키마 + 분석 Phase + KPI 체계)
- [x] generate_data.py 작성 (50K 유저, ~200K 주문, 시즌 이벤트 반영)
- [x] BigQuery 업로드 (`ds-ysy.kakao_gift` 데이터셋, upload_to_bq.py)
- [x] 분석 노트북 작성 완료 (Phase 1~5, selfmade/analysis/*.ipynb)
  - [x] Phase 1: EDA & 시즌 분석 (`01_eda_seasonal.ipynb`)
  - [x] Phase 2: RFM 세그멘테이션 — 9 segments, Champions 8% → GMV 44% (`02_rfm_segmentation.ipynb`)
  - [x] Phase 3: LTV 코호트 — M+11 LTV ₩203,169, 시즌=비시즌 LTV 동등 검증 (`03_ltv_cohort.ipynb`)
  - [x] Phase 4: Viral Loop — K-factor 1.559, 44.1% 인과 전환율 (`04_viral_loop.ipynb`)
  - [x] Phase 5: CRM 전략 — A/B 테스트 설계, ROAS 137배 시뮬레이션 (`05_crm_strategy.ipynb`)
- [x] PPT 보고서 작성 (`kakao_gift_analysis_selfmade.pptx`)
- [x] Phase 2~5 면접 대비 Notion Q&A 업데이트 완료 (2026-04-09)
