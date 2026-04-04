---
title: "Layer 3 — LTV 분석 & 코호트"
date: 2026-04-04
tags: [ltv, cohort, retention, customer-lifetime-value]
---

# LTV 분석 & 코호트

## 핵심 질문
월별로 첫 구매한 고객 집단(cohort)이 시간 경과에 따라 어떻게 변하는가?
세그먼트별 LTV는 얼마나 차이가 나는가?

## 선택 방법론
**Monthly Cohort Retention × Cumulative LTV**

## 수학적 정의

### Cohort 정의
```
Cohort = 첫 구매 월(month)별 고객 그룹

예: 2024-01 Cohort = 2024년 1월에 첫 구매한 모든 고객
```

### Retention Rate
```
Retention(t) = Active_users(t) / Initial_users(t=0)

예: 2024-01 Cohort 3개월차
- 초기(Jan): 1,000명
- 3개월차(April): 640명
- Retention = 640/1000 = 64%
```

### Cumulative LTV
```
LTV_cohort(T) = Σ(t=0 to T) Revenue(t) / Initial_Size

예: 2024-01 Cohort의 3개월 누적 LTV
- Month 0: $50,000 revenue
- Month 1: $36,000 revenue
- Month 2: $27,520 revenue
- Total: $113,520 / 1,000 users = $113.52 per user
```

## 구현 코드

### SQL 버전
```sql
-- Step 1: 사용자별 첫 구매 월 (Cohort 정의)
WITH user_cohort AS (
  SELECT
    sender_user_id,
    DATE_TRUNC('month', MIN(created_at)) AS cohort_month
  FROM orders
  WHERE order_status = 'accepted'
  GROUP BY sender_user_id
),

-- Step 2: 코호트-월별 활성 사용자 수 & 수익
cohort_revenue AS (
  SELECT
    uc.cohort_month,
    DATE_TRUNC('month', o.created_at) AS purchase_month,
    COUNT(DISTINCT o.sender_user_id) AS active_users,
    SUM(o.total_amount) AS revenue
  FROM user_cohort uc
  JOIN orders o
    ON uc.sender_user_id = o.sender_user_id
    AND o.created_at >= uc.cohort_month
    AND o.order_status = 'accepted'
  GROUP BY uc.cohort_month, purchase_month
),

-- Step 3: 경과 개월 계산 & 초기 코호트 크기
cohort_with_month_offset AS (
  SELECT
    cohort_month,
    DATEDIFF(MONTH, cohort_month, purchase_month) AS month_offset,
    active_users,
    revenue
  FROM cohort_revenue
),

-- Step 4: 코호트 초기 크기
cohort_size AS (
  SELECT
    cohort_month,
    SUM(active_users) FILTER (WHERE month_offset = 0) AS initial_size
  FROM cohort_with_month_offset
  GROUP BY cohort_month
),

-- Step 5: Retention & Cumulative LTV
final_cohort AS (
  SELECT
    cwmo.cohort_month,
    cwmo.month_offset,
    cs.initial_size,
    cwmo.active_users,
    ROUND(100.0 * cwmo.active_users / cs.initial_size, 1) AS retention_pct,
    cwmo.revenue,
    SUM(cwmo.revenue) OVER (
      PARTITION BY cwmo.cohort_month
      ORDER BY cwmo.month_offset
    ) AS cumulative_revenue
  FROM cohort_with_month_offset cwmo
  JOIN cohort_size cs
    ON cwmo.cohort_month = cs.cohort_month
)

SELECT
  cohort_month,
  month_offset,
  initial_size,
  active_users,
  retention_pct,
  revenue,
  cumulative_revenue,
  ROUND(cumulative_revenue / initial_size, 2) AS cumulative_ltv
FROM final_cohort
ORDER BY cohort_month, month_offset;
```

### Python 버전
```python
import pandas as pd
import numpy as np

# 1. 코호트 정의
df = orders[orders['order_status'] == 'accepted'].copy()
df['cohort_month'] = df.groupby('sender_user_id')['created_at'].transform('min').dt.to_period('M')
df['month_offset'] = (df['created_at'].dt.to_period('M') - df['cohort_month']).apply(lambda x: x.n)

# 2. 코호트별 크기
cohort_size = df.groupby('cohort_month')['sender_user_id'].nunique()

# 3. 코호트-월별 활성 사용자
cohort_users = df.groupby(['cohort_month', 'month_offset'])['sender_user_id'].nunique().unstack(fill_value=0)

# 4. Retention 계산
cohort_retention = cohort_users.divide(cohort_users.iloc[:, 0], axis=0)  # 초기 대비 비율

# 5. 코호트-월별 수익
cohort_revenue = df.groupby(['cohort_month', 'month_offset'])['total_amount'].sum().unstack(fill_value=0)

# 6. 누적 수익
cohort_cumulative = cohort_revenue.cumsum(axis=1)

# 7. 누적 LTV
cohort_ltv = cohort_cumulative.divide(cohort_size, axis=0)

# 시각화
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Retention Heatmap
sns.heatmap(cohort_retention, annot=True, fmt='.0%', cmap='RdYlGn', ax=axes[0, 0])
axes[0, 0].set_title('Cohort Retention Rate')

# LTV Heatmap
sns.heatmap(cohort_ltv, annot=True, fmt='$.0f', cmap='Greens', ax=axes[0, 1])
axes[0, 1].set_title('Cohort Cumulative LTV')

# Average Retention Curve
avg_retention = cohort_retention.mean()
avg_retention.plot(ax=axes[1, 0], marker='o')
axes[1, 0].set_title('Average Retention by Month')
axes[1, 0].set_ylabel('Retention %')

# Average LTV Curve
avg_ltv = cohort_ltv.mean()
avg_ltv.plot(ax=axes[1, 1], marker='o', color='green')
axes[1, 1].set_title('Average Cumulative LTV by Month')
axes[1, 1].set_ylabel('LTV ($)')

plt.tight_layout()
plt.show()
```

## 검증

### 1. Cohort 안정성 (ANOVA)
```python
from scipy.stats import f_oneway

# 각 cohort의 month_offset=12 시점 LTV
cohort_12m_ltv = cohort_ltv.iloc[:, 12]  # 12개월차 LTV

# 코호트 간 차이 유의성
f_stat, p_val = f_oneway(*[cohort_12m_ltv[cohort] for cohort in cohort_12m_ltv.index])
print(f"F-statistic: {f_stat:.2f}, p-value: {p_val:.4f}")
# p < 0.05 이면 cohort별 차이 유의미
```

### 2. Retention 곡선 형태
```python
# 건강한 retention curve는 지수적 감소
# 예: 100% → 80% → 65% → 55% → 50% → ...

# 이상 징후:
# 1. 급격한 낙보 (month 1-2): 품질 문제
# 2. 오르막: 데이터 오류
```

### 3. LTV 포화점
```python
# Cohort LTV가 month 6 이후 거의 증가하지 않으면,
# retention 추적을 6개월로 줄일 수 있음

# Diminishing return 지점 계산
diff = cohort_ltv.diff(axis=1)
plateau = (diff < 1).sum(axis=0)  # LTV 증가 < $1인 개월 수
```

## 주의사항

1. **생존자 편향(Survivor Bias)**
   - 이탈한 고객도 마지막 구매액은 카운트됨
   - 이탈 후 미구매 월도 활성 사용자에 포함 안 됨

2. **최근 코호트 데이터 불완전성**
   - 2024-11 cohort는 12개월 추적 불가능
   - 최소 12개월 기간이 지나야 LTV 비교 가능

3. **계절 효과(Time Effect) vs 코호트 효과(Cohort Effect)**
   - 11월 cohort는 처음부터 높은 LTV (시즌성)
   - 비교 시 주의 필요

## 참고 자료
- [Baremetrics: Cohort Analysis](https://baremetrics.com/blog/cohort-analysis)
- [Peel Insights: Cohort Analysis 101](https://www.peelinsights.com/post/cohort-analysis-101-an-introduction)
