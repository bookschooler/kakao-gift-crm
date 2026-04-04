"""
Layer 1: EDA & 시즌 분석
=========================
목적: 카카오 선물하기 GMV 트렌드, 시즌 패턴, 카테고리 믹스, 유저 분포를 파악한다.
핵심 인사이트:
  - 월별 GMV MoM/YoY 성장률
  - STL Decomposition으로 시즌성 분리
  - 빼빼로데이·발렌타인 등 시즌 이벤트 피크
  - 카테고리별 GMV 비중
  - 유저 성별/연령/채널 분포
"""

import matplotlib
matplotlib.use('Agg')  # GUI 없이 차트 저장

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from statsmodels.tsa.seasonal import STL

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

BASE = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift"
CHART_DIR = f"{BASE}/analysis/charts"

# ─────────────────────────────────────────
# 1. 데이터 로딩
# ─────────────────────────────────────────
print("=" * 60)
print("[Layer 1] EDA & 시즌 분석 시작")
print("=" * 60)

orders = pd.read_csv(f"{BASE}/orders.csv", parse_dates=["created_at", "updated_at"])
users  = pd.read_csv(f"{BASE}/users.csv")

# 완료된 주문만 분석 (cancelled 제외)
orders_active = orders[orders["order_status"] != "cancelled"].copy()
print(f"전체 주문: {len(orders):,}건 | 유효 주문(cancelled 제외): {len(orders_active):,}건")

# ─────────────────────────────────────────
# 2. 월별 GMV 트렌드 (MoM, YoY)
# ─────────────────────────────────────────
orders_active["ym"] = orders_active["created_at"].dt.to_period("M")
monthly_gmv = (
    orders_active.groupby("ym")["total_amount_krw"]
    .sum()
    .reset_index()
    .sort_values("ym")
)
monthly_gmv["gmv_bn"] = monthly_gmv["total_amount_krw"] / 1e8  # 억원 단위

# MoM 성장률
monthly_gmv["mom_pct"] = monthly_gmv["total_amount_krw"].pct_change() * 100

# YoY 성장률 (12개월 전 대비)
monthly_gmv["yoy_pct"] = monthly_gmv["total_amount_krw"].pct_change(12) * 100

print("\n--- 월별 GMV 요약 ---")
print(monthly_gmv[["ym", "gmv_bn", "mom_pct", "yoy_pct"]].to_string(index=False))

# 최고/최저 GMV 월
top_month = monthly_gmv.loc[monthly_gmv["total_amount_krw"].idxmax()]
bot_month = monthly_gmv.loc[monthly_gmv["total_amount_krw"].idxmin()]
print(f"\n최고 GMV 월: {top_month['ym']} ({top_month['gmv_bn']:.1f}억원)")
print(f"최저 GMV 월: {bot_month['ym']} ({bot_month['gmv_bn']:.1f}억원)")

# ─────────────────────────────────────────
# 3. STL Decomposition
# ─────────────────────────────────────────
# 일별 GMV 집계 후 STL 적용
orders_active["date"] = orders_active["created_at"].dt.date
daily_gmv = (
    orders_active.groupby("date")["total_amount_krw"]
    .sum()
    .reset_index()
    .sort_values("date")
)
daily_gmv["date"] = pd.to_datetime(daily_gmv["date"])
daily_gmv = daily_gmv.set_index("date")

# 누락된 날짜 보간 (연속 시계열 필요)
full_idx = pd.date_range(daily_gmv.index.min(), daily_gmv.index.max(), freq="D")
daily_gmv = daily_gmv.reindex(full_idx).interpolate(method="linear")

# STL: period=7 (주간 시즌성) — 월간은 period=30도 가능
stl = STL(daily_gmv["total_amount_krw"], period=7, robust=True)
stl_result = stl.fit()

print("\n--- STL Decomposition 완료 ---")
print(f"  시즌성 성분 표준편차: {stl_result.seasonal.std():,.0f}원")
print(f"  추세 성분 최솟값: {stl_result.trend.min():,.0f}원")
print(f"  추세 성분 최댓값: {stl_result.trend.max():,.0f}원")

# ─────────────────────────────────────────
# 4. 시즌 이벤트 피크 레이블링
# ─────────────────────────────────────────
season_events = {
    # (월, 일): 이벤트명
    (2, 14): "발렌타인데이",
    (3, 14): "화이트데이",
    (5, 5):  "어린이날",
    (5, 8):  "어버이날",
    (6, 1):  "스승의날",
    (11, 11): "빼빼로데이",
    (12, 25): "크리스마스",
    (1, 1):  "신정",
}

# 월별 GMV에 시즌 이벤트 표시용 — 해당 월에 이벤트가 있으면 레이블 부여
def get_season_label(period_obj):
    m = period_obj.month
    labels = []
    for (em, ed), name in season_events.items():
        if em == m:
            labels.append(name)
    return ", ".join(labels) if labels else ""

monthly_gmv["season_label"] = monthly_gmv["ym"].apply(get_season_label)
season_months = monthly_gmv[monthly_gmv["season_label"] != ""]
print("\n--- 시즌 이벤트 월 GMV ---")
print(season_months[["ym", "gmv_bn", "season_label"]].to_string(index=False))

# ─────────────────────────────────────────
# 5. 카테고리 믹스
# ─────────────────────────────────────────
cat_gmv = (
    orders_active.groupby("category_l1")["total_amount_krw"]
    .agg(["sum", "count"])
    .reset_index()
    .rename(columns={"sum": "gmv", "count": "orders"})
    .sort_values("gmv", ascending=False)
)
cat_gmv["gmv_share_pct"] = cat_gmv["gmv"] / cat_gmv["gmv"].sum() * 100
cat_gmv["gmv_bn"] = cat_gmv["gmv"] / 1e8

print("\n--- 카테고리별 GMV 비중 ---")
print(cat_gmv[["category_l1", "gmv_bn", "gmv_share_pct", "orders"]].to_string(index=False))

# ─────────────────────────────────────────
# 6. 유저 분포
# ─────────────────────────────────────────
print("\n--- 유저 성별 분포 ---")
print(users["gender"].value_counts())

print("\n--- 유저 연령대 분포 ---")
print(users["age_group"].value_counts().sort_index())

print("\n--- 유저 획득 채널 분포 ---")
print(users["acquisition_channel"].value_counts())

# ─────────────────────────────────────────
# 7. 차트 저장
# ─────────────────────────────────────────

# Chart 1: 월별 GMV 트렌드 + 시즌 이벤트 피크
fig, ax = plt.subplots(figsize=(16, 6))
x_vals = range(len(monthly_gmv))
bars = ax.bar(x_vals, monthly_gmv["gmv_bn"], color="#FEE500", edgecolor="#333", linewidth=0.5, alpha=0.85)

# 시즌 이벤트 강조
for _, row in season_months.iterrows():
    idx = monthly_gmv[monthly_gmv["ym"] == row["ym"]].index[0]
    bar_idx = monthly_gmv.index.get_loc(idx)
    bars[bar_idx].set_color("#FF6B00")
    ax.text(bar_idx, row["gmv_bn"] + 0.3, row["season_label"],
            ha='center', va='bottom', fontsize=7, color='#CC3300', rotation=45)

ax.set_xticks(x_vals)
ax.set_xticklabels([str(p) for p in monthly_gmv["ym"]], rotation=45, ha='right', fontsize=8)
ax.set_ylabel("GMV (억원)", fontsize=11)
ax.set_title("월별 GMV 트렌드 (주황=시즌 이벤트 월)", fontsize=13, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer1_monthly_gmv.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n차트 저장: layer1_monthly_gmv.png")

# Chart 2: STL Decomposition
fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)
stl_result.observed.plot(ax=axes[0], color='#2E86AB')
axes[0].set_title("원본 일별 GMV", fontsize=10)
stl_result.trend.plot(ax=axes[1], color='#A23B72')
axes[1].set_title("추세 성분 (Trend)", fontsize=10)
stl_result.seasonal.plot(ax=axes[2], color='#F18F01')
axes[2].set_title("시즌성 성분 (Seasonal)", fontsize=10)
stl_result.resid.plot(ax=axes[3], color='#C73E1D')
axes[3].set_title("잔차 성분 (Residual)", fontsize=10)
for ax in axes:
    ax.grid(alpha=0.2)
    ax.set_ylabel("GMV (원)", fontsize=8)
plt.suptitle("STL Decomposition — 일별 GMV (period=7)", fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer1_stl_decomposition.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer1_stl_decomposition.png")

# Chart 3: 카테고리 GMV 비중 파이차트
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

colors = plt.cm.Set3(np.linspace(0, 1, len(cat_gmv)))
wedges, texts, autotexts = ax1.pie(
    cat_gmv["gmv"], labels=cat_gmv["category_l1"],
    autopct='%1.1f%%', colors=colors, startangle=140,
    pctdistance=0.8, textprops={'fontsize': 8}
)
ax1.set_title("카테고리별 GMV 비중", fontsize=12, fontweight='bold')

# 주문 건수 기준 바 차트
ax2.barh(cat_gmv["category_l1"], cat_gmv["orders"], color=colors)
ax2.set_xlabel("주문 건수", fontsize=10)
ax2.set_title("카테고리별 주문 건수", fontsize=12, fontweight='bold')
ax2.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer1_category_mix.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer1_category_mix.png")

# Chart 4: 유저 분포 (3-panel)
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# 성별
gender_cnt = users["gender"].value_counts()
axes[0].pie(gender_cnt, labels=gender_cnt.index, autopct='%1.1f%%',
            colors=['#4A90D9', '#F5A0C0'], startangle=90)
axes[0].set_title("성별 분포", fontsize=11, fontweight='bold')

# 연령대
age_cnt = users["age_group"].value_counts().sort_index()
axes[1].bar(age_cnt.index, age_cnt.values, color='#FEE500', edgecolor='#333')
axes[1].set_title("연령대 분포", fontsize=11, fontweight='bold')
axes[1].set_xlabel("연령대")
axes[1].set_ylabel("유저 수")
axes[1].tick_params(axis='x', rotation=30)

# 획득 채널
ch_cnt = users["acquisition_channel"].value_counts()
axes[2].bar(ch_cnt.index, ch_cnt.values, color='#FF6B00', edgecolor='#333')
axes[2].set_title("획득 채널 분포", fontsize=11, fontweight='bold')
axes[2].set_xlabel("채널")
axes[2].set_ylabel("유저 수")
axes[2].tick_params(axis='x', rotation=30)

plt.suptitle("유저 분포 분석", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer1_user_distribution.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer1_user_distribution.png")

print("\n[Layer 1 완료]")
print(f"  총 유효 주문: {len(orders_active):,}건")
print(f"  전체 GMV: {orders_active['total_amount_krw'].sum() / 1e8:.1f}억원")
print(f"  분석 기간: {orders_active['created_at'].min().date()} ~ {orders_active['created_at'].max().date()}")
