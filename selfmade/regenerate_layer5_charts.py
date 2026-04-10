"""
Phase 5 차트 재생성 스크립트
============================
AB_METRICS 수정 후 새로 생성된 campaigns.csv / campaign_logs.csv 기반으로
layer5_*.png 차트를 모두 재생성.

저장 위치: selfmade/ppt_charts/
실행: python selfmade/regenerate_layer5_charts.py
"""

import matplotlib
matplotlib.use('Agg')

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from statsmodels.stats.multitest import multipletests
import warnings
warnings.filterwarnings('ignore')

try:
    import koreanize_matplotlib
except ImportError:
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False

# -- 경로 설정 ----------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))  # selfmade/
CHART_DIR = os.path.join(BASE, "ppt_charts")
RFM_PATH = os.path.join(BASE, "..", "analysis", "rfm_result.csv")
CAMPAIGNS_PATH = os.path.join(BASE, "campaigns.csv")
LOGS_PATH = os.path.join(BASE, "campaign_logs.csv")

os.makedirs(CHART_DIR, exist_ok=True)
np.random.seed(42)

print("=" * 60)
print("Phase 5 차트 재생성 시작")
print("=" * 60)

# -- 데이터 로딩 --------------------------------------------------------------
print("\n[데이터 로딩]")
campaigns = pd.read_csv(CAMPAIGNS_PATH)
campaign_logs = pd.read_csv(LOGS_PATH)
rfm = pd.read_csv(RFM_PATH)

print(f"  campaigns:     {len(campaigns):,}개")
print(f"  campaign_logs: {len(campaign_logs):,}건")
print(f"  rfm:           {len(rfm):,}명")

# -- 캠페인별 이벤트 집계 -----------------------------------------------------
funnel_pivot = (
    campaign_logs.groupby(["campaign_id", "event_type"])["user_id"]
    .count()
    .unstack(fill_value=0)
    .reset_index()
)
funnel_pivot.columns.name = None

camp_perf = campaigns.merge(funnel_pivot, on="campaign_id", how="left").fillna(0)

# sent 컬럼 (send 또는 target_user_count)
sent_col = "send" if "send" in camp_perf.columns else "target_user_count"

for event in ["open", "click", "purchase", "block"]:
    if event in camp_perf.columns:
        camp_perf[f"{event}_rate"] = camp_perf[event] / camp_perf[sent_col].replace(0, np.nan)

camp_perf.rename(columns={"purchase_rate": "purchase_cvr"}, inplace=True)
if "purchase_cvr" not in camp_perf.columns and "purchase" in camp_perf.columns:
    camp_perf["purchase_cvr"] = camp_perf["purchase"] / camp_perf[sent_col].replace(0, np.nan)

event_order = [c for c in ["send", "open", "click", "purchase"] if c in camp_perf.columns]

# ============================================================================
# Chart 1: 캠페인 퍼널 (깔때기 모양, v2 스타일)
# ============================================================================
print("\n[1/5] 캠페인 퍼널 차트 생성 중...")

funnel_totals = camp_perf[event_order].sum()

agg_cols = {c: (c, "mean") for c in ["open_rate", "click_rate", "purchase_cvr", "block_rate"]
            if c in camp_perf.columns}
agg_cols["n_campaigns"] = ("campaign_id", "count")

labels_kr  = {"send": "발송", "open": "오픈", "click": "클릭", "purchase": "구매"}
colors_fnl = ["#2E86AB", "#4EAFC6", "#F18F01", "#C73E1D"]
funnel_vals   = [funnel_totals[e] for e in event_order]
funnel_labels = [labels_kr.get(e, e) for e in event_order]
base_val = funnel_vals[0]
pct_of_send = [v / base_val * 100 for v in funnel_vals]  # 발송 기준 %

# 단계별 이탈률 (전 단계 대비 %, 표시용)
drop_pct = []
for i in range(1, len(funnel_vals)):
    prev = funnel_vals[i-1]
    curr = funnel_vals[i]
    drop = (prev - curr) / prev * 100 if prev > 0 else 0
    drop_pct.append(drop)

# 최대 병목: 발송 기준 절대 이탈량 기준 (오픈→클릭 구간이 실제 병목)
abs_drop = [funnel_vals[i] - funnel_vals[i+1] for i in range(len(funnel_vals)-1)]
max_drop_idx = int(np.argmax(abs_drop))  # 절대 이탈 인원이 가장 많은 구간

fig, ax = plt.subplots(figsize=(11, 7))
ax.set_xlim(-2, 12)   # 왼쪽 여백 -2 확보
ax.set_ylim(0, 10)
ax.axis('off')

n = len(funnel_vals)
max_w, min_w = 8.0, 1.5
widths = [max_w - (max_w - min_w) * i / (n - 1) for i in range(n)]
step_h = 8.5 / n
top_y  = 9.2

for i in range(n):
    y_top = top_y - i * step_h
    y_bot = y_top - step_h + 0.05
    w_top = widths[i]
    w_bot = widths[i+1] if i+1 < n else min_w * 0.6
    x_center = 5.0

    # 사다리꼴 폴리곤
    xs = [x_center - w_top/2, x_center + w_top/2,
          x_center + w_bot/2, x_center - w_bot/2]
    ys = [y_top, y_top, y_bot, y_bot]
    ax.fill(xs, ys, color=colors_fnl[i], alpha=0.90, zorder=2)
    ax.plot(xs + [xs[0]], ys + [ys[0]], color='white', linewidth=1.5, zorder=3)

    mid_y = (y_top + y_bot) / 2
    # 단계명
    ax.text(x_center, mid_y + 0.13, funnel_labels[i],
            ha='center', va='center', fontsize=12, fontweight='bold',
            color='white', zorder=4)
    # 건수
    ax.text(x_center, mid_y - 0.22, f"{funnel_vals[i]:,.0f}건",
            ha='center', va='center', fontsize=10, color='white', zorder=4)

    # 오른쪽: 발송 기준 %
    ax.text(x_center + w_top/2 + 0.25, mid_y, f"{pct_of_send[i]:.2f}%",
            ha='left', va='center', fontsize=10, color=colors_fnl[i],
            fontweight='bold', zorder=4)

    # 이탈률 — 최대 병목 구간은 오른쪽, 나머지는 왼쪽에 표시 (첫 단계 제외)
    if i > 0:
        drop = drop_pct[i-1]
        is_max = (i - 1 == max_drop_idx)
        drop_color = '#C73E1D' if is_max else '#666666'
        fw = 'bold' if is_max else 'normal'
        if is_max:
            # 최대 병목 이탈률은 오른쪽에 표시 (박스 화살표와 겹치지 않게)
            ax.text(x_center + widths[i]/2 + 0.2, y_top,
                    f"v {drop:.1f}%p 이탈",
                    ha='left', va='center', fontsize=8.5,
                    color=drop_color, fontweight=fw, zorder=4)
        else:
            ax.text(x_center - widths[i]/2 - 0.2, y_top,
                    f"v {drop:.1f}%p 이탈",
                    ha='right', va='center', fontsize=8.5,
                    color=drop_color, fontweight=fw, zorder=4)

# 최대 병목 스타 박스 — 왼쪽 바깥 여백에 표시
# 화살표는 오픈→클릭 경계선(y_top of click 단계)을 가리킴
boundary_y = top_y - (max_drop_idx + 1) * step_h   # 경계선 y (클릭 단계의 top)
box_x = -0.8                                         # 박스 x (왼쪽 바깥)
# 경계선 위의 깔때기 왼쪽 모서리 x
arrow_target_x = 5.0 - widths[max_drop_idx + 1] / 2

ax.annotate(
    f"* 최대 병목\n{funnel_labels[max_drop_idx]}->{funnel_labels[max_drop_idx+1]}\n-{drop_pct[max_drop_idx]:.1f}%p",
    xy=(arrow_target_x, boundary_y),        # 화살표 끝: 경계선
    xytext=(box_x, boundary_y),             # 박스: 같은 y, 왼쪽 바깥
    fontsize=8, color='#C73E1D', fontweight='bold',
    ha='center', va='center', zorder=5,
    bbox=dict(boxstyle='round,pad=0.4', facecolor='#FFF3CD',
              edgecolor='#C73E1D', linewidth=1.5),
    arrowprops=dict(arrowstyle='->', color='#C73E1D', lw=1.5),
)

ax.set_title("캠페인 퍼널 분석 (send -> open -> click -> purchase)",
             fontsize=13, fontweight='bold', pad=12)
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, "layer5_campaign_funnel.png"), dpi=150, bbox_inches='tight')
plt.close()
print("  -> layer5_campaign_funnel.png 저장 완료")

# 퍼널 수치 출력 (PPT 업데이트용)
print(f"\n  [퍼널 수치 - PPT 업데이트용]")
for i, evt in enumerate(event_order):
    val = funnel_totals[evt]
    if i == 0:
        print(f"    {evt:10s}: {val:>10,.0f}  (기준)")
    else:
        prev = funnel_totals[event_order[i-1]]
        rate = val / prev * 100 if prev > 0 else 0
        print(f"    {evt:10s}: {val:>10,.0f}  ({rate:.1f}%)")

rate_cols = [c for c in ["open_rate", "click_rate", "purchase_cvr", "block_rate"] if c in camp_perf.columns]
print(f"\n  [평균 전환율]")
for col in rate_cols:
    print(f"    {col}: {camp_perf[col].mean()*100:.2f}%")

# ============================================================================
# Chart 2: A/B 검정 (curation vs ranking)
# ============================================================================
print("\n[2/5] A/B 검정 차트 생성 중...")

if "message_type" in camp_perf.columns:
    ab_results = []
    rate_cols_ab = [c for c in ["open_rate", "click_rate", "purchase_cvr", "block_rate"]
                    if c in camp_perf.columns]

    msg_types = camp_perf["message_type"].unique()
    if len(msg_types) >= 2:
        mt_a, mt_b = msg_types[0], msg_types[1]
        grp_a = camp_perf[camp_perf["message_type"] == mt_a]
        grp_b = camp_perf[camp_perf["message_type"] == mt_b]

        for metric in rate_cols_ab:
            a_vals = grp_a[metric].dropna()
            b_vals = grp_b[metric].dropna()
            if len(a_vals) > 1 and len(b_vals) > 1:
                a_mean = a_vals.mean()
                b_mean = b_vals.mean()
                n_a = len(grp_a)
                n_b = len(grp_b)
                obs_a_pos = int(a_mean * n_a)
                obs_b_pos = int(b_mean * n_b)
                contingency = [[obs_a_pos, n_a - obs_a_pos],
                               [obs_b_pos, n_b - obs_b_pos]]
                try:
                    chi2, p_val, _, _ = stats.chi2_contingency(contingency)
                except Exception:
                    p_val = 1.0
                winner = mt_a if a_mean > b_mean else mt_b
                ab_results.append({
                    "metric": metric,
                    f"{mt_a}": f"{a_mean*100:.2f}%",
                    f"{mt_b}": f"{b_mean*100:.2f}%",
                    "p_value": round(p_val, 4),
                    "유의": "O" if p_val < 0.05 else "-",
                    "winner": winner,
                })

        ab_df = pd.DataFrame(ab_results)
        print(f"\n  [A/B 검정 요약 - PPT 업데이트용]")
        print(ab_df.to_string(index=False))

        # 차트
        fig, axes = plt.subplots(1, len(rate_cols_ab), figsize=(4.5 * len(rate_cols_ab), 5))
        if len(rate_cols_ab) == 1:
            axes = [axes]
        colors_ab = {mt_a: '#2E86AB', mt_b: '#C73E1D'}
        for ax, metric in zip(axes, rate_cols_ab):
            vals = [grp_a[metric].mean() * 100, grp_b[metric].mean() * 100]
            bars = ax.bar([mt_a, mt_b], vals,
                          color=[colors_ab[mt_a], colors_ab[mt_b]],
                          edgecolor='white', width=0.5)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, v + 0.1,
                        f"{v:.1f}%", ha='center', va='bottom', fontsize=9, fontweight='bold')
            ax.set_title(metric.replace("_", " ").title(), fontsize=10, fontweight='bold')
            ax.set_ylabel("%")
            ax.grid(axis='y', alpha=0.3)
        axes[-1].legend(
            handles=[mpatches.Patch(color=colors_ab[mt], label=mt) for mt in [mt_a, mt_b]],
            fontsize=8
        )
        plt.suptitle("A/B 검정: curation vs ranking 메시지 전략", fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(CHART_DIR, "layer5_ab_test_result.png"), dpi=150, bbox_inches='tight')
        plt.close()
        print("  -> layer5_ab_test_result.png 저장 완료")

# ============================================================================
# Chart 3: Segment x Message Type 히트맵
# ============================================================================
print("\n[3/5] 세그먼트 x 메시지 타입 히트맵 생성 중...")

if "message_type" in camp_perf.columns and "target_segment" in camp_perf.columns \
        and "purchase_cvr" in camp_perf.columns:
    seg_msg_matrix = camp_perf.pivot_table(
        index="target_segment",
        columns="message_type",
        values="purchase_cvr",
        aggfunc="mean"
    ) * 100

    print(f"\n  [세그먼트 x 메시지 CVR - PPT 업데이트용]")
    print(seg_msg_matrix.round(2).to_string())

    fig, ax = plt.subplots(figsize=(9, 7))
    plot_data = seg_msg_matrix.copy()
    sns.heatmap(
        plot_data,
        annot=True,
        fmt=".1f",
        cmap="YlOrRd",
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "CVR (%)"},
    )
    ax.set_title("Segment x Message Type 교차 분석\n(Purchase CVR %)", fontsize=13, fontweight='bold')
    ax.set_xlabel("메시지 타입", fontsize=11)
    ax.set_ylabel("타겟 세그먼트", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(CHART_DIR, "layer5_segment_message_matrix.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print("  -> layer5_segment_message_matrix.png 저장 완료")

# ============================================================================
# Chart 4: 시즌 vs 일반 캠페인
# ============================================================================
print("\n[4/5] 시즌 vs 일반 캠페인 비교 차트 생성 중...")

SEASON_KEYWORDS = ["pepero", "valentine", "white_day", "christmas", "childrens", "parents", "teachers"]

def classify_seasonal(row):
    # occasion_category 컬럼 있으면 우선 사용 (special=시즌, daily=일반)
    if "occasion_category" in row.index:
        return str(row.get("occasion_category", "daily")).lower() == "special"
    name_seasonal = any(kw in str(row.get("campaign_name", "")).lower() for kw in SEASON_KEYWORDS)
    occasion_seasonal = str(row.get("gift_occasion", "general")).lower() != "general" \
        if "gift_occasion" in row.index else False
    return name_seasonal or occasion_seasonal

camp_perf["is_seasonal"] = camp_perf.apply(classify_seasonal, axis=1)
camp_perf["season_label"] = camp_perf["is_seasonal"].map({True: "시즌 캠페인", False: "일반 캠페인"})

plot_metrics = [c for c in ["open_rate", "click_rate", "purchase_cvr", "block_rate"] if c in camp_perf.columns]
agg_season = {c: (c, "mean") for c in plot_metrics}
agg_season["count"] = ("campaign_id", "count")
seasonal_compare = camp_perf.groupby("season_label").agg(**agg_season).reset_index()

print(f"\n  [시즌 vs 일반 - PPT 업데이트용]")
print(seasonal_compare.to_string(index=False))

metric_display = {"open_rate": "Open Rate", "click_rate": "Click Rate",
                  "purchase_cvr": "Purchase CVR", "block_rate": "Block Rate"}
fig, axes = plt.subplots(1, len(plot_metrics), figsize=(4.5 * len(plot_metrics), 5))
if len(plot_metrics) == 1:
    axes = [axes]
colors_sn = {"시즌 캠페인": "#FEE500", "일반 캠페인": "#94A3B8"}
for ax, metric in zip(axes, plot_metrics):
    for i, (_, row) in enumerate(seasonal_compare.iterrows()):
        ax.bar(i, row[metric] * 100, color=list(colors_sn.values())[i],
               edgecolor='#333', width=0.5)
        ax.text(i, row[metric]*100 + 0.05, f"{row[metric]*100:.1f}%", ha='center', fontsize=9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(list(seasonal_compare["season_label"]), fontsize=9)
    ax.set_title(metric_display.get(metric, metric), fontsize=10, fontweight='bold')
    ax.set_ylabel("%")
    ax.grid(axis='y', alpha=0.3)
handles = [mpatches.Patch(color=c, label=l) for l, c in colors_sn.items()]
axes[-1].legend(handles=handles, fontsize=8)
plt.suptitle("시즌 vs 일반 캠페인 성과 비교", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(CHART_DIR, "layer5_seasonal_vs_normal.png"), dpi=150, bbox_inches='tight')
plt.close()
print("  -> layer5_seasonal_vs_normal.png 저장 완료")

# ============================================================================
# Chart 5 & 6: ROAS 시뮬레이션 + 감도분석 (캠페인 로그와 무관, RFM 기반)
# ============================================================================
print("\n[5/5] ROAS 시뮬레이션 차트 재확인 중 (RFM 기반, 변동 없음)...")

K_FACTOR = 1.559
BASE_COST = 15

# user_count: RFM 세그먼트별 유저 수
# avg_aov: orders.csv 실제 1회 주문 평균 금액 (monetary는 누적 LTV라 ROAS 계산에 부적합)
orders_df = pd.read_csv(os.path.join(BASE, "orders.csv"))
rfm_aov = orders_df.merge(rfm[["sender_user_id", "segment"]], on="sender_user_id", how="left")
seg_aov_map = rfm_aov.groupby("segment")["total_amount_krw"].mean().to_dict()
overall_aov = orders_df["total_amount_krw"].mean()

rfm_summary = rfm.groupby("segment").agg(
    user_count=("sender_user_id", "count"),
).reset_index()
rfm_summary["avg_monetary"] = rfm_summary["segment"].apply(
    lambda s: seg_aov_map.get(s, overall_aov)  # 1회 주문 AOV 사용
)

# CVR = 발송 기준 실제 전환율 (open_rate x ctr x cvr 조건부 확률 체인)
# 캠페인 로그 실측 평균 purchase_cvr = 0.62% (발송 기준)
# 세그먼트별 상대 가중치 적용 (Champions가 Dormant 대비 약 2배 반응)
base_cvr = 0.0062  # 전체 평균 발송 기준 CVR (실측)
default_cvr_map = {
    "Champions":           base_cvr * 1.9,   # 0.0118 (~1.2%)
    "Can't Lose Them":     base_cvr * 1.6,   # 0.0099
    "Loyal Customers":     base_cvr * 1.5,   # 0.0093
    "Potential Loyalists": base_cvr * 1.2,   # 0.0074
    "New Customers":       base_cvr * 1.0,   # 0.0062
    "Casual":              base_cvr * 0.9,   # 0.0056
    "At Risk":             base_cvr * 0.7,   # 0.0043
    "Dormant":             base_cvr * 0.5,   # 0.0031
}
if "target_segment" in camp_perf.columns and "purchase_cvr" in camp_perf.columns:
    # 캠페인 세그먼트명(소문자)을 RFM 세그먼트명(대소문자)에 매칭하기 위해 정규화
    raw_map = camp_perf.groupby("target_segment")["purchase_cvr"].mean().to_dict()
    seg_cvr_map = {k.lower().replace("_", " "): v for k, v in raw_map.items()}
else:
    seg_cvr_map = {}

rfm_summary["expected_cvr"] = rfm_summary["segment"].apply(
    lambda s: seg_cvr_map.get(s.lower(), default_cvr_map.get(s, base_cvr))
)
rfm_summary["campaign_cost"] = rfm_summary["user_count"] * BASE_COST
rfm_summary["expected_gmv"] = (
    rfm_summary["user_count"] * rfm_summary["expected_cvr"]
    * rfm_summary["avg_monetary"] * K_FACTOR
)
rfm_summary["roas"] = rfm_summary["expected_gmv"] / rfm_summary["campaign_cost"]
rfm_summary_sorted = rfm_summary.sort_values("roas", ascending=False)

total_roas = rfm_summary['expected_gmv'].sum() / rfm_summary['campaign_cost'].sum()
print(f"\n  [ROAS 수치 - PPT 확인용]")
print(f"    전체 ROAS: {total_roas:,.0f}x")
print(f"    전체 GMV: {rfm_summary['expected_gmv'].sum()/1e8:.1f}억원")
print(f"    전체 비용: {rfm_summary['campaign_cost'].sum()/1e6:.0f}백만원")

# ROAS 시뮬레이션 + 감도분석 — 1x2 레이아웃 (슬라이드 16용)
sens_data = {}
for cost in [10, 15, 20]:
    sens_data[cost] = (rfm_summary_sorted["avg_monetary"]
                       * rfm_summary_sorted["expected_cvr"]
                       * K_FACTOR / cost).values

segments_sens = rfm_summary_sorted["segment"].tolist()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 7))

# 왼쪽: 세그먼트별 ROAS 시뮬레이션 (가로 막대)
# 색상 기준을 실제 수치 범위(최대 ~96x)에 맞게 설정
roas_vals = rfm_summary_sorted["roas"]
colors_roas = ['#C73E1D' if r >= 80 else '#F18F01' if r >= 50 else '#2E86AB'
               for r in roas_vals]
bars = ax1.barh(rfm_summary_sorted["segment"], roas_vals,
                color=colors_roas, edgecolor='white', height=0.6)
for bar, val in zip(bars, roas_vals):
    ax1.text(val + roas_vals.max() * 0.01,
             bar.get_y() + bar.get_height()/2,
             f"{val:.0f}x", va='center', fontsize=9)
ax1.axvline(x=40, color='gray', linestyle='--', linewidth=1.5)  # 전체 평균 40x
ax1.set_xlabel("ROAS (배수)", fontsize=11)
ax1.set_title(f"세그먼트별 ROAS 시뮬레이션\n(K-factor={K_FACTOR}, 비용={BASE_COST}원/건)",
              fontsize=11, fontweight='bold')
ax1.tick_params(axis='y', labelsize=10)
legend_patches = [
    mpatches.Patch(color='#C73E1D', label='80x 이상'),
    mpatches.Patch(color='#F18F01', label='50~80x'),
    mpatches.Patch(color='#2E86AB', label='50x 미만'),
    plt.Line2D([0], [0], color='gray', linestyle='--', label='전체 평균 40x'),
]
ax1.legend(handles=legend_patches, fontsize=9)
ax1.grid(axis='x', alpha=0.3)

# 오른쪽: ROAS 감도분석 (비용 시나리오별)
x = np.arange(len(segments_sens))
w = 0.25
colors_sens = ["#2ED573", "#FEE500", "#FF4757"]
labels_sens = ["10원/건 (최저)", "15원/건 (기본)", "20원/건 (최고)"]
for i, (cost, color, label) in enumerate(zip([10, 15, 20], colors_sens, labels_sens)):
    ax2.bar(x + (i - 1) * w, sens_data[cost], width=w, color=color,
            edgecolor='#333', label=label, alpha=0.85)
ax2.axhline(y=100, color='gray', linestyle='--', linewidth=1.2, label='100x 기준')
ax2.set_xticks(x)
ax2.set_xticklabels(segments_sens, rotation=90, ha='center', fontsize=9)
ax2.set_ylabel("ROAS (배수)", fontsize=11)
ax2.set_title(f"ROAS 감도분석\n비용 10/15/20원/건 시나리오 (K-factor={K_FACTOR})",
              fontsize=11, fontweight='bold')
ax2.legend(fontsize=9)
ax2.grid(axis='y', alpha=0.3)

plt.suptitle("ROAS 시뮬레이션 - 캠페인 예산 승인 근거", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.18, wspace=0.35)
plt.savefig(os.path.join(CHART_DIR, "layer5_roas_simulation.png"), dpi=150, bbox_inches='tight')
plt.close()
print("  -> layer5_roas_simulation.png (1x2 레이아웃) 저장 완료")

# ============================================================================
print("\n" + "=" * 60)
print("차트 재생성 완료!")
print(f"저장 위치: {CHART_DIR}")
print("=" * 60)
print("\n재생성된 파일:")
for fname in sorted(os.listdir(CHART_DIR)):
    if fname.startswith("layer5_") and fname.endswith(".png"):
        fpath = os.path.join(CHART_DIR, fname)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {fname:<45} ({size_kb:.0f} KB)")