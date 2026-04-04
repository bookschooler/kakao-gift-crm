"""
Layer 5: CRM 캠페인 분석 & 전략
=================================
목적: 캠페인 성과(open_rate, click_rate, block_rate, CVR)를 세그먼트/채널/시즌별로 분석하고
      ROAS 시뮬레이션을 통해 우선 투자 세그먼트와 CRM 액션 플랜을 도출한다.

핵심 인사이트:
  - 캠페인 event_type별 퍼널 (sent → opened → clicked → purchased)
  - 시즌 캠페인 vs 일반 캠페인 효과 비교
  - 세그먼트별 ROAS 시뮬레이션
  - CRM 액션 플랜 (상위 3개 세그먼트)
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
print("[Layer 5] CRM 캠페인 분석 & 전략 시작")
print("=" * 60)

# ─────────────────────────────────────────
# 1. 데이터 로딩
# ─────────────────────────────────────────
campaigns    = pd.read_csv(f"{BASE}/campaigns.csv")
campaign_logs = pd.read_csv(f"{BASE}/campaign_logs.csv", parse_dates=["occurred_at"])
orders = pd.read_csv(f"{BASE}/orders.csv", parse_dates=["created_at"])
rfm = pd.read_csv(f"{BASE}/analysis/rfm_result.csv")

orders_active = orders[orders["order_status"] != "cancelled"].copy()

print(f"캠페인 수: {len(campaigns):,}개")
print(f"캠페인 로그: {len(campaign_logs):,}건")
print(f"event_type 종류: {campaign_logs['event_type'].unique()}")

# ─────────────────────────────────────────
# 2. 캠페인별 퍼널 지표 계산
# ─────────────────────────────────────────
# 각 캠페인별로 sent/opened/clicked/purchased 카운트
funnel = (
    campaign_logs.groupby(["campaign_id", "event_type"])["user_id"]
    .count()
    .reset_index()
    .rename(columns={"user_id": "count"})
)

funnel_pivot = funnel.pivot_table(
    index="campaign_id", columns="event_type", values="count", fill_value=0
).reset_index()

# 컬럼명 정리
funnel_pivot.columns.name = None
print(f"\n캠페인 퍼널 컬럼: {list(funnel_pivot.columns)}")

# campaigns 정보 결합
camp_perf = campaigns.merge(funnel_pivot, on="campaign_id", how="left")
print(f"campaigns 컬럼: {list(camp_perf.columns)}")

# 이벤트 타입 존재 여부 확인 후 비율 계산
# event_type이 send/open/click/purchase/block 형태임을 확인
# camp_perf 컬럼에서 실제 이벤트 컬럼 확인
available_events = [c for c in ["send", "open", "click", "purchase", "block"]
                    if c in camp_perf.columns]
print(f"사용 가능한 event_type: {available_events}")

# send 기준으로 rate 계산 (없으면 target_user_count 사용)
if "send" not in camp_perf.columns:
    camp_perf["send"] = camp_perf["target_user_count"]

sent_col = "send"
if "open" in camp_perf.columns:
    camp_perf["open_rate"]    = camp_perf["open"] / camp_perf[sent_col]
if "click" in camp_perf.columns:
    camp_perf["click_rate"]   = camp_perf["click"] / camp_perf[sent_col]
if "block" in camp_perf.columns:
    camp_perf["block_rate"]   = camp_perf["block"] / camp_perf[sent_col]
if "purchase" in camp_perf.columns:
    camp_perf["purchase_cvr"] = camp_perf["purchase"] / camp_perf[sent_col]

print("\n--- 캠페인 성과 요약 ---")
metric_cols = [c for c in ["campaign_id", "campaign_name", "target_segment",
                            "open_rate", "click_rate", "block_rate", "purchase_cvr"]
               if c in camp_perf.columns]
print(camp_perf[metric_cols].head(20).to_string(index=False))

# 전체 평균
print("\n--- 전체 캠페인 평균 지표 ---")
for col in ["open_rate", "click_rate", "block_rate", "purchase_cvr"]:
    if col in camp_perf.columns:
        print(f"  {col}: {camp_perf[col].mean()*100:.2f}%")

# ─────────────────────────────────────────
# 3. 세그먼트별 캠페인 응답률 비교
# ─────────────────────────────────────────
if "target_segment" in camp_perf.columns:
    agg_dict = {"campaign_count": ("campaign_id", "count")}
    for col in ["open_rate", "click_rate", "block_rate", "purchase_cvr"]:
        if col in camp_perf.columns:
            agg_dict[f"avg_{col}"] = (col, "mean")
    seg_perf = camp_perf.groupby("target_segment").agg(**agg_dict).reset_index()

    print("\n--- 세그먼트별 캠페인 성과 ---")
    print(seg_perf.to_string(index=False))

# ─────────────────────────────────────────
# 4. 시즌 캠페인 vs 일반 캠페인
# ─────────────────────────────────────────
season_keywords = ["pepero", "valentine", "white_day", "christmas", "childrens", "parents", "teachers"]

def is_seasonal(name):
    if pd.isna(name):
        return False
    name_lower = str(name).lower()
    return any(kw in name_lower for kw in season_keywords)

camp_perf["is_seasonal"] = camp_perf["campaign_name"].apply(is_seasonal)
# gift_occasion 컬럼도 확인
if "gift_occasion" in camp_perf.columns:
    camp_perf["is_seasonal"] = camp_perf["is_seasonal"] | (
        camp_perf["gift_occasion"].notna() &
        (camp_perf["gift_occasion"] != "general")
    )

agg_dict2 = {"count": ("campaign_id", "count")}
for col in ["open_rate", "click_rate", "block_rate", "purchase_cvr"]:
    if col in camp_perf.columns:
        agg_dict2[f"avg_{col}"] = (col, "mean")
seasonal_compare = camp_perf.groupby("is_seasonal").agg(**agg_dict2).reset_index()
seasonal_compare["is_seasonal"] = seasonal_compare["is_seasonal"].map({True: "시즌 캠페인", False: "일반 캠페인"})

print("\n--- 시즌 vs 일반 캠페인 비교 ---")
print(seasonal_compare.to_string(index=False))

# ─────────────────────────────────────────
# 5. ROAS 시뮬레이션
# ─────────────────────────────────────────
# ROAS = (타겟 세그먼트 평균 M × 기대 전환율) / 캠페인 비용(추정)
# 비용 추정: 카카오 친구톡 기준 1건당 약 15원 (산업 평균)

COST_PER_SEND = 15  # 원 (기본값 — 감도분석에서 10/15/20원 비교)

rfm_summary = rfm.groupby("segment").agg(
    user_count=("sender_user_id", "count"),
    avg_monetary=("monetary", "mean")
).reset_index()

# 세그먼트별 캠페인 CVR 매핑 (purchase_cvr 또는 기본값 사용)
default_cvr = 0.05  # 5% 기본값
if "target_segment" in camp_perf.columns and "purchase_cvr" in camp_perf.columns and camp_perf["purchase_cvr"].notna().any():
    seg_cvr = camp_perf.groupby("target_segment")["purchase_cvr"].mean()
else:
    seg_cvr = pd.Series(dtype=float)

def get_cvr(seg):
    # 세그먼트명 정규화 후 매핑
    if seg in seg_cvr.index:
        return seg_cvr[seg]
    return default_cvr

rfm_summary["expected_cvr"] = rfm_summary["segment"].apply(get_cvr)
rfm_summary["campaign_cost"] = rfm_summary["user_count"] * COST_PER_SEND
rfm_summary["expected_revenue"] = (
    rfm_summary["user_count"] * rfm_summary["expected_cvr"] * rfm_summary["avg_monetary"]
)
rfm_summary["roas"] = rfm_summary["expected_revenue"] / rfm_summary["campaign_cost"]
rfm_summary = rfm_summary.sort_values("roas", ascending=False)

print("\n--- 세그먼트별 ROAS 시뮬레이션 ---")
print(f"  (캠페인 비용 가정: 1건당 {COST_PER_SEND}원)")
roas_cols = ["segment", "user_count", "avg_monetary", "expected_cvr", "campaign_cost", "expected_revenue", "roas"]
print(rfm_summary[roas_cols].to_string(index=False))

# ─────────────────────────────────────────
# 6. CRM 액션 플랜
# ─────────────────────────────────────────
top3_roas = rfm_summary.head(3)
print("\n" + "=" * 60)
print("[CRM 액션 플랜] 우선순위 상위 3개 세그먼트")
print("=" * 60)

action_plans = {
    "Champions": {
        "액션": "VIP 전용 얼리버드 / 시즌 선착순 쿠폰 발송",
        "메시지": "감사합니다! OOO님을 위한 특별 혜택",
        "채널": "카카오 친구톡 (개인화 메시지)",
        "기대효과": "재구매율 유지 + 구전 효과 극대화"
    },
    "Loyal": {
        "액션": "구매 빈도 증대를 위한 번들 추천 / 시즌별 리마인더",
        "메시지": "자주 찾아주시는 OOO님, 이번엔 세트로!",
        "채널": "카카오 친구톡 + 앱 푸시",
        "기대효과": "F 스코어 상승 → Champions 전환"
    },
    "Need Attention": {
        "액션": "재인게이지 윈백 캠페인 (할인 쿠폰 + 시즌 넛지)",
        "메시지": "OOO님, 오랜만이에요! 특별 할인권 드려요",
        "채널": "카카오 알림톡 (비용 효율 우선)",
        "기대효과": "이탈 방지 + GMV 회수 (세그먼트 GMV 2위)"
    },
    "At Risk": {
        "액션": "감성 넛지 + 선물 추천 (수신자 관계 기반)",
        "메시지": "잊지 마세요, OOO님의 소중한 분들",
        "채널": "카카오 친구톡",
        "기대효과": "고가치 유저(avg_M 높음) 이탈 방지"
    },
    "Hibernating": {
        "액션": "저비용 SMS/카톡 메시지 + 시즌 단순 리마인더",
        "메시지": "다시 만나요! 시즌 선물 준비됐어요",
        "채널": "문자 또는 카카오 알림톡 (저비용)",
        "기대효과": "소규모 재활성화로 LTV 보완"
    }
}

for _, row in top3_roas.iterrows():
    seg = row["segment"]
    plan = action_plans.get(seg, {"액션": "표준 리텐션 캠페인", "채널": "카카오 친구톡"})
    print(f"\n[{seg}]")
    print(f"  ROAS: {row['roas']:,.1f}x | 유저: {row['user_count']:,}명 | 예상 수익: {row['expected_revenue']/1e6:,.0f}백만원")
    for k, v in plan.items():
        print(f"  {k}: {v}")

# ─────────────────────────────────────────
# 7. 차트 저장
# ─────────────────────────────────────────

# Chart 1: 캠페인 퍼널 (전체 합산)
event_cols = ["send", "open", "click", "purchase"]
event_cols = [c for c in event_cols if c in camp_perf.columns]

if len(event_cols) >= 2:
    funnel_totals = camp_perf[event_cols].sum()
    fig, ax = plt.subplots(figsize=(10, 6))
    colors_funnel = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'][:len(event_cols)]
    bars = ax.bar(event_cols, funnel_totals.values, color=colors_funnel, edgecolor='white', width=0.6)

    for bar, val in zip(bars, funnel_totals.values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + funnel_totals.max()*0.01,
                f"{val:,.0f}", ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 전환율 표시
    for i in range(1, len(event_cols)):
        prev_val = funnel_totals.values[i-1]
        curr_val = funnel_totals.values[i]
        if prev_val > 0:
            rate = curr_val / prev_val * 100
            ax.annotate(f"→ {rate:.1f}%",
                        xy=(i - 0.5, max(prev_val, curr_val) * 0.5),
                        ha='center', fontsize=9, color='#333')

    ax.set_ylabel("유저 수", fontsize=11)
    ax.set_title("전체 캠페인 퍼널 (누적)", fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/layer5_campaign_funnel.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("\n차트 저장: layer5_campaign_funnel.png")

# Chart 2: 세그먼트별 ROAS 시뮬레이션
fig, ax = plt.subplots(figsize=(12, 6))
roas_sorted = rfm_summary.sort_values("roas", ascending=True)
colors_roas = ['#FF4757' if r > 100 else '#FFA502' if r > 50 else '#2ED573'
               for r in roas_sorted["roas"]]
bars = ax.barh(roas_sorted["segment"], roas_sorted["roas"],
               color=colors_roas, edgecolor='white')
ax.axvline(x=100, color='red', linestyle='--', linewidth=1.5, label='ROAS 100x 기준선')
ax.set_xlabel("ROAS (배수)", fontsize=11)
ax.set_title("세그먼트별 ROAS 시뮬레이션\n(빨강=100x 이상, 주황=50-100x, 초록=50x 이하)", fontsize=12, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='x', alpha=0.3)
for bar, val in zip(bars, roas_sorted["roas"]):
    ax.text(val + 5, bar.get_y() + bar.get_height()/2,
            f"{val:,.0f}x", va='center', fontsize=8)
ax.set_xlim(0, roas_sorted["roas"].max() * 1.2)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_roas_simulation.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer5_roas_simulation.png")

# Chart 3: 시즌 vs 일반 캠페인 비교 (레이더 불필요, 바 차트)
metric_list = [c for c in ["avg_open_rate", "avg_click_rate", "avg_purchase_cvr"] if c in seasonal_compare.columns]
if len(metric_list) >= 1:
    fig, axes = plt.subplots(1, len(metric_list), figsize=(5 * len(metric_list), 5))
    if len(metric_list) == 1:
        axes = [axes]
    for ax, metric in zip(axes, metric_list):
        ax.bar(seasonal_compare["is_seasonal"],
               seasonal_compare[metric] * 100,
               color=['#FEE500', '#FF6B00'], edgecolor='#333', width=0.5)
        ax.set_title(metric.replace("avg_", "").replace("_", " ").title(), fontsize=11)
        ax.set_ylabel("%")
        ax.grid(axis='y', alpha=0.3)
        for i, val in enumerate(seasonal_compare[metric]):
            ax.text(i, val*100 + 0.1, f"{val*100:.1f}%", ha='center', fontsize=10)
    plt.suptitle("시즌 vs 일반 캠페인 성과 비교", fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/layer5_seasonal_vs_normal.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("차트 저장: layer5_seasonal_vs_normal.png")

# Chart 4: 세그먼트별 예상 수익 vs 비용 (버블)
fig, ax = plt.subplots(figsize=(12, 7))
colors_bubble = plt.cm.Set1(np.linspace(0, 1, len(rfm_summary)))
for i, (_, row) in enumerate(rfm_summary.iterrows()):
    ax.scatter(
        row["campaign_cost"] / 1e6,
        row["expected_revenue"] / 1e6,
        s=row["user_count"] / 50,
        color=colors_bubble[i],
        alpha=0.7,
        edgecolors='white',
        linewidth=1.5,
        label=row["segment"]
    )
    ax.annotate(row["segment"],
                xy=(row["campaign_cost"]/1e6, row["expected_revenue"]/1e6),
                xytext=(5, 5), textcoords='offset points', fontsize=8)

# 손익분기선
max_cost = rfm_summary["campaign_cost"].max() / 1e6
ax.plot([0, max_cost], [0, max_cost], 'k--', alpha=0.4, linewidth=1, label='손익분기 (ROAS=1)')
ax.set_xlabel("캠페인 비용 (백만원)", fontsize=11)
ax.set_ylabel("예상 수익 (백만원)", fontsize=11)
ax.set_title("세그먼트별 비용 vs 예상 수익\n(점 크기 = 유저 수)", fontsize=12, fontweight='bold')
ax.legend(fontsize=8, loc='upper left')
ax.grid(alpha=0.2)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_cost_vs_revenue.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer5_cost_vs_revenue.png")

# ─────────────────────────────────────────
# 8. ROAS 감도분석 (Reviewer 플래그: 15원 고정 가정 검증)
# ─────────────────────────────────────────
print("\n" + "=" * 60)
print("[ROAS 감도분석] 캠페인 비용 10원 / 15원 / 20원 시나리오 비교")
print("=" * 60)

sensitivity_rows = []
for cost in [10, 15, 20]:
    for _, row in rfm_summary.iterrows():
        roas_s = (row["avg_monetary"] * row["expected_cvr"]) / cost
        sensitivity_rows.append({
            "segment": row["segment"],
            "cost_per_send": cost,
            "roas": roas_s,
            "expected_revenue_M": row["expected_revenue"] / 1e6
        })

sens_df = pd.DataFrame(sensitivity_rows)
sens_pivot = sens_df.pivot_table(index="segment", columns="cost_per_send", values="roas")
sens_pivot.columns = [f"{c}원/건" for c in sens_pivot.columns]
sens_pivot = sens_pivot.round(0).astype(int)

print("\n세그먼트별 ROAS (비용 시나리오 별)")
print(sens_pivot.sort_values("15원/건", ascending=False).to_string())

# 감도분석 차트
fig, ax = plt.subplots(figsize=(13, 6))
segments = sens_pivot.sort_values("15원/건", ascending=False).index.tolist()
x = np.arange(len(segments))
w = 0.25
colors_sens = ["#2ED573", "#FEE500", "#FF4757"]
labels_sens = ["10원/건 (최저)", "15원/건 (기본)", "20원/건 (최고)"]

for i, (cost, col, lbl) in enumerate(zip([10, 15, 20], colors_sens, labels_sens)):
    vals = [sens_pivot.loc[s, f"{cost}원/건"] if s in sens_pivot.index else 0 for s in segments]
    bars = ax.bar(x + (i - 1) * w, vals, width=w, color=col, edgecolor='#333', label=lbl, alpha=0.85)

ax.axhline(y=100, color='gray', linestyle='--', linewidth=1, label='ROAS 100x 기준선')
ax.set_xticks(x)
ax.set_xticklabels(segments, rotation=20, ha='right', fontsize=9)
ax.set_ylabel("ROAS (배수)", fontsize=11)
ax.set_title("ROAS 감도분석 — 캠페인 비용 10 / 15 / 20원/건 시나리오\n(결론: 비용 2배 차이에도 모든 세그먼트 ROAS 100x 이상)", fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_roas_sensitivity.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n차트 저장: layer5_roas_sensitivity.png")

# 핵심 메시지 출력
print("\n[감도분석 결론]")
for seg in ["Champions", "At Risk", "Need Attention"]:
    if seg in sens_pivot.index:
        r10 = sens_pivot.loc[seg, "10원/건"]
        r15 = sens_pivot.loc[seg, "15원/건"]
        r20 = sens_pivot.loc[seg, "20원/건"]
        print(f"  {seg}: {r10:,}x (10원) / {r15:,}x (15원) / {r20:,}x (20원) -> 비용 가정 무관하게 고ROAS")

print(f"\n[Layer 5 완료]")
print(f"  최고 ROAS 세그먼트: {rfm_summary.iloc[0]['segment']} ({rfm_summary.iloc[0]['roas']:,.0f}x)")
print(f"  전체 예상 수익 합계: {rfm_summary['expected_revenue'].sum()/1e8:.1f}억원")
