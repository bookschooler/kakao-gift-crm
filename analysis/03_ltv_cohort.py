"""
Layer 3: LTV 코호트 분석
=========================
목적: 2023.01~2024.12 (24개 코호트) 기준으로 유저의 최초 구매 월을 코호트로 설정,
      각 코호트의 1/3/6/12개월 누적 LTV와 Retention Rate를 계산하여
      코호트 품질(획득 월별 유저 장기 가치)을 비교한다.

핵심 인사이트:
  - 코호트별 Retention 히트맵
  - 누적 LTV 곡선 (평균)
  - 신규 유저 획득 품질이 좋은 코호트 vs 이탈이 빠른 코호트
"""

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

BASE = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift"
CHART_DIR = f"{BASE}/analysis/charts"

print("=" * 60)
print("[Layer 3] LTV 코호트 분석 시작")
print("=" * 60)

# ─────────────────────────────────────────
# 1. 데이터 로딩
# ─────────────────────────────────────────
orders = pd.read_csv(f"{BASE}/orders.csv", parse_dates=["created_at", "updated_at"])
orders_active = orders[orders["order_status"] != "cancelled"].copy()

orders_active["order_month"] = orders_active["created_at"].dt.to_period("M")

# ─────────────────────────────────────────
# 2. 코호트 정의: 유저의 첫 구매 월
# ─────────────────────────────────────────
cohort_df = (
    orders_active.groupby("sender_user_id")["order_month"]
    .min()
    .reset_index()
    .rename(columns={"order_month": "cohort_month"})
)

orders_with_cohort = orders_active.merge(cohort_df, on="sender_user_id", how="left")

# 코호트 경과 월 계산
orders_with_cohort["months_since_cohort"] = (
    orders_with_cohort["order_month"] - orders_with_cohort["cohort_month"]
).apply(lambda x: x.n)

print(f"전체 유저: {cohort_df['sender_user_id'].nunique():,}명")
print(f"코호트 범위: {cohort_df['cohort_month'].min()} ~ {cohort_df['cohort_month'].max()}")

# ─────────────────────────────────────────
# 3. Retention Rate 매트릭스
# ─────────────────────────────────────────
# 코호트별 × 경과 월별 활성 유저 수
retention_matrix = (
    orders_with_cohort
    .groupby(["cohort_month", "months_since_cohort"])["sender_user_id"]
    .nunique()
    .reset_index()
    .rename(columns={"sender_user_id": "active_users"})
)

# 코호트 초기 유저 수 (month 0)
cohort_size = (
    retention_matrix[retention_matrix["months_since_cohort"] == 0]
    .set_index("cohort_month")["active_users"]
    .rename("cohort_size")
)

# Retention Rate 계산
retention_matrix = retention_matrix.merge(cohort_size, on="cohort_month")
retention_matrix["retention_rate"] = (
    retention_matrix["active_users"] / retention_matrix["cohort_size"] * 100
)

# 피벗: 코호트 × 경과 월
retention_pivot = retention_matrix.pivot_table(
    index="cohort_month",
    columns="months_since_cohort",
    values="retention_rate"
)
# 최대 12개월까지
retention_pivot = retention_pivot.iloc[:, :13]

print(f"\n--- Retention Rate 매트릭스 (코호트 × 경과월) ---")
print(retention_pivot.round(1).to_string())

# ─────────────────────────────────────────
# 4. 누적 LTV 계산
# ─────────────────────────────────────────
# 코호트별 × 경과 월별 누적 GMV per 초기 유저
ltv_matrix_raw = (
    orders_with_cohort
    .groupby(["cohort_month", "months_since_cohort"])["total_amount_krw"]
    .sum()
    .reset_index()
    .rename(columns={"total_amount_krw": "gmv"})
)

ltv_matrix_raw = ltv_matrix_raw.merge(cohort_size, on="cohort_month")

# 누적 GMV (정렬 후 cumsum)
ltv_matrix_raw = ltv_matrix_raw.sort_values(["cohort_month", "months_since_cohort"])
ltv_matrix_raw["cumulative_gmv"] = ltv_matrix_raw.groupby("cohort_month")["gmv"].cumsum()
ltv_matrix_raw["ltv_per_user"] = ltv_matrix_raw["cumulative_gmv"] / ltv_matrix_raw["cohort_size"]

# LTV 피벗
ltv_pivot = ltv_matrix_raw.pivot_table(
    index="cohort_month",
    columns="months_since_cohort",
    values="ltv_per_user"
)
ltv_pivot = ltv_pivot.iloc[:, :13]

# 주요 LTV 시점 (1/3/6/12개월)
ltv_checkpoints = {}
for m in [0, 1, 2, 5, 11]:  # 인덱스 기준 (0=첫달, 1=1개월 경과 등)
    col = m
    if col in ltv_pivot.columns:
        ltv_checkpoints[f"M+{m}"] = ltv_pivot[col].mean()

print("\n--- 평균 누적 LTV (전체 코호트 평균) ---")
for k, v in ltv_checkpoints.items():
    print(f"  {k}: {v:,.0f}원")

# ─────────────────────────────────────────
# 5. 코호트별 핵심 수치 (LTV 시점별)
# ─────────────────────────────────────────
print("\n--- 코호트별 초기 유저 수 & M+0 LTV ---")
cohort_summary = cohort_size.reset_index()
cohort_summary = cohort_summary.merge(
    ltv_pivot[[0]].rename(columns={0: "ltv_m0"}).reset_index(),
    on="cohort_month"
)
print(cohort_summary.to_string(index=False))

# ─────────────────────────────────────────
# 6. 차트 저장
# ─────────────────────────────────────────

# Chart 1: Retention 히트맵
fig, ax = plt.subplots(figsize=(16, 10))
mask = retention_pivot.isnull()
sns.heatmap(
    retention_pivot.round(1),
    annot=True, fmt=".0f",
    cmap="Blues",
    mask=mask,
    ax=ax,
    linewidths=0.3,
    cbar_kws={"label": "Retention Rate (%)"},
    annot_kws={"size": 7}
)
ax.set_title("코호트 Retention Rate 히트맵 (%)\n(행=첫 구매 월 코호트, 열=경과 월수)", fontsize=13, fontweight='bold')
ax.set_xlabel("경과 월수 (Months Since First Purchase)", fontsize=10)
ax.set_ylabel("코호트 (첫 구매 월)", fontsize=10)
ax.set_xticklabels([f"M+{c}" for c in retention_pivot.columns], fontsize=8)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer3_retention_heatmap.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n차트 저장: layer3_retention_heatmap.png")

# Chart 2: 평균 누적 LTV 곡선
avg_ltv_curve = ltv_pivot.mean(axis=0).dropna()

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(avg_ltv_curve.index, avg_ltv_curve.values / 1000, 'o-',
        color='#FF4757', linewidth=2.5, markersize=7)
ax.fill_between(avg_ltv_curve.index, avg_ltv_curve.values / 1000, alpha=0.15, color='#FF4757')
ax.set_xlabel("경과 월수", fontsize=11)
ax.set_ylabel("누적 LTV (천원)", fontsize=11)
ax.set_title("평균 누적 LTV 곡선 (전체 코호트 평균)", fontsize=13, fontweight='bold')
ax.set_xticks(avg_ltv_curve.index)
ax.set_xticklabels([f"M+{m}" for m in avg_ltv_curve.index])
ax.grid(alpha=0.3)

# 1/3/6/12개월 마킹
for m_idx in [0, 2, 5, 11]:
    if m_idx in avg_ltv_curve.index:
        val = avg_ltv_curve[m_idx] / 1000
        ax.annotate(f"M+{m_idx}\n{val:,.0f}K",
                    xy=(m_idx, val),
                    xytext=(m_idx + 0.3, val + 5),
                    fontsize=8, color='#CC0000',
                    arrowprops=dict(arrowstyle='->', color='#CC0000', lw=1))

plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer3_ltv_curve.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer3_ltv_curve.png")

# Chart 3: 코호트별 M+0 vs M+5 LTV 비교 (초기 유저 1인당)
fig, ax = plt.subplots(figsize=(14, 6))
cohorts = ltv_pivot.index.astype(str)
ltv_m0 = ltv_pivot[0] if 0 in ltv_pivot.columns else pd.Series(np.nan, index=ltv_pivot.index)
ltv_m5 = ltv_pivot[5] if 5 in ltv_pivot.columns else pd.Series(np.nan, index=ltv_pivot.index)

x = np.arange(len(cohorts))
w = 0.35
ax.bar(x - w/2, ltv_m0.values / 1000, width=w, label='M+0 (첫 달)', color='#FEE500', edgecolor='#333')
ax.bar(x + w/2, ltv_m5.values / 1000, width=w, label='M+5 (6개월 누적)', color='#FF6B00', edgecolor='#333', alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(cohorts, rotation=45, ha='right', fontsize=8)
ax.set_ylabel("LTV per User (천원)", fontsize=10)
ax.set_title("코호트별 LTV 비교 (M+0 vs M+5 누적)", fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer3_cohort_ltv_comparison.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer3_cohort_ltv_comparison.png")

print("\n[Layer 3 완료]")
print(f"  총 코호트 수: {len(cohort_size)}개")
print(f"  평균 1개월 Retention: {retention_pivot[1].mean():.1f}%")
print(f"  평균 M+0 LTV: {avg_ltv_curve[0]:,.0f}원")
if 5 in avg_ltv_curve.index:
    print(f"  평균 M+5 누적 LTV: {avg_ltv_curve[5]:,.0f}원")
