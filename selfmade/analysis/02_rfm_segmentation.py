"""
Layer 2: RFM 세그멘테이션
==========================
목적: 2024년 기준 12개월 (2024-01-01 ~ 2024-12-31) 유저별 RFM 계산 후
      11개 Named Segment로 분류하여 세그먼트별 GMV 기여도와 행동 특성을 파악한다.

핵심 인사이트:
  - 세그먼트별 유저 수 및 GMV 비중
  - Champions/Loyal 세그먼트의 집중 관리 우선순위
  - At Risk / Hibernating 세그먼트 재활성화 기회
"""

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

BASE = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift"
CHART_DIR = f"{BASE}/analysis/charts"

print("=" * 60)
print("[Layer 2] RFM 세그멘테이션 시작")
print("=" * 60)

# ─────────────────────────────────────────
# 1. 데이터 로딩 및 필터링
# ─────────────────────────────────────────
orders = pd.read_csv(f"{BASE}/orders.csv", parse_dates=["created_at", "updated_at"])

# 분석 기간: 2024년 전체
ANALYSIS_START = pd.Timestamp("2024-01-01")
ANALYSIS_END   = pd.Timestamp("2024-12-31")
REF_DATE       = pd.Timestamp("2024-12-31")  # RFM 기준일

orders_2024 = orders[
    (orders["created_at"] >= ANALYSIS_START) &
    (orders["created_at"] <= ANALYSIS_END) &
    (orders["order_status"] != "cancelled")
].copy()

print(f"2024년 유효 주문: {len(orders_2024):,}건")
print(f"2024년 주문자 수: {orders_2024['sender_user_id'].nunique():,}명")

# ─────────────────────────────────────────
# 2. RFM 계산
# ─────────────────────────────────────────
rfm = orders_2024.groupby("sender_user_id").agg(
    last_order_date=("created_at", "max"),
    frequency=("order_id", "count"),
    monetary=("total_amount_krw", "sum")
).reset_index()

# R: 기준일 - 마지막 구매일 (일수, 작을수록 최근)
rfm["recency"] = (REF_DATE - rfm["last_order_date"]).dt.days

print(f"\n--- RFM 기초 통계 ---")
print(rfm[["recency", "frequency", "monetary"]].describe().round(2))

# ─────────────────────────────────────────
# 3. NTILE(5) 스코어링
# ─────────────────────────────────────────
# R은 작을수록 좋으므로 역방향 (1=가장 오래됨 → 5=가장 최근)
# F, M은 클수록 좋음 (5=가장 높음)

def safe_qcut(series, q, labels, ascending=True):
    """duplicates='drop' 처리하는 안전한 qcut"""
    try:
        result = pd.qcut(series, q=q, labels=labels if ascending else labels[::-1],
                         duplicates='drop')
        # 레이블이 역방향인 경우 처리
        return result
    except Exception as e:
        print(f"  qcut 경고: {e}")
        return pd.cut(series, bins=q, labels=labels if ascending else labels[::-1],
                      duplicates='drop')

# R 스코어: recency가 작을수록(최근일수록) 높은 점수
rfm["R_score"] = pd.qcut(rfm["recency"], q=5,
                          labels=[5, 4, 3, 2, 1],  # 낮은 recency → 5점
                          duplicates='drop').astype(int)

# F 스코어: frequency가 클수록 높은 점수
rfm["F_score"] = pd.qcut(rfm["frequency"].rank(method='first'), q=5,
                          labels=[1, 2, 3, 4, 5],
                          duplicates='drop').astype(int)

# M 스코어: monetary가 클수록 높은 점수
rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method='first'), q=5,
                          labels=[1, 2, 3, 4, 5],
                          duplicates='drop').astype(int)

rfm["RFM_score"] = rfm["R_score"].astype(str) + rfm["F_score"].astype(str) + rfm["M_score"].astype(str)
rfm["RFM_avg"] = (rfm["R_score"] + rfm["F_score"] + rfm["M_score"]) / 3

print("\n--- RFM 스코어 분포 ---")
print(f"R 스코어 분포:\n{rfm['R_score'].value_counts().sort_index()}")
print(f"\nF 스코어 분포:\n{rfm['F_score'].value_counts().sort_index()}")
print(f"\nM 스코어 분포:\n{rfm['M_score'].value_counts().sort_index()}")

# ─────────────────────────────────────────
# 4. 11개 Named Segment 분류
# ─────────────────────────────────────────
def assign_segment(row):
    r, f, m = row["R_score"], row["F_score"], row["M_score"]

    if r >= 5 and f >= 5 and m >= 5:
        return "Champions"
    elif r >= 4 and f >= 4:
        return "Loyal"
    elif r >= 4 and f <= 2:
        return "Potential Loyalist"
    elif r >= 5 and f <= 1:
        return "New Customers"
    elif r >= 4 and f <= 3:
        return "Promising"
    elif r == 3 and f >= 3:
        return "Need Attention"
    elif r == 3 and f <= 2:
        return "About to Sleep"
    elif r <= 2 and f >= 4:
        return "At Risk"
    elif r <= 1 and f >= 4 and m >= 4:
        return "Can't Lose Them"
    elif r <= 2 and f <= 2:
        return "Hibernating"
    else:
        return "Lost"

rfm["segment"] = rfm.apply(assign_segment, axis=1)

# ─────────────────────────────────────────
# 5. 세그먼트별 요약
# ─────────────────────────────────────────
seg_summary = rfm.groupby("segment").agg(
    user_count=("sender_user_id", "count"),
    avg_recency=("recency", "mean"),
    avg_frequency=("frequency", "mean"),
    avg_monetary=("monetary", "mean"),
    total_gmv=("monetary", "sum")
).reset_index()

total_users = seg_summary["user_count"].sum()
total_gmv   = seg_summary["total_gmv"].sum()

seg_summary["user_pct"]   = seg_summary["user_count"] / total_users * 100
seg_summary["gmv_pct"]    = seg_summary["total_gmv"] / total_gmv * 100
seg_summary["gmv_bn"]     = seg_summary["total_gmv"] / 1e8
seg_summary = seg_summary.sort_values("total_gmv", ascending=False)

print("\n--- 세그먼트별 요약 ---")
print(seg_summary[[
    "segment", "user_count", "user_pct",
    "gmv_bn", "gmv_pct",
    "avg_recency", "avg_frequency", "avg_monetary"
]].to_string(index=False))

# ─────────────────────────────────────────
# 6. 차트 저장
# ─────────────────────────────────────────

# Chart 1: 세그먼트별 유저 수 & GMV 비중 (버블 차트 스타일 바)
seg_colors = {
    "Champions":         "#FF4757",
    "Loyal":             "#FF6B81",
    "Potential Loyalist":"#FFA502",
    "New Customers":     "#2ED573",
    "Promising":         "#7BED9F",
    "Need Attention":    "#1E90FF",
    "About to Sleep":    "#70A1FF",
    "At Risk":           "#747D8C",
    "Can't Lose Them":   "#5352ED",
    "Hibernating":       "#A4B0BE",
    "Lost":              "#DFE4EA",
}

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# 유저 수 기준 수평 바
segs = seg_summary.sort_values("user_count", ascending=True)
colors_bar = [seg_colors.get(s, "#ccc") for s in segs["segment"]]
axes[0].barh(segs["segment"], segs["user_count"], color=colors_bar, edgecolor='white')
for i, (cnt, pct) in enumerate(zip(segs["user_count"], segs["user_pct"])):
    axes[0].text(cnt + 50, i, f"{cnt:,}명 ({pct:.1f}%)", va='center', fontsize=8)
axes[0].set_title("세그먼트별 유저 수", fontsize=12, fontweight='bold')
axes[0].set_xlabel("유저 수")
axes[0].grid(axis='x', alpha=0.3)
axes[0].set_xlim(0, segs["user_count"].max() * 1.35)

# GMV 기준 수평 바
segs2 = seg_summary.sort_values("gmv_bn", ascending=True)
colors_bar2 = [seg_colors.get(s, "#ccc") for s in segs2["segment"]]
axes[1].barh(segs2["segment"], segs2["gmv_bn"], color=colors_bar2, edgecolor='white')
for i, (gmv, pct) in enumerate(zip(segs2["gmv_bn"], segs2["gmv_pct"])):
    axes[1].text(gmv + 0.05, i, f"{gmv:.1f}억 ({pct:.1f}%)", va='center', fontsize=8)
axes[1].set_title("세그먼트별 GMV", fontsize=12, fontweight='bold')
axes[1].set_xlabel("GMV (억원)")
axes[1].grid(axis='x', alpha=0.3)
axes[1].set_xlim(0, segs2["gmv_bn"].max() * 1.4)

plt.suptitle("RFM 세그멘테이션 — 유저/GMV 분포", fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer2_segment_overview.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n차트 저장: layer2_segment_overview.png")

# Chart 2: RFM 스코어 분포 히트맵 (R vs F, M 크기)
fig, ax = plt.subplots(figsize=(10, 8))
# R vs F 기준 평균 M 히트맵
pivot = rfm.pivot_table(values="monetary", index="R_score", columns="F_score", aggfunc="mean")
sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax,
            linewidths=0.5, cbar_kws={"label": "평균 M (원)"})
ax.set_title("RFM 히트맵 — R vs F 기준 평균 구매금액(M)", fontsize=12, fontweight='bold')
ax.set_xlabel("F 스코어 (구매 빈도)")
ax.set_ylabel("R 스코어 (최근성)")
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer2_rfm_heatmap.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer2_rfm_heatmap.png")

# Chart 3: 세그먼트별 GMV 파이차트
fig, ax = plt.subplots(figsize=(10, 8))
segs_pie = seg_summary.sort_values("total_gmv", ascending=False)
colors_pie = [seg_colors.get(s, "#ccc") for s in segs_pie["segment"]]
wedges, texts, autotexts = ax.pie(
    segs_pie["total_gmv"],
    labels=segs_pie["segment"],
    autopct='%1.1f%%',
    colors=colors_pie,
    startangle=140,
    pctdistance=0.82,
    textprops={'fontsize': 9}
)
ax.set_title("세그먼트별 GMV 비중 (2024년)", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer2_gmv_pie.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer2_gmv_pie.png")

# Chart 4: RFM 스코어 산점도 (R vs F, M=점 크기)
fig, ax = plt.subplots(figsize=(10, 8))
sample = rfm.sample(min(3000, len(rfm)), random_state=42)
colors_scatter = [seg_colors.get(s, "#ccc") for s in sample["segment"]]
scatter = ax.scatter(
    sample["F_score"] + np.random.uniform(-0.2, 0.2, len(sample)),
    sample["R_score"] + np.random.uniform(-0.2, 0.2, len(sample)),
    c=colors_scatter,
    s=sample["M_score"] * 20,
    alpha=0.5, edgecolors='none'
)
ax.set_xlabel("F 스코어", fontsize=11)
ax.set_ylabel("R 스코어", fontsize=11)
ax.set_title("RFM 세그먼트 산점도\n(점 크기=M 스코어, 색상=세그먼트)", fontsize=12, fontweight='bold')

# 범례
legend_patches = [mpatches.Patch(color=v, label=k) for k, v in seg_colors.items()
                  if k in sample["segment"].values]
ax.legend(handles=legend_patches, loc='lower right', fontsize=7, framealpha=0.8)
ax.set_xticks([1, 2, 3, 4, 5])
ax.set_yticks([1, 2, 3, 4, 5])
ax.grid(alpha=0.2)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer2_rfm_scatter.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer2_rfm_scatter.png")

# ─────────────────────────────────────────
# 7. 핵심 수치 출력
# ─────────────────────────────────────────
print("\n[Layer 2 완료] 핵심 수치:")
top3 = seg_summary.head(3)
for _, row in top3.iterrows():
    print(f"  {row['segment']}: {row['user_count']:,}명 | GMV {row['gmv_bn']:.1f}억 ({row['gmv_pct']:.1f}%)")

# RFM 데이터 저장 (Layer 5에서 재사용)
rfm.to_csv(f"{BASE}/analysis/rfm_result.csv", index=False)
print(f"\nRFM 결과 저장: analysis/rfm_result.csv")
