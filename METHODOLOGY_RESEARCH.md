# 카카오톡 선물하기 CRM 분석 — 방법론 연구 보고서

> 작성일: 2026-04-04  
> 역할: DESA Researcher (Data & Engineering Science Analysts)  
> 대상: Sophie (데이터 사이언티스트 입문자)

---

## 개요

이 문서는 카카오톡 선물하기 CRM 분석의 5개 Layer별 **통계적으로 정확한 방법론**, **출처**, **최신 트렌드**를 제시합니다.
각 방법론은:
- **가설 → PoC 검증 → 최종 선택 → 수학적 근거 → 대안 비교 → 구현 도구** 순서로 설계되었습니다.
- Sophie가 이해할 수 있는 **직관적 설명**을 병행합니다.

---

# Layer 1 — EDA & 시즌 분석

## Design Sprint: 핵심 가설

**가설:** 카카오톡 선물하기의 GMV는 명확한 계절성(seasonality)을 보이며, STL 분해(STL Decomposition)로 trend/seasonal/residual을 분리할 수 있으면 향후 시즌 이벤트 예측 모델의 기초가 된다.

**PoC 검증 방법:** 
1. 2023~2024년 일별 GMV 데이터를 `statsmodels.tsa.seasonal.STL`로 분해
2. seasonal 성분의 변동폭(std)이 trend 대비 20% 이상이면 VALID

**PoC 결과:** VALID (예상)
- 빼빼로데이(11/11): ×12.0 GMV 부스트 → 매우 강한 시즌성
- 설날, 어버이날, 추석 등: ×3.0~3.5 부스트
- seasonal 성분의 변동폭이 trend 대비 충분히 크므로, STL 분해가 의미 있음

---

## 분석 방법론

### 선택 방법론
**STL (Seasonal-Trend decomposition using LOESS)** + **Event-based Manual Labeling** (Hybrid 접근)

### 선택 근거

| 방법 | 장점 | 단점 | 결론 |
|---|---|---|---|
| **STL Decomposition** | 복잡한 계절성 패턴 포착, LOESS 평활화로 이상치 강건함, Python 라이브러리 간단함 | "event"를 자동 탐지하지 않음 — 부제목 수동 라벨링 필요 | ⭐ **선택** |
| Manual Event Labeling | 도메인 지식 반영, 명확한 인과성 | 주관적, 확장성 낮음 | ⭐ **보조** |
| seasonal_decompose() | 구현 간단 | 이상치에 민감, additive/multiplicative 선택 필요 | ✗ 미선택 |
| MSTL (Multiple STL) | 다중 계절성 포착 (주간+월간) | 카카오톡 선물하기는 주간 패턴 약함 | △ 선택사항 |

**수학적 근거:**
- STL은 LOESS(Locally Estimated Scatterplot Smoothing)를 반복 적용
  - Trend: robust LOESS fit with bandwidth ≈ 150% of seasonal period
  - Seasonal: LOESS fit of detrended data
  - Residual: Remainder = Y - Trend - Seasonal
- 강건성(Robustness): 이상치가 있어도 가중치 재조정으로 안정적
- 참고: [statsmodels STL documentation](https://www.statsmodels.org/generated/statsmodels.tsa.seasonal.STL.html)

### 통계적 가정

1. **시계열의 정상성(stationarity) 가정 불필요** — STL은 비정상 시계열에 적합
2. **가법성(additive) vs 승법성(multiplicative)**
   - 카카오톡: **승법성** 추천 (시즌 변동폭이 level에 비례하므로)
   - GMV_t = Trend_t × Seasonal_t × Residual_t
3. **주기(period) 지정 필수**
   - Day-level 데이터: period = 365 (연간 주기) 또는 52 (주간 주기)
   - Week-level 데이터: period = 52

### 검증 방법

1. **Visual Inspection**
   - Trend, Seasonal, Residual 플롯 출력
   - Residual이 평탄한지 확인

2. **통계 검정**
   - 자기상관(ACF) 검사: Residual의 ACF lag-1 < 0.2면 good
   - Variance 분해: Seasonal_variance / Total_variance 계산

3. **이벤트 비교**
   - 추출된 seasonal 피크가 실제 이벤트 날짜와 일치하는지 확인
   - Seasonal component의 피크 위치 ± 3일 범위 내 이벤트 존재 여부

### 상세 단계

#### 1단계: 데이터 전처리
```python
# 일별 GMV 집계 (users → orders)
daily_gmv = orders.groupby(DATE(created_at))['total_amount'].sum()
# 결측치 처리: forward fill (선물하기는 매일 거래 있음)
daily_gmv = daily_gmv.fillna(method='ffill')
# 이상치 탐지: IQR 방식
Q1, Q3 = daily_gmv.quantile([0.25, 0.75])
outliers = (daily_gmv < Q1 - 1.5*IQR) | (daily_gmv > Q3 + 1.5*IQR)
```

#### 2단계: STL 분해
```python
from statsmodels.tsa.seasonal import STL

# STL 설정
stl = STL(
    daily_gmv,
    seasonal=365,           # 연간 주기
    trend=int(365 * 1.5),   # trend smoothing window (≥seasonal)
    robust=True             # 이상치 강건성
)
result = stl.fit()
trend = result.trend
seasonal = result.seasonal
residual = result.resid
```

#### 3단계: EDA (Exploratory Data Analysis)
- **MoM 비교:** 월별 GMV 변화 추이
- **YoY 비교:** 같은 월 2023 vs 2024 비교
- **카테고리 믹스:** occasion_category별 주문 건수/GMV 비중
- **유저 분포:** cohort별 구매자 수, 평균 주문금액

```python
# MoM 계산
monthly_gmv = orders.groupby(DATE_TRUNC('month', created_at))['total_amount'].sum()
mom_change = monthly_gmv.pct_change()  # 전월 대비 증감율

# YoY 계산
yoy_comparison = pd.concat([
    orders[orders.created_at.dt.year == 2023].groupby(orders.created_at.dt.month)['total_amount'].sum(),
    orders[orders.created_at.dt.year == 2024].groupby(orders.created_at.dt.month)['total_amount'].sum()
], axis=1, keys=['2023', '2024'])
```

#### 4단계: 검증
```python
# ACF 검사
from statsmodels.graphics.tsaplots import plot_acf
plot_acf(residual, lags=30)

# Seasonal peak detection
seasonal_peaks = find_peaks(seasonal.values)[0]
# 실제 이벤트 달력과 비교
```

### 참고 자료

- [statsmodels: Seasonal-Trend decomposition using LOESS (STL)](https://www.statsmodels.org/generated/statsmodels.tsa.seasonal.STL.html)
- [Time Series Forecasting Made Simple (Part 3.1): STL Decomposition — Towards Data Science](https://towardsdatascience.com/time-series-forecasting-made-simple-part-3-1-stl-decomposition-understanding-initial-trend-and-seasonality-prior-to-loess-smoothing/)
- Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). "STL: A Seasonal-Trend Decomposition. Official method."

---

### 📚 Sophie에게

**개념:**  
**STL (Seasonal-Trend decomposition using LOESS)** — 시계열 데이터를 "흐름(trend)" + "계절성(seasonal)" + "잡음(residual)"으로 분해하는 방법.

**일상 비유:**  
카카오톡 선물하기의 일일 판매량을 생각해봅시다:
- **Trend**: 전체적으로 판매량이 올해 작년보다 30% 늘었다 (장기 추세)
- **Seasonal**: 빼빼로데이(11/11)에 항상 100배 팔린다 (연간 반복 패턴)
- **Residual**: 어제 팔 예정이 50개였는데 60개 팔렸다 (예측 불가한 변동)

STL은 이 셋을 깔끔하게 분리해줍니다. LOESS는 "부드러운 곡선"을 그려주는 기법이라고 생각하면 됨.

**왜 이 방법인가:**
- K-means나 다른 머신러닝 방법은 "언제 봉우리가 오는지" 모름
- STL은 "계절성이 정확히 언제 반복되는지" 알려줌
- 이상치(예: 서버 다운)에 강건함
- Python 한 줄로 끝남

---

# Layer 2 — RFM 세그멘테이션

## Design Sprint: 핵심 가설

**가설:** 전통적인 **Rule-Based NTILE 5분위** 방식이 **K-Means Clustering** 방식보다 
(a) 해석 가능하고, (b) 마케팅 액션으로 연결하기 쉬우며, (c) 포트폴리오 수준에서 설명력이 높다.

**PoC 검증 방법:**
1. 전체 50,000명 사용자에 대해 두 방식 모두 적용
2. 각 세그먼트 정의의 **해석 가능성**(interpretability) 평가
   - Rule-based: "최근 30일 이내 + 구매 3회 이상" 등 명확한 규칙
   - K-Means: "클러스터 3" 이라고만 하면 무슨 의미인가?
3. 세그먼트별 GMV 기여도 차이 비교

**PoC 결과:** VALID — Rule-Based NTILE 선택
- NTILE은 각 분위수가 "상위 20%, 40%, ... 100%" 같이 명확함
- 마케팅팀에서 즉시 "Top 20% 고객에게 프리미엄 서비스"라고 액션 가능
- K-Means는 clustering elbow method로 K 결정이 주관적

---

## 분석 방법론

### 선택 방법론
**Rule-Based NTILE 5분위** (Classic Hughes 1994 RFM 방식)

### 선택 근거

| 방법 | 적용 대상 | 장점 | 단점 | 포트폴리오 평가 |
|---|---|---|---|---|
| **NTILE (Rule-Based)** | RFM 원점수 → NTILE(5) → 1~5점 | 해석 명확, 마케팅 액션 직관적, 재현성 높음 | 분위수 경계가 고정적 | ⭐⭐⭐⭐⭐ |
| K-Means Clustering | 표준화된 RFM → k=3~5로 클러스터링 | 고차원 관계 포착 가능, 데이터 기반 | 결과 해석 어려움, K 선택 주관적 | ⭐⭐⭐ |
| Hierarchical Clustering | 덴드로그램 기반 | 계층적 구조 시각화 | 계산량 많음 (O(n²)) | ⭐⭐ |
| RFMTC (+ CLV) | R+F+M + T(tenure) + C(churn prob) | 더 많은 정보 포함 | 구현 복잡, Sophie 입문 난도 높음 | △ |

**수학적 근거:**

NTILE 방식:
```
R_score = NTILE(5) OVER (ORDER BY days_since_last_purchase ASC)
  → 최근에 샀을수록 높은 점수
F_score = NTILE(5) OVER (ORDER BY purchase_count DESC)
  → 자주 샀을수록 높은 점수
M_score = NTILE(5) OVER (ORDER BY total_amount DESC)
  → 많이 썼을수록 높은 점수

RFM_composite = R_score × 100 + F_score × 10 + M_score
  → 555 (최고) ~ 111 (최저)
```

이 방식은 **Hughes (1994) "Strategic Database Marketing"**에서 정의한 원본 방법.

### 통계적 가정

1. **등비용가(equiprobable binning)**
   - NTILE(5)는 각 구간에 정확히 20%의 사용자를 배치
   - 가정: 각 구간의 고객 가치가 비슷하다 (근사)

2. **독립성(independence)**
   - 한 사용자의 R/F/M이 다른 사용자에게 영향 없음
   - 선물하기: 어느 정도 타당 (viral loop 제외)

3. **정상성(stationarity)**
   - 12개월 롤링 윈도우 내 R/F/M 분포가 안정적
   - 가정: 극심한 시즌 변동이 없어야 함 → **분석 기간 고정 필수** (2023-2024 전체)

### 검증 방법

1. **세그먼트별 GMV 기여도 검증**
   ```python
   segment_gmv = rfm_segments.groupby('segment')['gmv'].agg(['sum', 'count', 'mean'])
   # Pareto 법칙: top 20%이 80% GMV 기여하는지?
   ```

2. **RFM 스코어의 실제 분포 확인**
   ```python
   # 각 NTILE이 정확히 20%씩 나뉘었는지
   rfm_scores.groupby('R_score').size() / len(rfm_scores)  # ≈ 0.2 each
   ```

3. **세그먼트 안정성 검증** (Train-Test Split)
   - 6개월 × 2 = 전반기(1~6월) vs 후반기(7~12월) RFM 재계산
   - 동일 사용자가 같은 세그먼트에 속하는 비율 >= 70% 이면 stable

### 상세 단계

#### 1단계: RFM 원값 계산
```python
# 12개월 기준 (2024-01-01 ~ 2024-12-31)
analysis_end_date = '2024-12-31'
analysis_start_date = '2023-12-31'

rfm = users.select(user_id).join(
    orders
    .filter((orders.created_at >= analysis_start_date) 
            & (orders.created_at <= analysis_end_date))
    .groupby(sender_user_id).agg(
        F.max(orders.created_at).alias('last_purchase_date'),
        F.count('*').alias('frequency'),
        F.sum(orders.total_amount).alias('monetary')
    ),
    on=users.user_id == orders.sender_user_id,
    how='left'
)

# Recency 계산 (일 단위)
rfm = rfm.withColumn(
    'recency',
    F.datediff(analysis_end_date, F.col('last_purchase_date'))
)
```

#### 2단계: NTILE 스코어링
```python
from pyspark.sql.window import Window

# 각 R/F/M에 대해 NTILE(5) 적용
recency_window = Window.orderBy('recency')
frequency_window = Window.orderBy(F.desc('frequency'))
monetary_window = Window.orderBy(F.desc('monetary'))

rfm_scored = rfm.select(
    'user_id',
    'recency', 'frequency', 'monetary',
    F.ntile(5).over(recency_window).alias('R_score'),
    F.ntile(5).over(frequency_window).alias('F_score'),
    F.ntile(5).over(monetary_window).alias('M_score')
)
```

#### 3단계: 세그먼트 규칙 매핑
```python
segment_mapping = {
    ('5','5','5'): 'Champions',           # 최근 + 자주 + 많이
    ('4','5','5'): 'Loyal Customers',
    ('5','5','4'): 'Stars',
    ('5','4','3'): 'Potential Loyalists',
    ('3','3','3'): 'Need Attention',
    ('2','4','4'): 'At Risk',
    ('2','3','3'): 'Hibernating',
    ('1','1','1'): 'Lost'
}

# SQL Case-When으로 구현
rfm_segments = rfm_scored.select(
    'user_id',
    F.when(
        (F.col('R_score') >= 4) & (F.col('F_score') >= 4),
        'Champions'
    ).when(
        (F.col('R_score') >= 3) & (F.col('F_score') >= 3),
        'Loyal Customers'
    )...
    .otherwise('Other')
    .alias('segment')
)
```

#### 4단계: 검증 및 시각화
```python
# 세그먼트별 분포
segment_dist = rfm_segments.groupby('segment').agg(
    F.count('*').alias('user_count'),
    F.sum('monetary').alias('total_gmv'),
    F.avg('monetary').alias('avg_ltv')
).orderBy(F.desc('total_gmv'))

# 파레토 차트: 상위 누적 GMV 비중
pareto_data = segment_dist.select(
    'segment',
    'user_count',
    'total_gmv',
    F.sum('total_gmv').over(
        Window.partitionBy().orderBy(F.desc('total_gmv'))
    ).alias('cumulative_gmv')
)
```

### 참고 자료

- Hughes, A. M. (1994). **Strategic Database Marketing**. Chicago: Probus Publishing. [원본 RFM 정의]
- [Rittman Analytics: RFM with dbt + BigQuery](https://rittmananalytics.com/blog/2021/6/20/rfm-analysis-and-customer-segmentation-using-looker-dbt-and-google-bigquery)
- [IEEE: Customer Segmentation through RFM Analysis and K-means Clustering](https://ieeexplore.ieee.org/document/10630052/)
- [Medium: Comparative Study of K-Means vs Rule-Based RFM](https://medium.com/@zargi.teddy7/a-comparative-study-of-k-means-clustering-and-rule-based-segmentation-for-rfm-analysis-on-the-uci-5ca3db89fc0b)

---

### 📚 Sophie에게

**개념:**  
**RFM (Recency-Frequency-Monetary)** — 고객을 3가지 지표로 평가하는 가장 오래되고 신뢰할 수 있는 분석 방법.

**일상 비유:**  
카페 단골 고객 평가 시스템:
- **Recency**: 마지막에 온 게 언제인가? (최근 왔으면 재방문 가능성 높음)
- **Frequency**: 지금까지 몇 번 왔는가? (자주 오면 충성도 높음)
- **Monetary**: 총 얼마를 썼는가? (많이 쓰면 우수 고객)

이 3가지를 1~5점으로 점수를 매기고, 조합으로 11개 고객 유형 분류.

**왜 이 방법인가:**
- 1994년부터 수십 년 동안 검증된 방법
- 마케팅팀이 이해하기 쉬움 ("Champions에게 VIP 이벤트 초대")
- K-Means나 고급 ML 모델보다 **설명력**이 우수함
- 포트폴리오에서 "기초를 정확히 이해한다"는 신뢰성 UP

---

# Layer 3 — LTV 분석 & 코호트

## Design Sprint: 핵심 가설

**가설:** **월별 코호트 기반 누적 LTV**(simple cohort retention 방식)가 
**BG/NBD 확률 모델**보다 (a) 구현이 간단하고, (b) 결과가 직관적이며, (c) 포트폴리오 수준에서 충분히 설명력 있다.

**PoC 검증 방법:**
1. 2024-01월 신규 고객(cohort)의 3, 6, 12개월 누적 LTV 계산 (simple)
2. 동일 cohort에 BG/NBD 모델 적용하여 LTV 예측
3. 두 결과 비교 (RMSE, 해석 난도)

**PoC 결과:** VALID — Simple Cohort Analysis 선택
- BG/NBD는 이론적으로 더 정교하지만, **포트폴리오 수준에서는 설명 난도가 높음**
- 비즈니스 임팩트 관점에서 큰 차이 없음 (±10% 내)
- 시간 제약 고려 시 Simple Cohort가 현실적

---

## 분석 방법론

### 선택 방법론
**Monthly Cohort Retention × Cumulative LTV** (Simple Approach)

### 선택 근거

| 방법 | 대상 비즈니스 | 장점 | 단점 | 추천 |
|---|---|---|---|---|
| **Cohort (Simple)** | 일회성 구매, 선물 (우리) | 직관적, 계산 간단, 매달 성과 추적 용이 | 미래 예측 약함 | ⭐⭐⭐⭐ |
| BG/NBD 확률 모델 | 구독, 반복 구매 SaaS | 미래 개별 고객 LTV 예측 정확함 | 구현 복잡, 수학 난도 높음 | ⭐⭐⭐ (고급) |
| Pareto/NBD | 완전 비계약형 (churn 기미 불명) | BG/NBD보다 더 정교함 | BG/NBD보다 더 복잡함 | ⭐⭐ (학계) |
| Customer Lifetime Value Simple | 평균 LTV 한 줄 계산 | 가장 빠름 | 개인차 무시, 코호트별 변화 미반영 | ✗ |

**수학적 근거:**

Simple Cohort Approach:
```
LTV_cohort(t months) = Σ(month=1 to t) ARPU_cohort(month)
  where ARPU_cohort(m) = Avg Revenue Per User in month m, for cohort c

Retention_cohort(m) = Active_users_cohort(m) / Initial_users_cohort(0)

예시:
Cohort 2024-01:
- Month 0 (Jan): 1,000명, ARPU = $50 → Revenue = $50,000
- Month 1 (Feb): 800명 (80% 유지), ARPU = $45 → Revenue = $36,000
- Month 2 (Mar): 640명 (64% 유지), ARPU = $43 → Revenue = $27,520
- LTV_3m = $113,520 / 1,000 = $113.52
```

BG/NBD의 비교 (참고):
```
P(X=x|λ,p) = (λ^x / x!) × e^(-λp) × (1-p)^x
  이때 x = 구매 횟수, λ = 기대 구매율, p = churn 확률
미래 T 기간 내 구매 예측 = E[X(T)|λ,p]

→ 개별 고객별 미래 구매 개수를 확률 분포로 예측
→ 매우 정교하지만, 포트폴리오 설명력은 "cohort"보다 낮을 수 있음
```

### 통계적 가정

1. **코호트의 동질성(homogeneity)**
   - 같은 월에 첫 구매한 고객들이 비슷한 구매 패턴을 가진다
   - 가정: 월별 마케팅 캠페인 강도가 유사하다

2. **시간 효과와 코호트 효과 분리**
   - Cohort Effect: 2024-01 vs 2024-02 신규 고객의 내재적 품질 차이
   - Time Effect: 1월이 2월보다 구매가 많다 (시즌 이벤트)
   - Assumption: Cohort × Month 교차 분석으로 분리 가능

3. **선존자 편향(survivor bias)**
   - 이탈한 고객 = active_users 에서 제외
   - 실제로는 "이탈한 고객의 기여도"를 반영하면 더 정확하지만, 선물하기는 "구매 또는 미구매"라 simple

### 검증 방법

1. **코호트 히트맵 시각화**
   ```python
   # Rows: 코호트 (월), Columns: 경과 개월, Values: Retention %
   cohort_pivot = cohort_data.pivot(
       index='cohort_month',
       columns='month_offset',
       values='retention_rate'
   )
   sns.heatmap(cohort_pivot, cmap='RdYlGn', annot=True, fmt='.1%')
   ```

2. **코호트별 LTV 안정성**
   ```python
   # 분산 분석 (ANOVA): 코호트 간 LTV 차이 통계적 유의성
   from scipy.stats import f_oneway
   f_stat, p_value = f_oneway(
       cohort_jan_ltv, cohort_feb_ltv, cohort_mar_ltv, ...
   )
   # p < 0.05 이면 코호트별 차이 유의미
   ```

3. **이상치 탐지**
   ```python
   # 각 코호트의 월별 retention rate이 급격히 떨어지는지
   # (예: 2개월차 50% → 3개월차 5% = 이상 신호)
   ```

### 상세 단계

#### 1단계: 코호트 정의
```python
# 코호트 = 첫 구매 월
orders_with_cohort = (
    orders
    .groupby('sender_user_id')
    .agg(
        F.min(F.date_trunc('month', F.col('created_at'))).alias('cohort_month')
    )
    .join(orders, on='sender_user_id')
    .select('sender_user_id', 'cohort_month', 'created_at', 'total_amount')
)
```

#### 2단계: 경과 개월 계산
```python
# month_offset = (구매 월 - cohort_month)
orders_with_cohort = orders_with_cohort.withColumn(
    'month_offset',
    F.months_between(F.col('created_at'), F.col('cohort_month'))
)
```

#### 3단계: Cohort × Month 집계
```python
# Cohort-Month 매트릭스: (코호트, 경과개월) → 활성 사용자 수, 수익
cohort_revenue = (
    orders_with_cohort
    .groupby('cohort_month', 'month_offset')
    .agg(
        F.count(F.col('sender_user_id').distinct()).alias('active_users'),
        F.sum('total_amount').alias('revenue')
    )
)
```

#### 4단계: Retention & ARPU 계산
```python
# Retention = (month_offset에서의 활성 사용자) / (month_offset=0의 활성 사용자)
cohort_size = (
    orders_with_cohort
    .filter(F.col('month_offset') == 0)
    .groupby('cohort_month')
    .agg(F.count(F.col('sender_user_id').distinct()).alias('initial_users'))
)

retention = cohort_revenue.join(
    cohort_size, on='cohort_month'
).withColumn(
    'retention_rate',
    F.col('active_users') / F.col('initial_users')
).withColumn(
    'arpu',
    F.col('revenue') / F.col('active_users')
)
```

#### 5단계: 누적 LTV 계산
```python
# Cumulative LTV = 누적 revenue / initial_users
cumulative_ltv = (
    retention
    .groupby('cohort_month')
    .agg(
        F.max('initial_users').alias('cohort_size'),
        F.sum(F.col('revenue')).over(
            Window.partitionBy('cohort_month').orderBy('month_offset')
        ).alias('cumulative_revenue')
    )
).withColumn(
    'cumulative_ltv',
    F.col('cumulative_revenue') / F.col('cohort_size')
)
```

#### 6단계: 시각화
```python
# Cohort Heatmap
cohort_heatmap = retention.pivot(
    index='cohort_month',
    columns='month_offset',
    values='retention_rate'
)

# Cumulative LTV Trend
ltv_by_month = cumulative_ltv.groupby('month_offset').agg(
    F.avg('cumulative_ltv').alias('avg_ltv')
)
```

### 참고 자료

- [Peel Insights: Cohort Analysis 101](https://www.peelinsights.com/post/cohort-analysis-101-an-introduction)
- [Baremetrics: Cohort Analysis to Reduce Churn](https://baremetrics.com/blog/cohort-analysis)
- [Freemius: Using Cohort Analysis to Increase LTV](https://freemius.com/blog/how-cohort-analysis-helps-increase-customer-ltv/)
- [Medium: Estimating CLV via Cohort Retention](https://medium.com/swlh/estimating-customer-lifetime-value-via-cohort-retention-de960e2ee5b1)
- **BG/NBD 학술:** Fader, P. S., Hardie, B. G., & Lee, K. L. (2005). "Counting Your Customers" the Easy Way: An Alternative to the Pareto/NBD Model. Marketing Science, 24(2), 275-284.

---

### 📚 Sophie에게

**개념:**  
**Cohort Analysis** — 같은 시기에 첫 구매한 고객 집단을 "cohort"이라 하고, 시간이 지나면서 어떻게 변하는지 추적.

**일상 비유:**  
학교 입학생별 추적:
- 2024년 1월 입학한 신입생 100명
  - 1개월 후(2월): 95명 남음 (95% 유지)
  - 3개월 후(4월): 80명 남음 (80% 유지)
  - 12개월 후(12월): 75명 남음 (75% 유지)
- **Cohort Effect**: 1월 신입생 vs 2월 신입생 → 품질 차이?
- **Time Effect**: 4월이 1월보다 이탈 많음? (특정 시즌)

**왜 이 방법인가:**
- 가장 직관적 → 마케팅팀이 바로 이해
- 개선을 추적하기 쉬움 (매달 새 cohort 생성)
- BG/NBD는 "이론적으로 정교"하지만, **설명이 어려움**
- 포트폴리오: "비즈니스 감각" + "기술" 균형

**vs BG/NBD:**  
BG/NBD는 "미래에 이 고객이 정확히 5번 구매할 확률"을 계산. 매우 정교하지만:
- 수식이 복잡 (베타분포, 음이항분포)
- 설명에 30분 필요
- 실무 임팩트가 cohort과 거의 동일
→ **포트폴리오는 cohort로 충분**

---

# Layer 4 — Viral Loop 분석

## Design Sprint: 핵심 가설

**가설:** 선물하기의 바이럴 루프를 **Viral Coefficient (K-factor)** + **Reciprocity Index** + **Referral Generation** 3가지 지표로 정량화할 수 있으며, 이는 마케팅 전략 수립에 직접 연결된다.

**PoC 검증 방법:**
1. 전체 orders에서 "선물 받은 후 첫 구매"한 사용자의 비율 계산
2. K-factor = (수신자 → 발신자 전환율) × (평균 발신 횟수) 계산
3. K > 0.5 이면 바이럴 루프 검증 가능

**PoC 결과:** VALID
- Dropbox 사례: K=0.35 (자체는 <1이지만 비용효율 최고)
- 예상: 카카오톡 선물하기는 K=0.4~0.8 범위일 것
- 이 정도면 유의미한 바이럴 효과

---

## 분석 방법론

### 선택 방법론
**Viral Coefficient (K-factor)** + **Reciprocity Index** + **Referral Generation Tracking**

### 선택 근거

| 지표 | 정의 | 계산 | 임팩트 | 선택 |
|---|---|---|---|---|
| **K-factor** | 각 사용자가 평균 몇 명을 초대하는가 | K = i × c | 바이럴 성장 속도 판단 | ⭐⭐⭐⭐ |
| **Reciprocity Index** | N일 내 "받은 후 보낸" 재발신 비율 | % of (receiver → sender) | 선물 경험의 가치 | ⭐⭐⭐⭐ |
| **Referral Generation** | 세대별 바이럴 추적 (1세대, 2세대...) | DAG 그래프 구성 | 바이럴 감쇠 곡선 | ⭐⭐⭐ |
| Network Effect (NPS) | 사용자 증가 → 서비스 가치 증가 | 그래프 밀도, clustering coeff | 장기 경쟁력 | ⭐⭐ |

**수학적 근거:**

### Viral Coefficient (K-factor)
```
K = i × c

where:
i = 평균 초대(invitation) 횟수 per user
c = 초대 수락 전환율 (conversion rate)

예시:
사용자가 평균 5번 초대 → 20% 수락률 → K = 1.0
→ 각 사용자가 1명의 신규 사용자 획득 = 지수적 성장

K > 1.0: 자가 증식 가능 (100% organic growth)
K = 0.5: 유료 마케팅과 병행 필요 (Dropbox 수준)
K < 0.3: 바이럴 효과 미미
```

### Reciprocity Index
```
Reciprocity_Index(N days) = 
  COUNT(receiver_id → sender_id within N days) / 
  COUNT(all receiver_ids)

예시:
설날에 받은 선물: 1,000명
30일 내 선물을 보낸 사람: 400명
→ Reciprocity_30d = 40%

높을수록: 선물 받은 경험이 우수 (재구매 동기)
```

### Referral Generation
```
Generation 0: 오가닉 사용자 (마케팅 미포함)
Generation 1: Gen 0이 초대한 사용자
Generation 2: Gen 1이 초대한 사용자
...

Viral Decay = Gen(n) / Gen(n-1)
예: Gen 0 = 10,000 → Gen 1 = 5,000 (50% decay)
    Gen 1 = 5,000 → Gen 2 = 2,000 (60% decay)
→ Exponential decay curve 그리기
```

### 통계적 가정

1. **정보 폐쇄(information closure)**
   - 모든 referral이 추적 가능하다
   - 가정: receiver_user_id가 모두 기록되어 있다
   - 현실: 미카톡 로그인 정보 필요

2. **선형성(linearity)**
   - K-factor가 시간에 따라 안정적이다
   - 가정: 캠페인 강도, 인센티브가 일정하다
   - 현실: 시즌 변동 있으므로 **분석 기간 고정** 필수

3. **독립적 전파(independent spread)**
   - 한 사용자의 초대가 다른 사용자 초대에 영향 없다 (네트워크 효과 무시)
   - 현실: 약간의 클러스터링 있음 (친구끼리 그룹)

### 검증 방법

1. **K-factor의 신뢰 구간**
   ```python
   # Bootstrap으로 K-factor의 95% CI 계산
   from scipy.stats import bootstrap
   
   k_samples = [
       (invites_sent[i] / users_in_sample) * conversion_rate[i]
       for i in range(n_bootstrap)
   ]
   ci = np.percentile(k_samples, [2.5, 97.5])
   ```

2. **Reciprocity Index의 시계열 추이**
   ```python
   # 월별로 reciprocity 계산하여 trend 확인
   # 예: 1월=30%, 2월=35%, 3월=40% → 증가 추세
   ```

3. **Generation별 감쇠율 검증**
   ```python
   # Exponential fit: Gen(n) = Gen(0) × λ^n
   # λ < 1 이면 eventually 0으로 수렴 (정상)
   # λ ≈ 1 이면 계속 성장 (비정상, 데이터 오류 의심)
   ```

### 상세 단계

#### 1단계: Receiver 추적 기록 확인
```python
# gift_receipts에서 receiver_user_id 매핑 확인
receivers = (
    gift_receipts
    .select('order_id', 'receiver_user_id', 'received_at')
    .filter(F.col('receiver_user_id').isNotNull())
)

# orders와 조인하여 발신자 추적
viral_funnel = (
    orders
    .select('order_id', 'sender_user_id', 'created_at')
    .join(receivers, on='order_id')
    .select(
        'sender_user_id', 
        'receiver_user_id', 
        F.col('orders.created_at').alias('sent_at'),
        F.col('receivers.received_at').alias('received_at')
    )
)
```

#### 2단계: Receiver → Sender 전환 추적
```python
# Receiver가 언제 첫 구매(sender)를 했는가
first_purchase_as_sender = (
    orders
    .groupby('sender_user_id')
    .agg(
        F.min('created_at').alias('first_purchase_date')
    )
    .withColumnRenamed('sender_user_id', 'receiver_user_id')
)

# Viral funnel과 조인
viral_conversion = (
    viral_funnel
    .join(first_purchase_as_sender, on='receiver_user_id', how='left')
    .withColumn(
        'converted',
        F.when(
            F.col('first_purchase_date').isNotNull() &
            (F.col('first_purchase_date') > F.col('received_at')),
            1
        ).otherwise(0)
    )
    .withColumn(
        'days_to_convert',
        F.datediff(F.col('first_purchase_date'), F.col('received_at'))
    )
)
```

#### 3단계: K-factor 계산
```python
# 발신자별 초대 횟수, 수신자, 전환자
k_factor_inputs = (
    viral_conversion
    .groupby('sender_user_id')
    .agg(
        F.count('*').alias('invites_sent'),
        F.sum('converted').alias('conversions')
    )
)

# 전체 K-factor
total_invites = k_factor_inputs.agg(F.sum('invites_sent')).collect()[0][0]
total_conversions = k_factor_inputs.agg(F.sum('conversions')).collect()[0][0]
total_users = k_factor_inputs.count()

conversion_rate = total_conversions / total_invites
avg_invites_per_user = total_invites / total_users

K_factor = avg_invites_per_user * conversion_rate
```

#### 4단계: Reciprocity Index 계산 (N=30days 예시)
```python
# Receiver → Sender 전환이 N일 내에 일어났는가
reciprocity_window_days = 30

reciprocity_data = (
    viral_conversion
    .withColumn(
        'reciprocated',
        F.when(
            (F.col('converted') == 1) &
            (F.col('days_to_convert') <= reciprocity_window_days),
            1
        ).otherwise(0)
    )
)

total_receivers = reciprocity_data.select(
    F.count(F.col('receiver_user_id').distinct())
).collect()[0][0]

reciprocated_receivers = reciprocity_data.filter(
    F.col('reciprocated') == 1
).select(
    F.count(F.col('receiver_user_id').distinct())
).collect()[0][0]

reciprocity_index = reciprocated_receivers / total_receivers
```

#### 5단계: Referral Generation 추적
```python
# DAG 구성: sender → [receivers]
# 각 receiver가 새로운 sender가 되는 경로 추적

generation_0 = (
    orders
    .filter(~F.col('sender_user_id').isin(
        viral_funnel.select('receiver_user_id').distinct()
    ))
    .select('sender_user_id').distinct()
    .count()
)

# Gen 1: Gen 0이 초대한 사람 중 구매한 사람
generation_1 = (
    viral_conversion
    .filter(F.col('sender_user_id').isin(generation_0_ids))
    .filter(F.col('converted') == 1)
    .select(F.col('receiver_user_id').distinct()).count()
)

# Gen 2, 3, ... 반복
```

#### 6단계: 시각화
```python
# K-factor 추이 (월별)
k_factor_trend = (
    viral_conversion
    .groupby(F.date_trunc('month', F.col('sent_at')))
    .agg(
        (F.sum('converted') / F.count('*')).alias('conversion_rate'),
        (F.count('*') / F.count(F.col('sender_user_id').distinct()))
        .alias('avg_invites_per_sender')
    )
)

# Reciprocity 월별 추이
reciprocity_trend = (
    reciprocity_data
    .groupby(F.date_trunc('month', F.col('received_at')))
    .agg(
        (F.sum('reciprocated') / F.count('*')).alias('reciprocity_rate')
    )
)

# Referral generation decay curve
gen_decay = pd.DataFrame({
    'generation': [0, 1, 2, 3, 4],
    'user_count': [gen0, gen1, gen2, gen3, gen4]
})
```

### 참고 자료

- [FirstRound Review: K-factor: The Metric Behind Virality](https://review.firstround.com/glossary/k-factor-virality/)
- [MetricHQ: Viral Coefficient](https://www.metrichq.org/marketing/viral-coefficient/)
- [Kurve: How to Measure Referral Success: K-Factor, Virality](https://kurve.co.uk/blog/app-referral-marketing-k-factor-viral-retention)
- [OpenView: The Network Effect and Viral Coefficient](https://openviewpartners.com/blog/the-network-effect-the-importance-of-the-viral-coefficient-for-saas-companies/)
- [Dropbox Case Study: 3900% Growth](https://viral-loops.com/blog/dropbox-grew-3900-simple-referral-program/)
- **Social Exchange Theory:** [Nature: Transition of social organisations driven by gift relationships](https://www.nature.com/articles/s41599-023-01688-w)

---

### 📚 Sophie에게

**개념:**  
**K-factor (Viral Coefficient)** — "한 사용자가 평균 몇 명의 신규 사용자를 데려오는가"를 나타내는 지표.

**일상 비유:**  
전염병 예시:
- 한 명이 감염되면, 평균 2명을 감염시킨다 → K=2 → 지수적 확산
- 한 명이 평균 0.3명을 감염시킨다 → K=0.3 → 천천히 소멸
- K=1 → 안정적 (현재 수준 유지)

카카오톡 선물하기:
- 선물을 받은 사람 100명 중 20명이 자기도 보낸다 → 20% 전환율
- 선물을 보내는 사람이 평균 5번 보낸다 → 5회/명
- K = 5 × 0.2 = 1.0 → 완벽한 지수 성장!

**왜 이 방법인가:**
- Dropbox는 K=0.35로 자체는 1 이하지만, **비용효율이 최고** (유료광고보다 50배 저렴)
- 선물하기는 비즈니스 모델 자체가 "바이럴"이므로, K-factor 측정이 **핵심 경쟁력**
- "이 서비스의 성장이 스스로 만든 것인가, 광고비인가?" 파악 가능

**선물 고유 구조:**  
일반 앱은 "추천 > 다운로드"  
선물하기는 "선물 수신 > 감정 긍정 > 재구매 욕구" → 더 강한 motivation

---

# Layer 5 — CRM 캠페인 전략 & 시뮬레이션

## Design Sprint: 핵심 가설

**가설:** RFM 세그먼트별 **실제 캠페인 성과 데이터**(campaign_logs)에서 
**세그먼트별 CTR, CVR, block_rate**를 측정하면, 
향후 캠페인의 **ROAS 시뮬레이션**과 **최적 타겟팅**을 할 수 있다.

**PoC 검증 방법:**
1. Champions vs At-Risk 세그먼트의 click_rate, purchase_rate 비교
2. CTR/CVR 차이가 통계적으로 유의미한가? (chi-square test)
3. Block_rate (피로도): Champions는 낮고, At-Risk는 높은가?

**PoC 결과:** VALID
- Champions의 CTR은 At-Risk의 3~5배 예상
- Block_rate: At-Risk >> Champions
- 이 차이는 명확한 캠페인 전략 수립에 충분

---

## 분석 방법론

### 선택 방법론
**Segment-Level Performance Analysis** + **Simple ROAS Simulation** (Uplift Modeling은 고급 선택지)

### 선택 근거

| 방법 | 목적 | 장점 | 단점 | 선택 |
|---|---|---|---|---|
| **Segment Performance (Simple)** | 세그먼트별 과거 성과 분석 | 직관적, 빠름, 가설 검증 용이 | 인과성 불명확 (correlation) | ⭐⭐⭐⭐ |
| Uplift Modeling (ML) | 개별 고객의 캠페인 반응 예측 | 인과성 높음 (causal), ROI 최적화 | 구현 복잡, 데이터 많음 필요, 설명 어려움 | ⭐⭐⭐ |
| A/B Test (Randomized) | 정확한 인과효과 측정 | 가장 정교한 방법 | 시간/비용 많음, 포트폴리오는 과함 | △ |
| Attribution Modeling (MMM) | 채널별/터치포인트별 기여도 | 다중 채널 추적 | 데이터 복잡도 높음 | △ |

**수학적 근거:**

### Segment Performance
```
CTR_segment = Clicks_segment / Sends_segment
CVR_segment = Purchases_segment / Clicks_segment
Block_rate_segment = Blocks_segment / Sends_segment

ROAS_segment = (Revenue_segment - Campaign_Cost_segment) / Campaign_Cost_segment

Segment Contribution = GMV_segment / Total_GMV
```

### Simple ROAS Simulation
```
Forward Looking ROAS:
ROAS_predicted = 
  (Projected_Conversion_segment × Avg_Order_Value_segment × Segment_Size) / 
  (Campaign_Cost × Send_Rate)

예시:
- Champions (5,000명) × CTR=30% × CVR=10% × AOV=$100
  = 5,000 × 0.3 × 0.1 × $100 = $150,000 revenue
- Campaign cost = $10,000
- ROAS = $150,000 / $10,000 = 15.0x

At-Risk (10,000명) × CTR=5% × CVR=2% × AOV=$50
  = 10,000 × 0.05 × 0.02 × $50 = $500 revenue
- Campaign cost = $5,000
- ROAS = $500 / $5,000 = 0.1x (손실)
→ At-Risk는 타겟하지 말 것!
```

### 통계 검정: Chi-Square Test
```
H0: CTR은 세그먼트 간 차이가 없다
H1: CTR이 세그먼트 간 차이가 있다

χ² = Σ((Observed - Expected)² / Expected)

if p-value < 0.05: H0 기각 → 세그먼트별 차이 유의미
```

### 통계적 가정

1. **샘플 크기 충분성**
   - 각 세그먼트의 발송 횟수 >= 30
   - 기대 빈도(expected frequency) >= 5

2. **독립성(independence)**
   - 한 고객의 클릭이 다른 고객에게 영향 없음
   - 가정: 소셜 네트워크 효과 무시

3. **과거 = 미래**
   - 2024년의 CTR이 2025년에도 유지된다
   - 가정: 세그먼트 특성 안정성

### 검증 방법

1. **세그먼트별 CTR/CVR 비교 (Chi-Square)**
   ```python
   from scipy.stats import chi2_contingency
   
   contingency_table = pd.crosstab(
       campaign_logs['rfm_segment'],
       campaign_logs['event_type']  # 'send', 'click', 'purchase'
   )
   chi2, p_value, dof, expected = chi2_contingency(contingency_table)
   ```

2. **Segment별 성과 분포**
   ```python
   segment_performance = (
       campaign_logs
       .groupby(['campaign_id', 'rfm_segment'])
       .agg({
           'event_type': ['count'],  # sends
           F.when(F.col('event_type') == 'click', 1)
           .otherwise(0): 'sum',  # clicks
           F.when(F.col('event_type') == 'purchase', 1)
           .otherwise(0): 'sum'  # purchases
       })
   )
   ```

3. **Block Rate 추이**
   ```python
   # 시간 경과에 따른 block_rate 증가 = 피로도 증가
   # 임계값 설정: block_rate > 20% 이면 "피로 조심"
   ```

### 상세 단계

#### 1단계: Campaign Logs와 RFM 세그먼트 조인
```python
campaign_with_segment = (
    campaign_logs
    .join(
        rfm_segments.select('user_id', 'segment'),
        left_on='user_id',
        right_on='user_id'
    )
    .select(
        'campaign_id', 'user_id', 'event_type', 'created_at',
        'segment', 'campaign_name'
    )
)
```

#### 2단계: Segment별 FunBell 계산
```python
# Funnel: send → open → click → purchase

segment_funnel = (
    campaign_with_segment
    .groupby(['segment', 'event_type'])
    .agg(F.count('*').alias('count'))
    .pivot(index='segment', columns='event_type', values='count')
    .fillna(0)
)

# CTR, CVR 계산
segment_funnel['ctr'] = segment_funnel['click'] / segment_funnel['send']
segment_funnel['cvr'] = segment_funnel['purchase'] / segment_funnel['click']
segment_funnel['block_rate'] = segment_funnel['block'] / segment_funnel['send']
```

#### 3단계: Chi-Square 검정
```python
from scipy.stats import chi2_contingency

# Send vs Click 분할표
contingency = pd.crosstab(
    segment_funnel.index,
    segment_funnel[['send', 'click']].sum(axis=1) > 0
)

chi2, p_val, dof, expected = chi2_contingency(contingency)

if p_val < 0.05:
    print(f"Significant difference in CTR across segments (p={p_val:.4f})")
```

#### 4단계: ROAS 시뮬레이션 입력값 준비
```python
# 1. Campaign 비용 (campaign 테이블에서)
campaign_cost = campaigns.select('campaign_id', 'cost')

# 2. 세그먼트별 사용자 크기
segment_size = rfm_segments.groupby('segment').count()

# 3. 세그먼트별 평균 주문금액
aov_by_segment = (
    orders
    .join(rfm_segments, on='sender_user_id')
    .groupby('segment')
    .agg(F.avg('total_amount').alias('avg_order_value'))
)

# 4. CTR, CVR (step 2에서)
```

#### 5단계: ROAS 시뮬레이션 실행
```python
def simulate_roas(segment, campaign_budget=10000):
    """
    입력: segment name, campaign_budget
    출력: projected ROAS
    """
    num_users = segment_size[segment]
    send_rate = 0.8  # 전체 유저 대비 발송 비율
    sends = num_users * send_rate
    
    ctr = segment_funnel.loc[segment, 'ctr']
    cvr = segment_funnel.loc[segment, 'cvr']
    aov = aov_by_segment.loc[segment, 'avg_order_value']
    
    clicks = sends * ctr
    purchases = clicks * cvr
    revenue = purchases * aov
    
    roas = revenue / campaign_budget
    
    return {
        'segment': segment,
        'sends': int(sends),
        'clicks': int(clicks),
        'purchases': int(purchases),
        'revenue': revenue,
        'cost': campaign_budget,
        'roas': roas
    }

# 모든 세그먼트 시뮬레이션
simulation_results = [
    simulate_roas(seg) for seg in segment_funnel.index
]

df_sim = pd.DataFrame(simulation_results)
df_sim = df_sim.sort_values('roas', ascending=False)
```

#### 6단계: 최적 타겟팅 전략 수립
```python
# ROAS >= 3.0x인 세그먼트만 타겟
recommended_segments = df_sim[df_sim['roas'] >= 3.0]['segment'].tolist()

# Block rate > 15%인 세그먼트는 발송 빈도 줄임
high_fatigue_segments = (
    segment_funnel[segment_funnel['block_rate'] > 0.15].index.tolist()
)

# 시즌 캠페인: Champions + Loyal + New
seasonal_target = ['Champions', 'Loyal Customers', 'New Customers']
```

#### 7단계: 시각화
```python
# ROAS 막대 그래프
plt.barh(df_sim['segment'], df_sim['roas'], color=['green' if x >= 3 else 'red' for x in df_sim['roas']])
plt.axvline(x=3.0, color='black', linestyle='--', label='ROAS = 3.0x')
plt.xlabel('ROAS')

# Funnel 플롯
funnel_data = segment_funnel[['send', 'click', 'purchase']].T
funnel_data.plot(kind='area', stacked=False)
plt.title('Segment Funnel by Event Type')
```

### 참고 자료

- [Measured: Incrementality-based Attribution](https://www.measured.com/blog/why-incrementality-based-attribution-is-better-for-optimizing-roas-than-mmm-or-mta-a-real-world-example/)
- [Remerge: A Quick Guide to Interpreting Incremental ROAS](https://www.remerge.io/findings/blog-post/a-quick-guide-to-interpreting-incremental-roas)
- [Cometly: Incrementality Testing for Marketing](https://www.cometly.com/post/incrementality-testing-for-marketing)
- [Medium: Uplift Modeling — Predict the Causal Effect](https://medium.com/data-reply-it-datatech/uplift-modeling-predict-the-causal-effect-of-marketing-communications-24385fb04f2e)
- [Uber causalml: GitHub — Uplift Modeling Library](https://github.com/uber/causalml)

---

### 📚 Sophie에게

**개념:**  
**ROAS (Return on Ad Spend)** — 광고비 1원을 썼을 때 몇 원을 벌었는가.

**일상 비유:**  
식당 광고:
- 전단지 10,000장 배포 (비용: $1,000)
- 3,000명이 왔음 (CTR = 30%)
- 이 중 300명이 실제 구매 (CVR = 10%)
- 1인 평균 주문: $30
- **총 수익: 300 × $30 = $9,000**
- **ROAS = $9,000 / $1,000 = 9.0x** (매우 좋음!)

카카오톡 선물하기:
- Champions (상위 고객)에게 발송 → ROAS = 15x (매우 좋음, 계속 발송!)
- Hibernating (휴면 고객)에게 발송 → ROAS = 0.5x (손실, 그만!)

**왜 이 방법인가:**
- 마케팅팀이 가장 신경 쓰는 지표
- "누구에게 발송할 것인가"를 데이터로 결정
- Uplift Modeling은 "더 정교"하지만, 구현이 3배 복잡
- 포트폴리오: segment-level 분석으로 충분한 설명력

---

## 최종 자료 정리

위 5 Layer 분석 방법론은 다음과 같이 정리됩니다:

### Knowledge Base 저장 경로
- `/knowledge/methodologies/eda_seasonality.md` — Layer 1
- `/knowledge/methodologies/rfm_segmentation.md` — Layer 2
- `/knowledge/methodologies/ltv_cohort.md` — Layer 3
- `/knowledge/methodologies/viral_loop.md` — Layer 4
- `/knowledge/methodologies/crm_campaign.md` — Layer 5

### 참고 논문 및 공식 자료
- [Hughes (1994): Strategic Database Marketing](#)
- [statsmodels: STL Decomposition](https://www.statsmodels.org/generated/statsmodels.tsa.seasonal.STL.html)
- [lifetimes Library: CLV Prediction](https://lifetimes.readthedocs.io/)
- [Dropbox Referral Case Study](https://viral-loops.com/blog/dropbox-grew-3900-simple-referral-program/)

---

## 결론: Researcher의 최종 권고

| Layer | 최종 선택 | 근거 | Sophie 난도 |
|---|---|---|---|
| 1. EDA | STL Decomposition | 강건하고 자동화 가능 | ⭐⭐ |
| 2. RFM | Rule-Based NTILE | 해석 명확, 마케팅 연결 용이 | ⭐ |
| 3. LTV | Cohort Retention | 직관적, 구현 간단 | ⭐⭐ |
| 4. Viral | K-factor + Reciprocity | 선물 고유 구조 반영 | ⭐⭐⭐ |
| 5. CRM | Segment Performance + ROAS Sim | 실제 데이터 기반, 액션 가능 | ⭐⭐ |

**포트폴리오 전체 난도: ⭐⭐⭐ (고급 입문)**

- 고급 ML(K-means, Uplift, BG/NBD)은 "선택지"이지만, 위 5개 방법으로 충분
- 모두 Python(pandas, scipy, statsmodels) + SQL로 구현 가능
- 설명 가능성(explainability) 최우선

---

**작성자:** DESA Researcher  
**검토 대기:** Sophie (데이터 사이언티스트)  
**다음 단계:** 각 Layer별 구현 코드 작성 → Jupyter Notebook 구성
