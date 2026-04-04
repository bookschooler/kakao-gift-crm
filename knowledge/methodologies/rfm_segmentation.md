---
title: "Layer 2 — RFM 세그멘테이션"
date: 2026-04-04
tags: [rfm, segmentation, customer-value, rule-based]
---

# RFM 세그멘테이션

## 핵심 질문
고객을 어떻게 가치별로 분류할 것인가?
RFM 점수로 11개 세그먼트를 명확히 정의할 수 있는가?

## 선택 방법론
**Rule-Based NTILE 5분위** (Hughes 1994)

## 수학적 정의

### RFM 원값 계산 (12개월 기준)
```
R (Recency) = Days since last purchase
F (Frequency) = Number of purchases in 12 months
M (Monetary) = Total spending in 12 months
```

### NTILE 스코어링
```
R_score = NTILE(5) OVER (ORDER BY Recency ASC)
  → 최근 구매일수록 높은 점수 (1~5)

F_score = NTILE(5) OVER (ORDER BY Frequency DESC)
  → 자주 구매할수록 높은 점수 (1~5)

M_score = NTILE(5) OVER (ORDER BY Monetary DESC)
  → 많이 지출할수록 높은 점수 (1~5)

RFM_Composite = (R_score × 100) + (F_score × 10) + M_score
  → 555 (최고) ~ 111 (최저)
```

## 세그먼트 정의

| RFM 조합 | 세그먼트명 | 정의 | 마케팅 액션 |
|---|---|---|---|
| 55x | Champions | 최근 + 자주 구매 | VIP 이벤트, 프리미엄 상품 추천 |
| 45x, 54x, 55 | Loyal | 꾸준한 충성도 | 정기 캠페인, 멤버십 |
| 35x, 45x | Potential | 성장 가능성 | 교육 캠페인, 인센티브 |
| 33x, 34x | Need Attention | 유지 필요 | 리엔게이지먼트 캠페인 |
| 24x, 25x | At Risk | 이탈 위험 | 복귀 프로모션, 긴급 연락 |
| 1x, 2x | Hibernating | 휴면 | 재활성화 시도, 낮은 빈도 |
| 11x, 21x | Lost | 거의 전향 없음 | 삭제 또는 저비용 유지 |

## 구현 코드 (PySpark/SQL)

### SQL 버전
```sql
-- step 1: RFM 원값 계산
WITH rfm_calc AS (
  SELECT
    sender_user_id AS user_id,
    DATE_DIFF(CURRENT_DATE(), MAX(DATE(created_at))) AS recency,
    COUNT(DISTINCT order_id) AS frequency,
    SUM(total_amount) AS monetary
  FROM orders
  WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    AND order_status = 'accepted'
  GROUP BY user_id
),

-- step 2: NTILE 스코어링
rfm_scored AS (
  SELECT
    user_id,
    recency, frequency, monetary,
    NTILE(5) OVER (ORDER BY recency ASC) AS r_score,
    NTILE(5) OVER (ORDER BY frequency DESC) AS f_score,
    NTILE(5) OVER (ORDER BY monetary DESC) AS m_score
  FROM rfm_calc
),

-- step 3: 세그먼트 매핑
rfm_segments AS (
  SELECT
    user_id,
    r_score, f_score, m_score,
    CASE
      WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
      WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
      WHEN r_score = 5 AND f_score >= 2 THEN 'New Customers'
      WHEN r_score >= 3 AND f_score = 3 THEN 'Need Attention'
      WHEN r_score <= 2 AND f_score >= 4 THEN 'At Risk'
      WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
      ELSE 'Hibernating'
    END AS segment
  FROM rfm_scored
)

SELECT * FROM rfm_segments;
```

### Python 버전
```python
import pandas as pd
import numpy as np

# 1. RFM 원값
rfm = (
    orders[orders['order_status'] == 'accepted']
    .groupby('sender_user_id')
    .agg({
        'created_at': lambda x: (pd.Timestamp.now() - x.max()).days,
        'order_id': 'count',
        'total_amount': 'sum'
    })
    .rename(columns={
        'created_at': 'recency',
        'order_id': 'frequency',
        'total_amount': 'monetary'
    })
)

# 2. NTILE 스코어
rfm['r_score'] = pd.qcut(rfm['recency'], q=5, labels=[5, 4, 3, 2, 1], duplicates='drop')
rfm['f_score'] = pd.qcut(rfm['frequency'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')
rfm['m_score'] = pd.qcut(rfm['monetary'], q=5, labels=[1, 2, 3, 4, 5], duplicates='drop')

# 3. 세그먼트 정의
def segment_mapping(row):
    r, f, m = row['r_score'], row['f_score'], row['m_score']
    if r >= 4 and f >= 4: return 'Champions'
    elif r >= 3 and f >= 3: return 'Loyal Customers'
    elif r == 5 and f >= 2: return 'New Customers'
    elif r >= 3 and f == 3: return 'Need Attention'
    elif r <= 2 and f >= 4: return 'At Risk'
    elif r <= 2 and f <= 2: return 'Lost'
    else: return 'Hibernating'

rfm['segment'] = rfm.apply(segment_mapping, axis=1)
```

## 검증

### 1. 세그먼트 크기 분포
```python
segment_dist = rfm.groupby('segment').size()
print(segment_dist)
# 각 세그먼트가 전체 고객의 5~15% 범위 내인지 확인
```

### 2. 세그먼트별 GMV 기여도
```python
segment_gmv = rfm.groupby('segment')['monetary'].agg(['sum', 'mean'])
segment_gmv['contribution'] = segment_gmv['sum'] / segment_gmv['sum'].sum()
print(segment_gmv.sort_values('contribution', ascending=False))
# Pareto: 상위 20%가 80% 이상 기여하는가?
```

### 3. 안정성 검증 (Stability Test)
```python
# 6개월 × 2 (분기별) RFM 재계산
rfm_q1 = calculate_rfm(orders[orders['created_at'] < '2024-07-01'])
rfm_q2 = calculate_rfm(orders[orders['created_at'] >= '2024-07-01'])

# 동일 사용자가 같은 세그먼트에 속하는 비율
stability = (rfm_q1['segment'] == rfm_q2['segment']).mean()
print(f"Stability: {stability:.1%}")
# >= 70% 이면 안정적
```

## 주의사항

1. **NTILE 적용 전 결측치 처리**
   - 구매 기록이 전혀 없는 신규 고객 제외

2. **분석 기간 고정**
   - 12개월 롤링 윈도우 권장
   - 분석 기간마다 점수 재계산

3. **이벤트 효과 고려**
   - 분석 직후 대형 이벤트(빼빼로데이)가 있으면 분석 전 실행

## 참고 자료
- Hughes, A. M. (1994). Strategic Database Marketing
- [Rittman Analytics: RFM with dbt](https://rittmananalytics.com/blog/2021/6/20/rfm-analysis-and-customer-segmentation-using-looker-dbt-and-google-bigquery)
