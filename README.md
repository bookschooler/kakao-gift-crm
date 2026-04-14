# 카카오 선물하기 CRM 분석

> **Kakao Gift** · RFM 세그먼트 기반 최적 CRM 전략 설계 및 비즈니스 시사점 도출

---

## 프로젝트 개요

카카오 선물하기 플랫폼의 유저 행동 데이터를 분석해 **세그먼트별·이벤트별 최적 CRM 마케팅 전략**을 설계한 포트폴리오 프로젝트입니다.

"어떤 유저에게, 어떤 메시지를, 언제 보내야 전환율이 높아지는가?"라는 질문에 데이터 기반으로 답합니다.

EDA → RFM → LTV/Cohort → K-factor 바이럴 루프 → Segment×Message 전략으로 이어지는 **5단계 분석 파이프라인**을 구성했습니다.

| 항목 | 내용 |
|---|---|
| 분석 대상 | 발신자 49,048명 |
| 데이터 테이블 | users, gift_receipts, orders, campaigns, campaign_logs |
| 분석 기간 | 2023.01 ~ 2024.12 (2년) |
| 사용 언어 | Python |

---

## 배경 및 문제 정의

카카오 선물하기는 단순 커머스가 아닌 **관계 기반 소비 플랫폼**입니다. 발신자(Sender)가 수신자를 위해 선물을 구매하는 구조이기 때문에, 전통적인 커머스 CRM 전략을 그대로 적용하면 핵심 동기(occasion, 관계)를 놓치게 됩니다.

이 프로젝트에서 발견한 핵심 문제의식은 다음과 같습니다.

- 기존 CRM이 **D+N 경과일 기반**으로 설계되어 있어 실제 구매 트리거(생일, 기념일 등)를 선제적으로 공략하지 못함
- 세그먼트 구분 없이 동일 메시지를 발송 → Champions에게 Discount 메시지를 보내면 브랜드 가치 훼손 우려
- 바이럴(K-factor) 이미 작동 중임에도 불구하고 신규 획득에 마케팅 리소스가 집중되는 비효율 존재

---

## 데이터 구조 (ERD 요약)

```
users ──────────── orders ──────────── gift_receipts
  │                  │
  └── campaign_logs ──── campaigns
```

| 테이블 | 주요 컬럼 | 설명 |
|---|---|---|
| users | user_id, signup_date, gender, age_group | 발신자 유저 정보 |
| orders | order_id, user_id, amount, order_date | 구매 트랜잭션 |
| gift_receipts | receipt_id, order_id, occasion, receiver_id | 선물 수신 정보 및 occasion 태그 |
| campaigns | campaign_id, message_type, channel | 캠페인 메타 정보 |
| campaign_logs | log_id, user_id, campaign_id, sent_at, converted | 유저별 캠페인 발송·전환 로그 |

> 본 데이터는 실제 플랫폼 데이터가 아닌 **분석 프레임워크 검증을 위한 시뮬레이션 데이터**입니다.  
> `generate_data.py`에서 현실적인 분포(계절성, 코호트 리텐션 패턴 등)를 반영해 생성했습니다.

---

## 분석 파이프라인

```
01_eda_seasonal     →  02_rfm_segmentation  →  03_ltv_cohort
계절성·트렌드 파악       유저 그룹 분류           생애가치·코호트 분석
        ↓                                            ↓
04_viral_loop       ←──────────────────────  05_crm_strategy
바이럴 구조 분석                               전략 수립 및 우선순위화
```

### Step 01 · EDA + STL 시계열 분해

- 2년치 주문 데이터의 트렌드·계절성·잔차를 **STL(Seasonal-Trend decomposition using LOESS)** 분해로 분리
- 크리스마스·밸런타인데이·화이트데이·어버이날 등 **occasion 피크** 패턴 검증
- 요일별·시간대별 구매 패턴 분석 → 발송 최적 타이밍 도출

### Step 02 · RFM 세그멘테이션

- **RFM(Recency, Frequency, Monetary)** 지표 계산 후 Quintile 기반 스코어링
- 8개 세그먼트 분류: Champions / Loyal Customers / Can't Lose Them / At Risk / Potential Loyalists / Casual / New Customers / Dormant
- 세그먼트별 GMV 기여도·이탈 비용 산출

### Step 03 · LTV 분석 + 코호트 리텐션

- **LTV(Lifetime Value)** 12개월 기준 추정 → 평균 203,169원
- 코호트별 월별 리텐션 히트맵으로 이탈 구간 파악
- "CRM의 목표는 단건 전환이 아닌 12개월 재구매 사이클 유지"로 목표 재정의

### Step 04 · K-factor 바이럴 루프 분석

- **K-factor** = 발신자 1명이 만들어내는 신규 발신자 수
- K = 1.559 (K > 1 → 바이럴 자생적 성장 중)
- 수신자의 첫 발신 전환까지의 **골든타임이 30일** 이내임을 확인
- "신규 획득보다 골든타임 내 전환 가속"으로 CRM 방향 전환 근거 마련

### Step 05 · Segment × Message CRM 전략 수립

- 3가지 메시지 유형(Discount / Curation / Ranking) × 8개 세그먼트 = 24개 조합 CVR 비교
- 세그먼트별 최적 메시지·채널·발송 타이밍 매트릭스 설계
- Occasion 기반 재설계: 전환 트리거 1위 birthday(24.2%) → D-14 선제 발송 전략

---

## 핵심 발견

| 분석 | 주요 인사이트 |
|---|---|
| RFM 세그먼트 | Champions(8.8%)가 GMV의 16.1% 차지 → 이탈 1명이 가장 비싼 손실 |
| LTV 분석 | 12개월 LTV 203,169원 → CRM 목표는 단건 전환이 아닌 12개월 재구매 사이클 |
| K-factor | K=1.559 → 바이럴 이미 작동. 골든타임 30일 내 전환 가속이 최우선 과제 |
| 최적 CRM 조합 | At Risk × Discount(CVR 1.03%) vs Loyal × Ranking(0.24%) — **4.3배 차이** |
| Champions 전략 | Curation 메시지 → ROAS 837x (Ranking 메시지 대비 CVR 3배 높음) |

---

## CRM 전략 매트릭스

| 세그먼트 | 유저 비중 | GMV 기여 | 최적 메시지 | 핵심 근거 | 발송 타이밍 |
|---|---|---|---|---|---|
| Champions | 8.8% | 16.1% | Curation | ROAS 837x · block rate 최저 | Occasion D-14 선제 |
| Loyal Customers | 7.1% | 12.7% | Curation 보조 | Ranking 대비 CVR 2.9배 | Occasion D-7 |
| Can't Lose Them | 2.9% | 7.9% | Discount + 감성 메시지 | GMV 기여 높지만 이탈 위험 | 이탈 신호 감지 즉시 |
| At Risk | 2.4% | 1.9% | Discount 우선 | CVR 1.03% = 전체 최고 | 이탈 신호 감지 즉시 |
| Potential Loyalists | 13.4% | 13.2% | Curation 유도 | GMV 기여 잠재력 높음 | Occasion D-7 |
| Casual | 17.9% | 14.0% | 계절성 가벼운 메시지 | ROAS 184x · 재진입 유도 | 연간 피크 시즌 전 |
| New Customers | 3.0% | 1.1% | 온보딩 중심 | 바이럴 골든타임 30일 내 전환 | 가입 후 즉시 |
| Dormant | 44.5% | 33.2% | 최소 리소스 | 규모 크지만 ROI 낮음 | 대규모 이벤트 한정 |

**핵심 전략 전환:** 경과일(D+N) 기반 → **Occasion 기반**  
전환 트리거 1위 birthday(24.2%) → D-14 선제 발송으로 전략 재설계

---

## 비즈니스 시사점

**1. 고가치 유저 보호가 최우선**  
Champions 세그먼트는 전체의 8.8%에 불과하지만 GMV의 16.1%를 담당합니다. 이탈 방지 비용이 신규 획득 비용보다 훨씬 낮기 때문에, CRM 예산의 우선순위를 Champions 리텐션에 배분하는 것이 ROI(Return on Investment) 측면에서 유리합니다.

**2. 메시지 유형 미스매칭이 비용**  
Loyal 세그먼트에 Ranking 메시지를 발송하면 CVR이 Curation 대비 2.9배 낮습니다. 같은 발송 비용으로 3배 가까운 전환 차이가 발생하는 것으로, 세그먼트-메시지 매칭이 CRM 효율의 핵심 레버입니다.

**3. 바이럴 루프 활용 전략 전환**  
K=1.559는 자생적 성장이 이미 일어나고 있음을 의미합니다. 수신자가 발신자로 전환되는 골든타임(30일) 내에 경험을 강화하는 온보딩 CRM이 신규 유저 광고 획득보다 높은 효율을 낼 수 있습니다.

---

## 폴더 구조

```
kakao-gift-crm/
├── README.md
├── generate_data.py              # 시뮬레이션 데이터 생성 스크립트
├── erd.dbml                      # ERD 스키마 정의 (dbdiagram.io 호환)
│
├── notebooks/                    # 직접 작성한 Jupyter Notebook (분석 단계별)
│   ├── 01_eda_seasonal.ipynb     # EDA + STL 시계열 분해
│   ├── 02_rfm_segmentation.ipynb # RFM 세그멘테이션
│   ├── 03_ltv_cohort.ipynb       # LTV + 코호트 분석
│   ├── 04_viral_loop.ipynb       # K-factor 바이럴 루프
│   └── 05_crm_strategy.ipynb     # Segment × Message CRM 전략
│
├── analysis/                     # Python 스크립트 버전 (동일 분석, 재현용)
│   ├── 01_eda_seasonal.py
│   ├── 02_rfm_segmentation.py
│   ├── 03_ltv_cohort.py
│   ├── 04_viral_loop.py
│   └── 05_crm_strategy.py
│
├── data/                         # 시뮬레이션 데이터 (generate_data.py로 생성)
│   ├── users.csv
│   ├── orders.csv
│   ├── gift_receipts.csv
│   ├── campaigns.csv
│   └── campaign_logs.csv
│
└── assets/                       # 분석 결과 차트 이미지
```

---

## 실행 방법

```bash
# 1. 의존성 설치
pip install pandas numpy scipy statsmodels matplotlib seaborn jupyter

# 2. 시뮬레이션 데이터 생성
python generate_data.py

# 3. Jupyter Notebook 실행
jupyter notebook notebooks/
```

notebooks/ 폴더의 `01_`부터 순서대로 실행하면 전체 분석 파이프라인이 재현됩니다.

---

## 기술 스택

| 분류 | 사용 도구 |
|---|---|
| 데이터 처리 | Python · pandas · numpy |
| 통계 분석 | scipy · statsmodels |
| 시계열 분해 | statsmodels STL |
| 시각화 | matplotlib · seaborn |
| 개발 환경 | Jupyter Notebook |

---

> 본 프로젝트는 공개 데이터 기반 시뮬레이션입니다. 실제 카카오 데이터와 무관하며, 분석 프레임워크 및 의사결정 로직 설계 역량 시연에 초점을 맞췄습니다.
