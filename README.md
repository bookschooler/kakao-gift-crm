# 카카오 선물하기 CRM 분석

> **Kakao Gift** · RFM 세그먼트 기반 최적 CRM 전략 설계 및 비즈니스 시사점 도출

---

## 프로젝트 개요

카카오 선물하기 플랫폼은 **선물→수신→재발신**의 바이럴 구조가 핵심입니다.  
이 프로젝트는 유저 행동 데이터를 분석해 세그먼트별 구매 동기와 바이럴 구조를 정량화하고,  
각 세그먼트에 최적화된 CRM 전략을 설계하는 것을 목표로 합니다.

EDA → RFM → LTV/Cohort → K-factor 바이럴 루프 → Segment×Message 전략으로 이어지는  
5단계 분석 파이프라인을 구성했습니다.

| 항목 | 내용 |
|---|---|
| 발신자 수 | 49,048명 (전체 코호트 / LTV 분석 기준) |
| RFM 분석 대상 | 44,713명 (2024년 구매 유저) |
| 데이터 테이블 | users, gift_receipts, orders, campaigns, campaign_logs |
| 분석 기간 | 2023.01 ~ 2024.12 (2년) |

---

## 핵심 결과

| 분석 | 주요 인사이트 |
|---|---|
| RFM 세그먼트 | Champions(8.8%)가 GMV의 16.1% 차지 → 이탈 1명이 가장 비싼 손실 |
| LTV 분석 | 12개월 LTV 203,169원 → CRM 목표는 단건 전환이 아닌 12개월 재구매 사이클 |
| K-factor | K=1.559 → 바이럴 이미 작동. CRM은 신규 획득보다 골든타임 30일 전환 가속에 집중 |
| 최적 CRM 조합 | At Risk × Discount(CVR 0.81%) vs Loyal Customers × Ranking(CVR 0.40%) — 2.0배 차이 |
| Champions 전략 | Curation 메시지 → ROAS 2,595x (ranking 대비 CVR 3배 높음) |
| 전략 시뮬레이션 | 3종 캠페인 기대 GMV 6.02억원 (K-factor 1.559 바이럴 승수 반영) |

---

## 분석 파이프라인

```
EDA + STL 시계열 분해
        ↓
RFM 세그멘테이션 (8개 그룹)
        ↓
LTV 분석 + 코호트 리텐션
        ↓
K-factor 바이럴 루프 분석
        ↓
Segment × Message CRM 전략 수립
```

---

## 폴더 구조

```
selfmade/
├── analysis/          # Jupyter Notebook 5개 (01_eda ~ 05_crm_strategy)
├── ppt_charts/        # 분석 결과 차트 이미지
├── *.csv              # 시뮬레이션 데이터 (5개 테이블)
└── generate_data.py   # 데이터 생성 스크립트
```

---

## 기술 스택

Python · pandas · numpy · scipy · statsmodels · matplotlib · seaborn · Jupyter Notebook

---

## CRM 전략 요약

| 세그먼트 | 최적 메시지 유형 | 근거 |
|---|---|---|
| Champions | Curation | ROAS 2,595x, block rate 최저 |
| At Risk | Discount 우선 | CVR 0.81% = discount 적용 세그먼트 중 최고 |
| Loyal Customers | Curation 보조 | Ranking 대비 CVR 2.9배 (0.49% vs 0.40%) |
| Hibernating | 계절성 가벼운 메시지 | 유저 수 1위(23.2%), 소량 재활성화로 유의미한 GMV 회수 가능 |
| Dormant | 최소 리소스 | 규모 크지만 ROI 낮음 |

**핵심 전략 전환: 경과일(D+N) 기반 → Occasion 기반**  
전환 트리거 1위 birthday(24.2%) → 앱 내 생일 등록 유도 + D-14 선제 발송으로 재설계

---

> 본 프로젝트는 공개 데이터 기반 시뮬레이션입니다. 분석 프레임워크 및 의사결정 로직 설계에 초점을 맞췄습니다.
