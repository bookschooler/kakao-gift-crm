---
title: "Knowledge Base 인덱스"
date: 2026-04-04
---

# Knowledge Base 인덱스

이 문서는 카카오톡 선물하기 CRM 분석의 모든 방법론과 자료를 검색하기 위한 인덱스입니다.

## 디렉토리 구조

```
knowledge/
├── INDEX.md (이 파일)
├── methodologies/
│   ├── eda_seasonality.md
│   ├── rfm_segmentation.md
│   ├── ltv_cohort.md
│   ├── viral_loop.md
│   └── crm_campaign.md
└── papers/
    └── REFERENCES.md
```

---

## 방법론별 가이드

### 1. Layer 1: EDA & 시즌 분석
**파일**: `methodologies/eda_seasonality.md`

**주요 내용**:
- STL (Seasonal-Trend Decomposition using LOESS)
- 시계열 분해: Trend + Seasonal + Residual
- Python 구현 코드 (statsmodels)
- ACF 검증, 피크 탐지
- 주의사항: period 설정, robust 옵션

**사용 시기**: 
- 데이터 탐색 초기 단계
- 시즌 이벤트(빼빼로데이 등) 영향 파악

**예상 시간**: 1~2주

---

### 2. Layer 2: RFM 세그멘테이션
**파일**: `methodologies/rfm_segmentation.md`

**주요 내용**:
- RFM (Recency-Frequency-Monetary)
- NTILE 5분위 스코어링
- 11개 세그먼트 정의 (Champions ~ Lost)
- SQL + Python 구현
- 안정성 검증 (Stability Test)

**사용 시기**:
- 고객 분류 및 세그멘테이션
- 세그먼트별 마케팅 전략 수립

**예상 시간**: 1주

**핵심 함수**:
```python
NTILE(5) OVER (ORDER BY recency)
NTILE(5) OVER (ORDER BY frequency DESC)
```

---

### 3. Layer 3: LTV & 코호트
**파일**: `methodologies/ltv_cohort.md`

**주요 내용**:
- Monthly Cohort Retention 계산
- Cumulative LTV (누적 고객 가치)
- Cohort Heatmap 시각화
- ANOVA로 안정성 검증
- Plateau 포인트 계산

**사용 시기**:
- 월별 신규 고객 성과 추적
- 이탈 패턴 분석
- LTV 벤치마킹

**예상 시간**: 1~2주

**핵심 SQL**:
```sql
DATE_TRUNC('month', MIN(created_at)) AS cohort_month
DATEDIFF(MONTH, cohort_month, purchase_month) AS month_offset
```

---

### 4. Layer 4: Viral Loop
**파일**: `methodologies/viral_loop.md`

**주요 내용**:
- K-factor (Viral Coefficient): i × c
- Reciprocity Index (N일 내 재발신)
- Referral Generation (세대별 감쇠)
- DAG (Directed Acyclic Graph) 추적
- Bootstrap CI 계산

**사용 시기**:
- 선물 고유 바이럴 루프 분석
- 수신자 → 발신자 전환율 측정
- 세대별 바이럴 효과 감쇠 파악

**예상 시간**: 2~3주

**핵심 개념**:
```
K = invites_per_user × conversion_rate
K > 1.0 → 자가 증식 성장
K ≈ 0.35 → Dropbox 수준
```

---

### 5. Layer 5: CRM 캠페인 & ROAS
**파일**: `methodologies/crm_campaign.md`

**주요 내용**:
- Segment Performance (CTR, CVR, Block Rate)
- ROAS 시뮬레이션
- Chi-Square Test (세그먼트 차이 검증)
- 최적 타겟팅 전략
- 피로도(Block Rate) 모니터링

**사용 시기**:
- 캠페인 전략 수립
- 세그먼트별 발송 최적화
- ROI 예측

**예상 시간**: 2주

**핵심 공식**:
```
ROAS = (Sends × CTR × CVR × AOV) / Cost
```

---

## 참고 자료

### 학술 논문
**파일**: `papers/REFERENCES.md`

**포함 내용**:
- Layer별 핵심 논문 (Hughes, Fader, Cleveland 등)
- 공식 문서 링크 (statsmodels, lifetimes, dbt)
- 업계 사례 (Dropbox, Braze, Klaviyo)
- 추천 학습 순서

---

## 빠른 검색 (Quick Search)

### 개념별

#### 시계열/시즌성
- `eda_seasonality.md`: STL Decomposition, LOESS
- `REFERENCES.md`: Cleveland (1990)

#### 고객 분류
- `rfm_segmentation.md`: RFM, NTILE, 11 segments
- `REFERENCES.md`: Hughes (1994)

#### 고객 수명 가치
- `ltv_cohort.md`: Cohort Retention, Cumulative LTV
- `crm_campaign.md`: CLV Prediction
- `REFERENCES.md`: Fader (2005), lifetimes library

#### 성장 & 네트워크
- `viral_loop.md`: K-factor, Reciprocity, Generation
- `REFERENCES.md`: Dropbox Case Study, Network Theory

#### 마케팅/ROI
- `crm_campaign.md`: ROAS, Segment Performance
- `REFERENCES.md`: Braze, Incrementality

### 도구/라이브러리별

#### Python
- STL: `statsmodels.tsa.seasonal.STL`
- RFM: `pandas.qcut()`, `NTILE()`
- Cohort: `pd.groupby()`, `pivot()`
- Viral: `networkx` (DAG)
- ROAS: `scipy.stats.chi2_contingency()`

#### SQL
- RFM: `NTILE(5) OVER ()`
- Cohort: `DATE_TRUNC()`, `DATEDIFF()`
- Funnel: `COUNT(CASE WHEN event_type = ...)`

#### 시각화
- Heatmap: `seaborn.heatmap()`
- Scatter: `matplotlib.scatter()`
- Line: `pandas.plot()`
- Bubble: `plt.scatter(s=...)`

### 통계 검증별

#### 자기상관
- ACF (Autocorrelation Function)
  → `statsmodels.graphics.tsaplots.plot_acf()`
  → 참고: `eda_seasonality.md`

#### 차이 검증
- Chi-Square Test
  → `scipy.stats.chi2_contingency()`
  → 참고: `crm_campaign.md`, `rfm_segmentation.md`

#### ANOVA
- F-test
  → `scipy.stats.f_oneway()`
  → 참고: `ltv_cohort.md`

#### 신뢰도
- Bootstrap CI
  → `scipy.stats.bootstrap()`
  → 참고: `viral_loop.md`

---

## 상황별 가이드

### "RFM 분석을 처음 한다"
1. `rfm_segmentation.md` 읽기
2. `REFERENCES.md`에서 Hughes (1994) 개념 확인
3. Python 코드 실행 → NTILE 스코어링
4. 세그먼트별 분포 확인

**예상 시간**: 2~3일

### "시즌 이벤트 영향을 파악하고 싶다"
1. `eda_seasonality.md` 읽기
2. STL 분해 실행
3. Seasonal component 플롯 확인
4. 피크 위치와 실제 이벤트 날짜 비교

**예상 시간**: 3~5일

### "고객 가치를 추적하고 싶다"
1. `ltv_cohort.md` 읽기
2. 월별 cohort 정의
3. Retention & LTV 계산
4. Cohort Heatmap 시각화

**예상 시간**: 1주

### "바이럴 루프를 검증하고 싶다"
1. `viral_loop.md` 읽기
2. Receiver 데이터 준비 (gift_receipts)
3. K-factor 계산
4. Reciprocity Index 추이 분석
5. Referral Generation DAG 구성

**예상 시간**: 2~3주

### "어느 고객에게 캠페인을 보낼지 결정하고 싶다"
1. `crm_campaign.md` 읽기
2. 세그먼트별 CTR/CVR 계산
3. ROAS 시뮬레이션
4. 최적 타겟 세그먼트 도출
5. Block Rate 모니터링

**예상 시간**: 2주

---

## FAQ

### Q: 어디서 시작해야 하나?
**A**: Layer 1 (EDA) → Layer 2 (RFM) → Layer 3 (LTV) → Layer 4 (Viral) → Layer 5 (CRM) 순서 권장

### Q: 한 번에 모두 구현해야 하나?
**A**: 아니오. 각 Layer는 독립적이므로, 우선순위에 따라 선택 가능.
- MVP: Layer 1~2 (3주)
- Full: Layer 1~5 (8~9주)

### Q: 방법론을 바꾸려면?
**A**: `METHODOLOGY_RESEARCH.md`의 "대안 비교" 섹션 참고. 변경 전 Researcher와 협의 권장.

### Q: 데이터가 가정과 다르면?
**A**: 각 `methodologies/*.md`의 "주의사항" 섹션 검토. 필요시 Researcher와 상의.

### Q: 코드를 어디서 찾나?
**A**: 각 `methodologies/*.md`의 "구현 코드" 섹션에 Python/SQL 템플릿 있음.

### Q: 논문을 더 읽고 싶으면?
**A**: `papers/REFERENCES.md`의 "추천 학습 순서" 섹션 참고.

---

## 파일 업데이트 이력

| 날짜 | 파일 | 변경사항 |
|---|---|---|
| 2026-04-04 | 전체 | Researcher Stage 1차 완성 |
| (예정) | 각 methodologies | Sophie 구현 피드백 반영 |
| (예정) | REFERENCES | 추가 논문 링크 |

---

## 라이센스 & 출처

모든 방법론은 학술 논문, 공식 문서, 업계 사례를 기반으로 작성되었습니다.
상세한 출처는 `papers/REFERENCES.md`를 참고하세요.

---

**Knowledge Base 유지보수**: DESA Researcher  
**최종 업데이트**: 2026-04-04
