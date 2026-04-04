---
title: "Layer 5 — CRM 캠페인 전략 & ROAS 시뮬레이션"
date: 2026-04-04
tags: [crm, campaign, roas, segment-performance, incrementality]
---

# CRM 캠페인 전략 & ROAS 시뮬레이션

## 핵심 질문
세그먼트별로 캠페인 반응이 얼마나 다른가?
어느 세그먼트를 타겟해야 ROAS가 최대인가?
피로도(block rate)가 높은 세그먼트는 어디인가?

## 선택 방법론
**Segment-Level Performance Analysis** + **Simple ROAS Simulation**

## 수학적 정의

### 캠페인 Funnel 메트릭
```
CTR (Click-Through Rate) = Clicks / Sends
CVR (Conversion Rate) = Purchases / Clicks
Block Rate = Blocks / Sends

예시:
Champions: 10,000 sends → 3,000 clicks → 300 purchases → 10 blocks
  CTR = 30%, CVR = 10%, Block rate = 0.1%

At-Risk: 5,000 sends → 250 clicks → 5 purchases → 500 blocks
  CTR = 5%, CVR = 2%, Block rate = 10%
```

### ROAS 계산
```
ROAS = Revenue / Campaign_Cost

Projected Revenue = Sends × CTR × CVR × AOV (Average Order Value)

예시 (Champions, 1회 캠페인, Budget $10,000):
- Sends: 10,000
- Revenue: 10,000 × 0.30 × 0.10 × $100 = $300,000
- ROAS = $300,000 / $10,000 = 30.0x

At-Risk (동일 budget):
- Revenue: 5,000 × 0.05 × 0.02 × $50 = $500
- ROAS = $500 / $10,000 = 0.05x (손실!!)
```

### Chi-Square Test (세그먼트별 차이 검증)
```
H0: CTR은 세그먼트 간 차이가 없다
H1: CTR이 세그먼트 간 차이가 있다

χ² = Σ((Observed - Expected)² / Expected)
df = (rows - 1) × (cols - 1)

if p-value < 0.05: H0 기각 → 세그먼트별 유의미한 차이
```

## 구현 코드

### SQL 버전: Segment Performance
```sql
-- Step 1: Campaign logs와 RFM 세그먼트 조인
WITH campaign_with_segment AS (
  SELECT
    cl.campaign_id,
    cl.user_id,
    cl.event_type,  -- 'send', 'open', 'click', 'block', 'purchase'
    cl.created_at,
    rs.rfm_segment
  FROM campaign_logs cl
  LEFT JOIN rfm_segments rs
    ON cl.user_id = rs.user_id
),

-- Step 2: 세그먼트별 Funnel 계산
segment_funnel AS (
  SELECT
    rfm_segment,
    COUNT(CASE WHEN event_type = 'send' THEN 1 END) AS sends,
    COUNT(CASE WHEN event_type = 'open' THEN 1 END) AS opens,
    COUNT(CASE WHEN event_type = 'click' THEN 1 END) AS clicks,
    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) AS purchases,
    COUNT(CASE WHEN event_type = 'block' THEN 1 END) AS blocks
  FROM campaign_with_segment
  GROUP BY rfm_segment
),

-- Step 3: 메트릭 계산
segment_metrics AS (
  SELECT
    rfm_segment,
    sends,
    ROUND(100.0 * opens / sends, 2) AS open_rate_pct,
    ROUND(100.0 * clicks / sends, 2) AS ctr_pct,
    CASE WHEN clicks > 0
      THEN ROUND(100.0 * purchases / clicks, 2)
      ELSE 0
    END AS cvr_pct,
    ROUND(100.0 * blocks / sends, 2) AS block_rate_pct
  FROM segment_funnel
  WHERE sends > 0
)

SELECT * FROM segment_metrics
ORDER BY ctr_pct DESC;
```

### Python 버전: 전체 분석
```python
import pandas as pd
import numpy as np
from scipy.stats import chi2_contingency
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Campaign logs + RFM 세그먼트 조인
campaign_segment = (
    campaign_logs
    .merge(rfm_segments[['user_id', 'segment']], on='user_id', how='left')
)

# 2. 세그먼트별 Funnel 계산
segment_funnel = (
    campaign_segment
    .groupby(['segment', 'event_type'])
    .size()
    .unstack(fill_value=0)
)

# 3. 메트릭 계산
segment_metrics = pd.DataFrame({
    'segment': segment_funnel.index,
    'sends': segment_funnel['send'],
    'opens': segment_funnel.get('open', 0),
    'clicks': segment_funnel.get('click', 0),
    'purchases': segment_funnel.get('purchase', 0),
    'blocks': segment_funnel.get('block', 0),
})

segment_metrics['open_rate'] = segment_metrics['opens'] / segment_metrics['sends']
segment_metrics['ctr'] = segment_metrics['clicks'] / segment_metrics['sends']
segment_metrics['cvr'] = segment_metrics['purchases'] / segment_metrics['clicks']
segment_metrics['block_rate'] = segment_metrics['blocks'] / segment_metrics['sends']

print(segment_metrics[['segment', 'ctr', 'cvr', 'block_rate']])

# 4. Chi-Square Test (CTR 차이)
contingency = pd.crosstab(
    campaign_segment['segment'],
    campaign_segment['event_type'] == 'click'
)
chi2, p_val, dof, expected = chi2_contingency(contingency)
print(f"\nChi-square test for CTR difference:")
print(f"χ² = {chi2:.2f}, p-value = {p_val:.4f}")
if p_val < 0.05:
    print("✓ Significant difference across segments")
```

### ROAS 시뮬레이션
```python
# 5. 입력 데이터 준비
campaign_budget = 10000  # 캠페인 총 예산

# 세그먼트별 사용자 크기
segment_size = rfm_segments['segment'].value_counts()

# 세그먼트별 평균 주문금액 (AOV)
aov_by_segment = (
    orders
    .merge(rfm_segments[['user_id', 'segment']], left_on='sender_user_id', right_on='user_id')
    .groupby('segment')['total_amount']
    .mean()
)

# 6. ROAS 시뮬레이션 함수
def simulate_roas(segment_name, budget, send_rate=0.8):
    """
    Parameters:
    - segment_name: 세그먼트명
    - budget: 캠페인 예산
    - send_rate: 전체 고객 대비 발송 비율 (default 80%)
    
    Returns:
    - dict with revenue, roas, etc.
    """
    
    num_users = segment_size[segment_name]
    sends = int(num_users * send_rate)
    
    ctr = segment_metrics[segment_metrics['segment'] == segment_name]['ctr'].values[0]
    cvr = segment_metrics[segment_metrics['segment'] == segment_name]['cvr'].values[0]
    aov = aov_by_segment[segment_name]
    
    clicks = int(sends * ctr)
    purchases = int(clicks * cvr)
    revenue = purchases * aov
    
    roas = revenue / budget if budget > 0 else 0
    
    return {
        'segment': segment_name,
        'users': num_users,
        'sends': sends,
        'clicks': clicks,
        'purchases': purchases,
        'revenue': revenue,
        'cost': budget,
        'roas': roas
    }

# 7. 모든 세그먼트 시뮬레이션
simulation_results = [
    simulate_roas(seg, campaign_budget)
    for seg in segment_metrics['segment'].unique()
]

df_sim = pd.DataFrame(simulation_results).sort_values('roas', ascending=False)
print("\n=== ROAS Simulation Results ===")
print(df_sim.to_string(index=False))

# 8. 최적 타겟팅 전략 수립
roas_threshold = 3.0
recommended_segments = df_sim[df_sim['roas'] >= roas_threshold]['segment'].tolist()

block_threshold = 0.15
high_fatigue_segments = segment_metrics[
    segment_metrics['block_rate'] > block_threshold
]['segment'].tolist()

print(f"\n=== Targeting Recommendations ===")
print(f"✓ Target segments (ROAS >= {roas_threshold}x): {recommended_segments}")
print(f"⚠ High-fatigue segments (block_rate > {block_threshold*100:.0f}%): {high_fatigue_segments}")
```

### 시각화
```python
# 9. Visualization

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Subplot 1: ROAS 막대 그래프
colors = ['green' if r >= 3 else 'red' for r in df_sim['roas']]
axes[0, 0].barh(df_sim['segment'], df_sim['roas'], color=colors)
axes[0, 0].axvline(x=3.0, color='black', linestyle='--', label='ROAS = 3.0x')
axes[0, 0].set_xlabel('ROAS')
axes[0, 0].set_title('Projected ROAS by Segment')
axes[0, 0].legend()

# Subplot 2: CTR vs CVR
axes[0, 1].scatter(
    segment_metrics['ctr'],
    segment_metrics['cvr'],
    s=segment_metrics['sends']/10,  # bubble size = sends
    alpha=0.6
)
for idx, row in segment_metrics.iterrows():
    axes[0, 1].annotate(row['segment'], (row['ctr'], row['cvr']))
axes[0, 1].set_xlabel('CTR')
axes[0, 1].set_ylabel('CVR')
axes[0, 1].set_title('CTR vs CVR by Segment')

# Subplot 3: Block Rate
block_data = segment_metrics.sort_values('block_rate', ascending=False)
colors_block = ['red' if b > 0.15 else 'orange' for b in block_data['block_rate']]
axes[1, 0].barh(block_data['segment'], block_data['block_rate'], color=colors_block)
axes[1, 0].axvline(x=0.15, color='black', linestyle='--', label='Alert threshold (15%)')
axes[1, 0].set_xlabel('Block Rate')
axes[1, 0].set_title('Fatigue Level by Segment')
axes[1, 0].legend()

# Subplot 4: Revenue Contribution
revenue_data = df_sim.sort_values('revenue', ascending=False)
axes[1, 1].barh(revenue_data['segment'], revenue_data['revenue'])
axes[1, 1].set_xlabel('Projected Revenue ($)')
axes[1, 1].set_title('Revenue Contribution by Segment')

plt.tight_layout()
plt.show()
```

## 검증

### 1. 세그먼트 간 성과 차이 유의성 (Chi-Square)
```python
from scipy.stats import chi2_contingency

# Click vs No-Click by Segment
contingency_table = pd.crosstab(
    campaign_segment['segment'],
    campaign_segment['event_type'] == 'click'
)

chi2, p_val, dof, expected = chi2_contingency(contingency_table)
print(f"Chi² = {chi2:.2f}, p-value = {p_val:.4f}, dof = {dof}")

if p_val < 0.05:
    print("✓ Significant difference in CTR across segments (p < 0.05)")
else:
    print("✗ No significant difference (p >= 0.05)")
```

### 2. 샘플 크기 충분성
```python
# 각 세그먼트의 기대 빈도 확인
print("Expected frequencies:")
print(expected)

# 모든 기대 빈도 >= 5 확인
if (expected >= 5).all():
    print("✓ All expected frequencies >= 5 (Chi-square valid)")
else:
    print("⚠ Some expected frequencies < 5 (consider Fisher's exact test)")
```

### 3. 시간 경과에 따른 Block Rate 변화
```python
# 캠페인 발송 후 시간에 따른 block rate 추이
campaign_segment['days_since_send'] = (
    pd.Timestamp.now() - campaign_segment['created_at']
).dt.days

fatigue_trend = (
    campaign_segment
    .groupby(['segment', 'days_since_send'])
    .apply(lambda g: (g['event_type'] == 'block').sum() / len(g))
    .reset_index()
    .rename(columns={0: 'block_rate'})
)

for segment in fatigue_trend['segment'].unique():
    seg_data = fatigue_trend[fatigue_trend['segment'] == segment]
    plt.plot(seg_data['days_since_send'], seg_data['block_rate'], label=segment)

plt.xlabel('Days Since Send')
plt.ylabel('Block Rate')
plt.title('Fatigue Trend Over Time')
plt.legend()
plt.show()
```

## 주의사항

1. **선택 편향(Selection Bias)**
   - 특정 세그먼트에만 캠페인을 보냈으면 공정한 비교 불가능
   - 무작위 추출 또는 매칭 필요

2. **혼동 변수(Confounding)**
   - Champions의 높은 CTR이 세그먼트 특성 때문인가, 캠페인 내용 때문인가?
   - 같은 캠페인을 모든 세그먼트에 발송해야 함

3. **시간 효과(Time Effect)**
   - 캠페인 시점에 따라 반응이 다를 수 있음
   - 요일, 계절, 이벤트 등 고려 필요

## 고급: Uplift Modeling (선택 사항)

K-Means나 고급 ML을 추가로 고려할 경우:
- **Causal Inference**: 인과 효과 추정 (correlation vs causation)
- **T-Learner**: Treatment와 Control 그룹 분리 학습
- **Uber causalml**: Python 라이브러리 활용
- 시간/리소스 충분할 때만 고려

## 참고 자료
- [Measured: Incrementality-based Attribution](https://www.measured.com/blog/why-incrementality-based-attribution-is-better-for-optimizing-roas-than-mmm-or-mta-a-real-world-example/)
- [Cometly: Incrementality Testing for Marketing](https://www.cometly.com/post/incrementality-testing-for-marketing)
- [Uber causalml: GitHub](https://github.com/uber/causalml)
