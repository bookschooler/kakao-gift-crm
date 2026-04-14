# 카카오 선물하기 CRM 분석

> **Kakao Gift** · RFM 세그먼트 기반 최적 CRM 전략 설계 및 비즈니스 시사점 도출

---

## 프로젝트 개요

카카오 선물하기 플랫폼의 유저 행동 데이터를 분석해 세그먼트별·이벤트별 최적 CRM 마케팅 전략을 설계한 포트폴리오 프로젝트입니다.
EDA → RFM → LTV/Cohort → K-factor 바이럴 루프 → Segment×Message 전략으로 이어지는 5단계 분석 파이프라인을 구성했습니다.

| 항목 | 내용 |
|---|---|
| 분석 대상 | 발신자 49,048명 |
| 데이터 테이블 | users, gift_receipts, orders, campaigns, campaign_logs |
| 분석 기간 | 2023.01 ~ 2024.12 (2년) |

---

## 핵심 결과

| 분석 | 주요 인사이트 |
|---|---|
| RFM 세그먼트 | Champions(8.8%)가 GMV의 16.1% 차지 → 이탈 1명이 가장 비싼 손실 |
| LTV 분석 | 12개월 LTV 203,169원 → CRM 목표는 단건 전환이 아닌 12개월 재구매 사이클 |
| K-factor | K=1.559 → 바이럴 이미 작동. CRM은 신규 획득보다 골든타임 30일 전환 가속에 집중 |
| 최적 CRM 조합 | At Risk × Discount(CVR 1.03%) vs Loyal × Ranking(0.24%) — 4.3배 차이 |
| Champions 전략 | Curation 메시지 → ROAS 837x (vs Ranking 메시지 CVR 3배 낮음) |

---

## 분석 파이프라인

EDA + STL 시계열 분해 → RFM 세그멘테이션 (5개 그룹) → LTV 분석 + 코호트 리텐션 → K-factor 바이럴 루프 분석 → Segment x Message CRM 전략 수립

---

## 폴더 구조

- `selfmade/analysis/` — Jupyter Notebook 5개 (01_eda ~ 05_crm_strategy)
- `selfmade/ppt_charts/` — 분석 결과 차트 이미지
- `selfmade/*.csv` — 시뮬레이션 데이터 (5개 테이블)
- `selfmade/generate_data.py` — 데이터 생성 스크립트

---

## 기술 스택

Python · pandas · numpy · scipy · statsmodels · matplotlib · seaborn · Jupyter Notebook

---

## CRM 전략 요약

| 세그먼트 | 최적 메시지 유형 | 근거 |
|---|---|---|
| Champions | Curation | ROAS 837x, block rate 최저 |
| At Risk | Discount 우선 | CVR 1.03% = 전체 최고 |
| Loyal | Curation 보조 | Ranking 대비 CVR 2.9배 |
| Hibernating | 계절성 가벼운 메시지 | ROAS 184x, 재진입 유도 |
| Dormant | 최소 리소스 | 규모 크지만 ROI 낮음 |

핵심 전략 전환: 경과일(D+N) 기반 → Occasion 기반
전환 트리거 1위 birthday(24.2%) → D-14 선제 발송으로 재설계

---

> 본 프로젝트는 공개 데이터 기반 시뮬레이션입니다. 분석 프레임워크 및 의사결정 로직 설계에 초점을 맞췄습니다.
