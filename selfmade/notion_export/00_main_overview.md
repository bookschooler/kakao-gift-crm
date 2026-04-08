# 카카오톡 선물하기 데이터 분석 프로젝트

## 프로젝트 개요

카카오톡 선물하기 플랫폼의 사용자 행동 데이터를 분석하여 비즈니스 인사이트를 도출하는 포트폴리오 프로젝트.
5개 Phase로 구성: EDA → RFM 세그멘테이션 → LTV 분석 → 바이럴 루프 → CRM 전략

---

## 분석 구조 (5 Phases)

### Phase 1 — EDA & 시즌 분석
- GMV 추이, 시즌 효과, 카테고리 믹스 분석
- 핵심 발견: 2024 GMV ₩75.2억 (+29.7% YoY), 빼빼로데이 소액다량 vs 설날 고단가

### Phase 2 — RFM 세그멘테이션
- 9개 세그먼트 설계 (R/F 2×2 기반 + Champions/At Risk 분류)
- 핵심 발견: Champions가 전체 GMV의 44.3% 차지

### Phase 3 — LTV 코호트 분석
- 코호트별 Lifetime Value 산출 및 시즌 코호트 품질 비교
- 핵심 발견: M+11 LTV ₩203,169 (M+0 대비 2.7배), 시즌=비시즌 품질 동일

### Phase 4 — 바이럴 루프 분석
- K-factor, 상호성(Reciprocity), Occasion 트리거 분석
- 핵심 발견: K=1.559 (수정값), 자기선물 K=2.090 > 타인선물 1.515, Golden Time 30일

### Phase 5 — CRM 전략 수립
- A/B 테스트, ROAS 시뮬레이션, CRM 액션 플랜
- 핵심 발견: Champions ROAS 2,595배, 총 GMV ₩6.02억, curation CVR 12.73% vs ranking CTR 15.16%

---

## 데이터 구조 (5개 테이블)

| 테이블 | 설명 | 주요 컬럼 |
|--------|------|-----------|
| `orders` | 주문 트랜잭션 | order_id, user_id, amount, category, order_date |
| `users` | 사용자 정보 | user_id, join_date, gender, age_group |
| `gifts` | 선물 발송/수신 | gift_id, sender_id, receiver_id, occasion |
| `campaigns` | 캠페인 메타 | campaign_id, type, target_segment, start_date |
| `events` | 사용자 이벤트 로그 | event_id, user_id, event_type, timestamp |

---

## 핵심 지표 요약

| Phase | 지표 | 값 |
|-------|------|----|
| 1 | 2024 Total GMV | ₩75.2억 |
| 1 | YoY Growth | +29.7% |
| 1 | 빼빼로데이 AOV | ₩40,946 (소액다량) |
| 1 | 설날 AOV | ₩128,266 (고단가) |
| 1 | 수신→발신 전환율 | 97.9% |
| 2 | Champions GMV 비중 | 44.3% |
| 3 | M+11 LTV | ₩203,169 |
| 3 | LTV 성장 배수 | 2.7배 (M+0 대비) |
| 4 | K-factor (수정) | 1.559 |
| 4 | 자기선물 K-factor | 2.090 |
| 4 | Golden Time | 30일 |
| 4 | Pay-it-forward 비율 | 99.4% |
| 5 | 캠페인 Open Rate | 53.68% |
| 5 | 캠페인 CVR | 0.53% |
| 5 | Champions ROAS | 2,595배 |
| 5 | 총 캠페인 GMV | ₩6.02억 |

---

## 관련 파일
- `selfmade/PLAN.md` — Phase별 진행 계획
- `selfmade/analysis/` — Phase별 Python 분석 코드
- `report/kakao_gift_analysis.pptx` — DESA팀 PPT 보고서
- `kakao_gift_analysis_selfmade.pptx` — Selfmade PPT 보고서