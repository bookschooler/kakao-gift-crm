---
title: "Layer 4 — Viral Loop 분석"
date: 2026-04-04
tags: [viral, k-factor, network-effect, referral, reciprocity]
---

# Viral Loop 분석

## 핵심 질문
선물 받은 고객이 발신자가 될 확률은?
선물하기의 바이럴 계수(K-factor)는 얼마나 되는가?
세대별(generation) 바이럴 효과는 어디까지 미치는가?

## 선택 방법론
**K-factor (Viral Coefficient)** + **Reciprocity Index** + **Referral Generation Tracking**

## 수학적 정의

### Viral Coefficient (K-factor)
```
K = i × c

where:
i = average invites per user (평균 초대 횟수)
c = conversion rate of invitees (초대 수락 전환율)

해석:
K > 1.0: 자가 증식 (지수적 성장) — 마케팅 최소
K = 0.5: 하이브리드 (유료 마케팅 병행)
K < 0.3: 미미한 바이럴
```

### Reciprocity Index (N일 기준)
```
Reciprocity_N = 
  COUNT(receiver_id → sender_id within N days) /
  COUNT(all unique receiver_ids)

해석:
높을수록: 선물 받은 경험이 우수, 재구매 동기 강함
낮을수록: 선물 경험이 미흡, 추가 마케팅 필요
```

### Referral Generation
```
Generation 0: 오가닉 고객 (캠페인 미포함)
Generation 1: Gen 0이 초대한 고객 중 구매자
Generation 2: Gen 1이 초대한 고객 중 구매자
...

Viral Decay = Gen(n) / Gen(n-1)
예: Gen 0 = 10,000 → Gen 1 = 5,000 (50% decay)
    Gen 1 = 5,000 → Gen 2 = 2,000 (60% decay)
```

## 구현 코드

### SQL 버전
```sql
-- Step 1: 수신자 추적
WITH receiver_data AS (
  SELECT
    gift_receipt.order_id,
    orders.sender_user_id,
    orders.created_at AS sent_at,
    gift_receipt.receiver_user_id,
    gift_receipt.received_at
  FROM orders
  JOIN gift_receipts
    ON orders.order_id = gift_receipts.order_id
  WHERE gift_receipt.receiver_user_id IS NOT NULL
),

-- Step 2: 수신자의 첫 구매 (발신자로 전환)
receiver_first_purchase AS (
  SELECT
    receiver_user_id,
    MIN(created_at) AS first_purchase_date
  FROM orders
  WHERE order_status = 'accepted'
  GROUP BY receiver_user_id
),

-- Step 3: 수신자 → 발신자 전환 연결
viral_conversion AS (
  SELECT
    rd.sender_user_id,
    rd.receiver_user_id,
    rd.sent_at,
    rd.received_at,
    rfp.first_purchase_date,
    CASE
      WHEN rfp.first_purchase_date IS NOT NULL
        AND rfp.first_purchase_date > rd.received_at
      THEN 1 ELSE 0
    END AS converted,
    DATEDIFF(DAY, rd.received_at, rfp.first_purchase_date) AS days_to_convert
  FROM receiver_data rd
  LEFT JOIN receiver_first_purchase rfp
    ON rd.receiver_user_id = rfp.receiver_user_id
),

-- Step 4: K-factor 계산
k_factor_calc AS (
  SELECT
    COUNT(DISTINCT sender_user_id) AS total_senders,
    COUNT(DISTINCT receiver_user_id) AS total_receivers,
    SUM(converted) AS conversions,
    COUNT(*) AS total_invites,
    ROUND(100.0 * SUM(converted) / COUNT(*), 2) AS conversion_rate_pct,
    ROUND(COUNT(*) / COUNT(DISTINCT sender_user_id), 2) AS avg_invites_per_sender
  FROM viral_conversion
),

-- Step 5: Reciprocity Index (30일 기준)
reciprocity_30 AS (
  SELECT
    ROUND(100.0 * SUM(
      CASE WHEN converted = 1 AND days_to_convert <= 30 THEN 1 ELSE 0 END
    ) / COUNT(*), 2) AS reciprocity_rate_30d
  FROM viral_conversion
)

SELECT
  *,
  ROUND(
    (SELECT avg_invites_per_sender FROM k_factor_calc) *
    (SELECT conversion_rate_pct FROM k_factor_calc) / 100,
    2
  ) AS k_factor
FROM k_factor_calc, reciprocity_30;
```

### Python 버전
```python
import pandas as pd
import networkx as nx

# 1. 수신자 추적
receivers = gift_receipts[gift_receipts['receiver_user_id'].notna()].copy()
receivers = receivers.join(orders[['order_id', 'sender_user_id', 'created_at']], on='order_id')
receivers.rename(columns={'created_at': 'sent_at'}, inplace=True)

# 2. 수신자의 첫 구매
first_purchase = (
    orders[orders['order_status'] == 'accepted']
    .groupby('sender_user_id')['created_at']
    .min()
    .rename('first_purchase_date')
)

# 3. 전환 연결
viral_df = (
    receivers
    .merge(
        first_purchase.reset_index(),
        left_on='receiver_user_id',
        right_on='sender_user_id',
        how='left',
        indicator=True
    )
)

viral_df['converted'] = (
    (viral_df['_merge'] == 'both') &
    (viral_df['first_purchase_date'] > viral_df['received_at'])
).astype(int)

viral_df['days_to_convert'] = (
    viral_df['first_purchase_date'] - viral_df['received_at']
).dt.days

# 4. K-factor 계산
total_senders = viral_df['sender_user_id'].nunique()
total_conversions = viral_df['converted'].sum()
total_invites = len(viral_df)

conversion_rate = total_conversions / total_invites
avg_invites = total_invites / total_senders
k_factor = avg_invites * conversion_rate

print(f"K-factor: {k_factor:.2f}")
print(f"  - Avg invites per sender: {avg_invites:.2f}")
print(f"  - Conversion rate: {conversion_rate:.1%}")

# 5. Reciprocity Index
reciprocity_30 = (
    (viral_df['converted'] == 1) &
    (viral_df['days_to_convert'] <= 30)
).sum() / len(viral_df)

print(f"Reciprocity Index (30d): {reciprocity_30:.1%}")

# 6. 월별 K-factor 추이
monthly_k = (
    viral_df
    .assign(month=viral_df['sent_at'].dt.to_period('M'))
    .groupby('month')
    .apply(lambda g: (
        (g['sender_user_id'].nunique()) *
        (g['converted'].sum() / len(g))
    ) / g['sender_user_id'].nunique() * len(g) / g['sender_user_id'].nunique())
)
```

### Referral Generation 추적
```python
# DAG 구성: networkx 활용
import networkx as nx

G = nx.DiGraph()

# 0세대: 초대 받지 않은 오가닉 고객
gen_0_ids = set(orders['sender_user_id']) - set(viral_df['receiver_user_id'].unique())
G.add_nodes_from([(uid, {'generation': 0}) for uid in gen_0_ids])

# 1세대: Gen 0이 초대한 사람 중 구매자
gen_1_senders = viral_df[viral_df['sender_user_id'].isin(gen_0_ids)]['receiver_user_id'].unique()
gen_1_ids = set(gen_1_senders) & set(orders['sender_user_id'])  # 실제 구매자만
G.add_nodes_from([(uid, {'generation': 1}) for uid in gen_1_ids])

# 간선 추가
for _, row in viral_df[viral_df['converted'] == 1].iterrows():
    if row['sender_user_id'] in gen_0_ids or row['sender_user_id'] in gen_1_ids:
        G.add_edge(row['sender_user_id'], row['receiver_user_id'])

# 세대별 사용자 수
gen_counts = {}
for gen in range(5):
    gen_nodes = [n for n, d in G.nodes(data=True) if d.get('generation') == gen]
    gen_counts[gen] = len(gen_nodes)
    print(f"Generation {gen}: {len(gen_nodes)} users")

# Viral decay curve
import matplotlib.pyplot as plt
generations = sorted(gen_counts.keys())
counts = [gen_counts[g] for g in generations]

plt.plot(generations, counts, marker='o', label='User Count')
plt.xlabel('Generation')
plt.ylabel('Users')
plt.title('Viral Decay Curve')
plt.show()
```

## 검증

### 1. K-factor 신뢰도 (Bootstrap CI)
```python
from scipy.stats import bootstrap

def k_factor_bootstrap(sample):
    """단일 bootstrap sample의 K-factor"""
    conv_rate = sample['converted'].mean()
    avg_invites = len(sample) / sample['sender_user_id'].nunique()
    return avg_invites * conv_rate

# 1000회 bootstrap
k_samples = [
    k_factor_bootstrap(viral_df.sample(n=len(viral_df), replace=True))
    for _ in range(1000)
]

ci_lower = np.percentile(k_samples, 2.5)
ci_upper = np.percentile(k_samples, 97.5)
print(f"K-factor 95% CI: [{ci_lower:.2f}, {ci_upper:.2f}]")
```

### 2. 세대별 감쇠율 검증
```python
# Exponential fit: Gen(n) = Gen(0) × λ^n
# λ < 1 이면 정상 (지수적 감소)

from scipy.optimize import curve_fit

def exponential(x, a, lam):
    return a * (lam ** x)

generations = np.array(list(gen_counts.keys()))
counts = np.array([gen_counts[g] for g in generations])

popt, _ = curve_fit(exponential, generations[counts > 0], counts[counts > 0])
lambda_decay = popt[1]

print(f"Decay factor λ: {lambda_decay:.3f}")
if 0 < lambda_decay < 1:
    print("✓ Normal exponential decay")
else:
    print("⚠ Unusual pattern — check data")
```

### 3. 수신자 → 발신자 경로 추적
```python
# 수신자가 발신자가 되는 평균 시간
days_to_conversion = viral_df[viral_df['converted'] == 1]['days_to_convert'].dropna()
print(f"Average days to convert: {days_to_conversion.mean():.0f} days")
print(f"Median: {days_to_conversion.median():.0f} days")
print(f"25th-75th percentile: {days_to_conversion.quantile(0.25):.0f}-{days_to_conversion.quantile(0.75):.0f} days")
```

## 주의사항

1. **정보 폐쇄(Information Closure)**
   - 모든 receiver_user_id가 기록되어 있어야 함
   - 미카톡 로그인 정보 필수

2. **선택 편향(Selection Bias)**
   - receiver를 특정 고객에게만 보냈으면 바이럴 과다추정
   - 무작위 표본 추출 확인 필요

3. **경쟁 효과(Saturation)**
   - K > 1.0이어도 시장 포화로 성장 멈출 수 있음
   - 장기 성장률 모니터링 필수

## 참고 자료
- [FirstRound: K-factor: The Metric Behind Virality](https://review.firstround.com/glossary/k-factor-virality/)
- [Dropbox Case Study](https://viral-loops.com/blog/dropbox-grew-3900-simple-referral-program/)
- [Nature: Transition of social organisations driven by gift relationships](https://www.nature.com/articles/s41599-023-01688-w)
