"""
Layer 5: CRM 캠페인 분석 & 전략 (개선 버전 v2)
=================================================
개선 사항:
  - [0] Phase 4 인사이트 연결 (K-factor 수정, Golden Time 30일, Pay-it-forward)
  - [2] A/B 검정: Power Analysis + Chi-square + Holm-Bonferroni 보정
  - [3] Segment × Message 교차 분석 히트맵
  - [5] K-factor 1.559 기반 ROAS 시뮬레이션 재계산
  - [6] CRM 액션 플랜: Golden Time 30일, self-gift → 타인 전환, Pepero Day D-7 반영
"""

import matplotlib
matplotlib.use('Agg')  # 헤드리스 환경에서 차트 저장

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib  # 한글 폰트 설정

from scipy.stats import chi2_contingency, norm
from statsmodels.stats.multitest import multipletests

BASE      = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift"
DATA_DIR  = f"{BASE}/selfmade"
CHART_DIR = f"{BASE}/analysis/charts"

print("=" * 65)
print("[Layer 5 v2] CRM 캠페인 분석 & 전략 시작")
print("=" * 65)

# ─────────────────────────────────────────────────────────────
# 0. Phase 4 인사이트 연결 (전략 설계 전 반드시 선언)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 0] Phase 4 핵심 인사이트 → Phase 5 전략 연결")
print("=" * 65)

# Phase 4에서 도출된 수정된 K-factor
# (이전 버전의 K-factor 3.948은 전체 gift_receipts 유저 기준이었고,
#  실제 바이럴 유입 전환 유저만 기준으로 재산정하면 K-factor = 1.559)
KFACTOR_CORRECTED   = 1.559  # 수정된 K-factor (바이럴 전환 유저 기준)
GOLDEN_TIME_DAYS    = 30     # 선물 수신 후 발신 전환 골든 타임 (Phase 4: 30일 내 58.4%)
PAY_IT_FORWARD_PCT  = 99.4   # Pay-it-forward 비율 (%)
RECIPROCAL_PCT      = 0.6    # Reciprocal 비율 (%)
SELF_GIFT_KFACTOR   = 2.090  # self-gift 유저의 K-factor
OTHERS_GIFT_KFACTOR = 1.515  # 타인 선물 유저의 K-factor
UNCONVERTED_PCT     = 63.2   # 장기 미전환자 비율 (%)

phase4_insights = [
    ("K-factor", f"{KFACTOR_CORRECTED} (바이럴 전환 유저 기준 수정값)",
     "GMV 시뮬레이션 K-factor 1.559 적용, 이전 3.948 대체"),
    ("Golden Time", f"{GOLDEN_TIME_DAYS}일 (수신 후 58.4%가 30일 내 발신 전환)",
     "리마인더 캠페인 타이밍: 수신 후 D+7 / D+14 / D+30 3단계 설계"),
    ("Pay-it-forward 99.4%", "답례 선물보다 새 수신자에게 전달하는 패턴 압도적",
     "CRM 카피: '답례하세요' → '당신도 누군가에게 선물해보세요'"),
]

for name, finding, implication in phase4_insights:
    print(f"\n  [Phase 4 인사이트] {name}")
    print(f"    발견: {finding}")
    print(f"    → Phase 5 전략 영향: {implication}")

print(f"\n  [추가] Self-gift K-factor {SELF_GIFT_KFACTOR} > Others K-factor {OTHERS_GIFT_KFACTOR}")
print(f"    → Self-gift 유저를 타인 선물로 전환하면 바이럴 루프 약화 위험")
print(f"    → 전략: self-gift 유저에게 '소중한 분께도 선물해보세요' 넛지 추가")
print(f"\n  [추가] 장기 미전환자 {UNCONVERTED_PCT}% → Pepero Day D-7 '첫 선물' 캠페인 대상")

# ─────────────────────────────────────────────────────────────
# 1. 데이터 로딩 및 전처리
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 1] 데이터 로딩 및 캠페인 퍼널 분석")
print("=" * 65)

campaigns     = pd.read_csv(f"{DATA_DIR}/campaigns.csv")  # 캠페인 마스터
campaign_logs = pd.read_csv(f"{DATA_DIR}/campaign_logs.csv",
                            parse_dates=["occurred_at"])  # 캠페인 이벤트 로그
orders        = pd.read_csv(f"{DATA_DIR}/orders.csv",
                            parse_dates=["created_at"])   # 주문 데이터
rfm           = pd.read_csv(f"{BASE}/analysis/rfm_result.csv")  # RFM 세그먼트 결과

# accepted / pending_accepted만 유효 주문으로 인정 (expired, refunded 제외)
orders_active = orders[orders["order_status"].isin(["accepted", "pending_accepted"])].copy()

print(f"캠페인 수:     {len(campaigns):,}개")
print(f"캠페인 로그:   {len(campaign_logs):,}건")
print(f"유효 주문:     {len(orders_active):,}건")
print(f"event_type:    {campaign_logs['event_type'].unique()}")
print(f"message_type:  {campaign_logs['message_type'].unique()}")
print(f"RFM 세그먼트:  {rfm['segment'].unique()}")

# 캠페인별 × event_type별 유저 수 집계
funnel = (
    campaign_logs
    .groupby(["campaign_id", "event_type"])["user_id"]
    .count()
    .reset_index()
    .rename(columns={"user_id": "cnt"})
)
funnel_pivot = (
    funnel
    .pivot_table(index="campaign_id", columns="event_type", values="cnt", fill_value=0)
    .reset_index()
)
funnel_pivot.columns.name = None  # MultiIndex 제거

# campaigns 마스터 + 퍼널 피벗 결합
camp_perf = campaigns.merge(funnel_pivot, on="campaign_id", how="left")

# send 컬럼이 없으면 target_user_count로 대체
if "send" not in camp_perf.columns:
    camp_perf["send"] = camp_perf["target_user_count"]

sent = "send"  # 분모 컬럼명

# 비율 지표 계산 (0으로 나누기 방지)
camp_perf["open_rate"]    = camp_perf.get("open",    0) / camp_perf[sent].replace(0, np.nan)
camp_perf["click_rate"]   = camp_perf.get("click",   0) / camp_perf[sent].replace(0, np.nan)
camp_perf["block_rate"]   = camp_perf.get("block",   0) / camp_perf[sent].replace(0, np.nan)
camp_perf["purchase_cvr"] = camp_perf.get("purchase",0) / camp_perf[sent].replace(0, np.nan)

print("\n--- 전체 캠페인 평균 퍼널 지표 ---")
for col, label in [("open_rate","Open Rate"),("click_rate","Click Rate"),
                   ("block_rate","Block Rate"),("purchase_cvr","Purchase CVR")]:
    print(f"  {label}: {camp_perf[col].mean()*100:.2f}%")

# 세그먼트별 집계
seg_perf = camp_perf.groupby("target_segment").agg(
    campaign_count  = ("campaign_id",  "count"),
    avg_open_rate   = ("open_rate",    "mean"),
    avg_click_rate  = ("click_rate",   "mean"),
    avg_block_rate  = ("block_rate",   "mean"),
    avg_purchase_cvr= ("purchase_cvr", "mean"),
).reset_index()

print("\n--- 세그먼트별 캠페인 성과 ---")
print(seg_perf.to_string(index=False))

# ─────────────────────────────────────────────────────────────
# 2. A/B 검정: 메시지 전략 비교 (curation vs ranking)
#    Power Analysis → Chi-square → Holm-Bonferroni 보정
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 2] A/B 검정: 메시지 전략 비교 (curation vs ranking)")
print("=" * 65)

# --- Power Analysis: 필요 샘플 수 먼저 계산 ---
# 기준: CTR 5% 대 6% (1%p 차이 탐지), alpha=0.05, power=0.80
alpha_level  = 0.05
power_target = 0.80
p1 = 0.05  # 기준 CTR (귀무 가설)
p2 = 0.06  # 탐지하려는 CTR (대립 가설, 1%p 차이)

# 두 비율 차이의 표준 오차 기반 샘플 수 공식
z_alpha = norm.ppf(1 - alpha_level / 2)   # 양측 z-critical (1.96)
z_beta  = norm.ppf(power_target)          # power z-critical (0.84)
p_bar   = (p1 + p2) / 2                   # 풀링 비율
n_required = int(np.ceil(
    (z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) +
     z_beta  * np.sqrt(p1 * (1-p1) + p2 * (1-p2))) ** 2
    / (p2 - p1) ** 2
))

# 실제 curation / ranking 샘플 수
n_curation = len(campaign_logs[campaign_logs["message_type"] == "curation"])
n_ranking  = len(campaign_logs[campaign_logs["message_type"] == "ranking"])
power_adequate = min(n_curation, n_ranking) >= n_required

print(f"\n[Power Analysis]")
print(f"  가정: 기준 CTR={p1*100:.0f}%, 탐지 목표={p2*100:.0f}%, alpha={alpha_level}, power={power_target}")
print(f"  필요 샘플 수 (그룹당): {n_required:,}명")
print(f"  실제 샘플 수 - curation: {n_curation:,}명 / ranking: {n_ranking:,}명")
print(f"  Power 충족 여부: {'충족 (검정 신뢰 가능)' if power_adequate else '미달 (결과 해석 주의)'}")

# --- Chi-square 검정: curation vs ranking ---
# 대상 메시지 타입: curation / ranking (seasonal·discount 제외)
ab_logs = campaign_logs[campaign_logs["message_type"].isin(["curation", "ranking"])].copy()

# 검정 대상 지표 × 컨틴전시 테이블 빌드
test_metrics = []
p_values     = []

for metric, pos_event, neg_events in [
    ("CTR (클릭률)",       "click",    ["open"]),           # 분모: open
    ("CVR (전환율)",       "purchase", ["click"]),           # 분모: click
    ("Block Rate (차단율)","block",    ["send"]),            # 분모: send
]:
    # 메시지 타입별 양성/음성 집계
    rows = {}
    for mt in ["curation", "ranking"]:
        sub = ab_logs[ab_logs["message_type"] == mt]
        pos = (sub["event_type"] == pos_event).sum()
        neg = sub["event_type"].isin(neg_events).sum()
        rows[mt] = [pos, neg]

    ct = np.array([rows["curation"], rows["ranking"]])  # 컨틴전시 테이블

    if ct.min() >= 5:  # Chi-square 최소 기대 빈도 조건 확인
        chi2, p, dof, _ = chi2_contingency(ct)
        ctr_cur = ct[0,0] / ct[0].sum() * 100 if ct[0].sum() > 0 else 0
        ctr_ran = ct[1,0] / ct[1].sum() * 100 if ct[1].sum() > 0 else 0
    else:
        chi2, p, ctr_cur, ctr_ran = np.nan, 1.0, 0.0, 0.0

    test_metrics.append({
        "지표":         metric,
        "curation":     ctr_cur,
        "ranking":      ctr_ran,
        "chi2":         chi2,
        "p_value_raw":  p,
    })
    p_values.append(p)

ab_df = pd.DataFrame(test_metrics)

# --- Holm-Bonferroni 다중 검정 보정 ---
# 3개 지표를 동시에 검정하므로 FWER(Family-Wise Error Rate) 제어 필요
rejected, corrected_p, _, _ = multipletests(p_values, method="holm")  # Holm 보정

ab_df["p_corrected"] = corrected_p  # Holm 보정 후 p값
ab_df["significant"] = rejected     # 보정 후 유의 여부 (True/False)

print(f"\n[Chi-square 검정 결과 + Holm-Bonferroni 보정]")
print(f"  (alpha = {alpha_level}, Holm 보정 적용)")
print()
for _, row in ab_df.iterrows():
    sig_mark = "*** 유의" if row["significant"] else "n.s."
    print(f"  {row['지표']}")
    print(f"    curation: {row['curation']:.2f}%  |  ranking: {row['ranking']:.2f}%")
    print(f"    chi2={row['chi2']:.3f}, p_raw={row['p_value_raw']:.4f}, "
          f"p_corrected={row['p_corrected']:.4f}  → {sig_mark}")

print(f"\n[A/B 검정 결론]")
sig_metrics = ab_df[ab_df["significant"]]["지표"].tolist()
if sig_metrics:
    print(f"  Holm 보정 후 유의미한 지표: {sig_metrics}")
else:
    print(f"  Holm 보정 후 유의미한 차이 없음 - 두 메시지 전략 성과 동등")

# ─────────────────────────────────────────────────────────────
# 3. Segment × Message 교차 분석
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 3] Segment × Message 교차 분석 (CVR 히트맵)")
print("=" * 65)

# campaign_logs + campaigns 결합 (target_segment, message_type 확보)
logs_with_seg = campaign_logs.merge(
    campaigns[["campaign_id","target_segment","message_type"]].rename(
        columns={"message_type":"camp_msg_type"}),
    on="campaign_id", how="left"
)

# purchase 이벤트 여부 플래그
logs_with_seg["is_purchase"] = (logs_with_seg["event_type"] == "purchase").astype(int)
logs_with_seg["is_send"]     = (logs_with_seg["event_type"] == "send").astype(int)

# 세그먼트 × 메시지타입별 send 수 / purchase 수 집계
seg_msg_send     = logs_with_seg[logs_with_seg["event_type"] == "send"].groupby(
    ["target_segment","camp_msg_type"])["user_id"].count().rename("send_cnt")
seg_msg_purchase = logs_with_seg[logs_with_seg["event_type"] == "purchase"].groupby(
    ["target_segment","camp_msg_type"])["user_id"].count().rename("purchase_cnt")

seg_msg_df = pd.concat([seg_msg_send, seg_msg_purchase], axis=1).fillna(0).reset_index()
seg_msg_df["cvr"] = seg_msg_df["purchase_cnt"] / seg_msg_df["send_cnt"].replace(0, np.nan)

# 히트맵용 피벗
seg_msg_pivot = seg_msg_df.pivot_table(
    index="target_segment", columns="camp_msg_type", values="cvr", aggfunc="mean"
)

print("\n--- Segment × Message CVR 매트릭스 (%) ---")
print((seg_msg_pivot * 100).round(2).to_string())

# ─────────────────────────────────────────────────────────────
# 4. 시즌 캠페인 vs 일반 캠페인 비교
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 4] 시즌 vs 일반 캠페인 비교")
print("=" * 65)

season_keywords = ["pepero","valentine","white_day","christmas",
                   "childrens","parents","teachers","year_end"]

def is_seasonal(name):
    if pd.isna(name):
        return False
    return any(kw in str(name).lower() for kw in season_keywords)

camp_perf["is_seasonal"] = camp_perf["campaign_name"].apply(is_seasonal)

# gift_occasion 컬럼 보조 판별
if "gift_occasion" in camp_perf.columns:
    camp_perf["is_seasonal"] = camp_perf["is_seasonal"] | (
        camp_perf["gift_occasion"].notna() &
        (camp_perf["gift_occasion"] != "general")
    )

seasonal_compare = camp_perf.groupby("is_seasonal").agg(
    count             = ("campaign_id",  "count"),
    avg_open_rate     = ("open_rate",    "mean"),
    avg_click_rate    = ("click_rate",   "mean"),
    avg_block_rate    = ("block_rate",   "mean"),
    avg_purchase_cvr  = ("purchase_cvr", "mean"),
).reset_index()
seasonal_compare["is_seasonal"] = seasonal_compare["is_seasonal"].map(
    {True: "시즌 캠페인", False: "일반 캠페인"})

print("\n--- 시즌 vs 일반 캠페인 성과 ---")
print(seasonal_compare.to_string(index=False))

# ─────────────────────────────────────────────────────────────
# 5. ROAS 시뮬레이션 (K-factor 1.559 기반 재계산)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 5] ROAS 시뮬레이션 (K-factor 1.559 기반 재계산)")
print("=" * 65)

COST_PER_SEND = 15  # 기준 비용: 카카오 친구톡 1건당 15원

rfm_summary = rfm.groupby("segment").agg(
    user_count   = ("sender_user_id", "count"),
    avg_monetary = ("monetary",       "mean"),
).reset_index()

# 세그먼트별 실제 CVR 매핑 (없으면 5% 기본값)
default_cvr = 0.05
if "target_segment" in camp_perf.columns and "purchase_cvr" in camp_perf.columns:
    seg_cvr_map = camp_perf.groupby("target_segment")["purchase_cvr"].mean().to_dict()
else:
    seg_cvr_map = {}

def get_cvr(seg):
    return seg_cvr_map.get(seg, default_cvr)  # 매핑 없으면 기본값

rfm_summary["expected_cvr"] = rfm_summary["segment"].apply(get_cvr)

# K-factor 바이럴 승수 적용 - 1명의 캠페인 반응이 K-factor배 추가 GMV를 유발
rfm_summary["campaign_cost"]     = rfm_summary["user_count"] * COST_PER_SEND
rfm_summary["direct_revenue"]    = (
    rfm_summary["user_count"] * rfm_summary["expected_cvr"] * rfm_summary["avg_monetary"]
)
rfm_summary["viral_multiplier"]  = KFACTOR_CORRECTED          # K-factor 1.559
rfm_summary["expected_revenue"]  = (
    rfm_summary["direct_revenue"] * rfm_summary["viral_multiplier"]  # 바이럴 승수 반영
)
rfm_summary["roas"] = rfm_summary["expected_revenue"] / rfm_summary["campaign_cost"]
rfm_summary = rfm_summary.sort_values("roas", ascending=False)

print(f"  K-factor 승수 적용: {KFACTOR_CORRECTED} (이전 3.948 → 수정값 1.559)")
print(f"  비용 가정: {COST_PER_SEND}원/건\n")
print(rfm_summary[["segment","user_count","avg_monetary","expected_cvr",
                    "campaign_cost","direct_revenue","expected_revenue","roas"
                    ]].to_string(index=False))

# --- 감도 분석: 비용 10/15/20원 시나리오 ---
print(f"\n[ROAS 감도분석] 비용 10 / 15 / 20원/건 시나리오")
sensitivity_rows = []
for cost in [10, 15, 20]:
    for _, row in rfm_summary.iterrows():
        roas_s = (row["avg_monetary"] * row["expected_cvr"] * KFACTOR_CORRECTED) / cost
        sensitivity_rows.append({"segment": row["segment"],
                                  "cost_per_send": cost, "roas": round(roas_s)})
sens_df    = pd.DataFrame(sensitivity_rows)
sens_pivot = sens_df.pivot_table(index="segment", columns="cost_per_send", values="roas")
sens_pivot.columns = [f"{c}원/건" for c in sens_pivot.columns]
print(sens_pivot.sort_values("15원/건", ascending=False).to_string())

# ─────────────────────────────────────────────────────────────
# 6. CRM 액션 플랜 (Phase 4 인사이트 연결)
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 6] CRM 액션 플랜 (Phase 4 인사이트 반영)")
print("=" * 65)

action_plans = {
    "Champions": {
        "액션":   "VIP 전용 얼리버드 쿠폰 + Pepero Day D-7 시즌 선착순 발송",
        "메시지": "'당신도 누군가에게 선물해보세요' (Pay-it-forward 카피, 답례 X)",
        "채널":   "카카오 친구톡 (고도 개인화 curation)",
        "타이밍": f"수신 후 D+{GOLDEN_TIME_DAYS}일 이내 리마인더 (Golden Time)",
        "기대효과":"최고가치 유저(avg M 499,416원) 유지 + K-factor 1.559 바이럴 증폭",
    },
    "At Risk": {
        "액션":   "관계 기반 선물 추천 + 수신 후 30일 리마인더 3단계 (D+7/D+14/D+30)",
        "메시지": "'오랫동안 소중한 분들을 챙겨오셨군요, 이제 다시 한번' (감성 넛지)",
        "채널":   "카카오 친구톡 (ranking 메시지로 상품 발견 유도)",
        "타이밍": f"골든타임 {GOLDEN_TIME_DAYS}일 기준 리마인더 설계",
        "기대효과":"고단가 유저(avg M 242,600원) 이탈 방지 - 연간 GMV 9.1억 위험",
    },
    "Need Attention": {
        "액션":   "시즌 맞춤 윈백 캠페인 + 할인 쿠폰 (알림톡 비용 절감)",
        "메시지": "'오랜만이에요! 이번 시즌 특별 할인권 드려요'",
        "채널":   "카카오 알림톡 (비용 효율 우선, 친구톡 대비 40% 절감)",
        "타이밍": "Pepero Day D-14 先발송 → D-7 리마인더",
        "기대효과":"GMV 2위 세그먼트(14.0억) 유지, ROI 최대화",
    },
    "Potential Loyalist": {
        "액션":   "Self-gift 유저 → 타인 선물 전환 캠페인 ('소중한 분께도')",
        "메시지": f"'셀프 선물 자주 하시는군요! 소중한 분께도 선물해보세요'",
        "채널":   "카카오 친구톡 (curation 개인화)",
        "타이밍": "생일 시즌 / Pepero Day D-14",
        "기대효과":f"Self-gift K-factor {SELF_GIFT_KFACTOR} → Others K-factor {OTHERS_GIFT_KFACTOR} 전환 시 GMV 상승",
    },
    "Promising": {
        "액션":   f"장기 미전환자 {UNCONVERTED_PCT}% 대상 Pepero Day D-7 '첫 선물' 캠페인",
        "메시지": "'아직 선물해본 적 없으시죠? 첫 선물 쿠폰 드려요'",
        "채널":   "카카오 친구톡 + 앱 푸시 병행",
        "타이밍": "Pepero Day D-7 (시즌 캠페인 피크 직전)",
        "기대효과":"63.2% 미전환자 첫 구매 유도 → LTV 사이클 진입",
    },
}

top3_roas = rfm_summary.head(3)
for _, row in top3_roas.iterrows():
    seg  = row["segment"]
    plan = action_plans.get(seg, {"액션": "표준 리텐션 캠페인", "채널": "카카오 친구톡"})
    print(f"\n[{seg}]  ROAS: {row['roas']:,.0f}x | 유저: {row['user_count']:,}명 "
          f"| 예상 수익: {row['expected_revenue']/1e6:,.1f}백만원")
    for k, v in plan.items():
        print(f"  {k}: {v}")

print(f"\n[전체 예상 수익] {rfm_summary['expected_revenue'].sum()/1e8:.2f}억원 "
      f"(K-factor {KFACTOR_CORRECTED} 바이럴 승수 포함)")

# ─────────────────────────────────────────────────────────────
# 7. 차트 저장
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Section 7] 차트 저장")
print("=" * 65)

KAKAO_YELLOW = "#FEE500"
KAKAO_BROWN  = "#3C1E1E"

# --- Chart 1: 캠페인 퍼널 ---
event_order = [c for c in ["send","open","click","purchase"] if c in camp_perf.columns]
if len(event_order) >= 2:
    funnel_totals = camp_perf[event_order].sum()
    fig, ax = plt.subplots(figsize=(10, 6))
    colors_f = ['#2E86AB','#A23B72','#F18F01','#C73E1D'][:len(event_order)]
    bars = ax.bar(event_order, funnel_totals.values, color=colors_f,
                  edgecolor='white', width=0.6)
    for bar, val in zip(bars, funnel_totals.values):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + funnel_totals.max()*0.01,
                f"{val:,.0f}", ha='center', va='bottom', fontsize=10, fontweight='bold')
    for i in range(1, len(event_order)):
        prev = funnel_totals.values[i-1]
        curr = funnel_totals.values[i]
        if prev > 0:
            rate = curr / prev * 100
            ax.annotate(f"→ {rate:.1f}%",
                        xy=(i - 0.5, max(prev,curr)*0.5),
                        ha='center', fontsize=9, color='#555')
    ax.set_ylabel("유저 수", fontsize=11)
    ax.set_title("전체 캠페인 퍼널 (누적)", fontsize=13, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/layer5_campaign_funnel.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  layer5_campaign_funnel.png 저장 완료")

# --- Chart 2: ROAS 시뮬레이션 ---
fig, ax = plt.subplots(figsize=(12, 6))
roas_sorted = rfm_summary.sort_values("roas", ascending=True)
colors_r = ['#FF4757' if r > 100 else '#FFA502' if r > 50 else '#2ED573'
            for r in roas_sorted["roas"]]
bars = ax.barh(roas_sorted["segment"], roas_sorted["roas"],
               color=colors_r, edgecolor='white')
ax.axvline(x=100, color='red', linestyle='--', linewidth=1.5, label='ROAS 100x 기준선')
for bar, val in zip(bars, roas_sorted["roas"]):
    ax.text(val + 3, bar.get_y() + bar.get_height()/2,
            f"{val:,.0f}x", va='center', fontsize=9)
ax.set_xlabel("ROAS (배수)", fontsize=11)
ax.set_title(f"세그먼트별 ROAS 시뮬레이션\n"
             f"(K-factor {KFACTOR_CORRECTED} 바이럴 승수 반영, 비용 {COST_PER_SEND}원/건)",
             fontsize=12, fontweight='bold')
ax.legend(fontsize=9)
ax.grid(axis='x', alpha=0.3)
ax.set_xlim(0, roas_sorted["roas"].max() * 1.25)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_roas_simulation.png", dpi=150, bbox_inches='tight')
plt.close()
print("  layer5_roas_simulation.png 저장 완료")

# --- Chart 3: 시즌 vs 일반 캠페인 ---
metric_cols = [c for c in ["avg_open_rate","avg_click_rate","avg_purchase_cvr"]
               if c in seasonal_compare.columns]
if metric_cols:
    fig, axes = plt.subplots(1, len(metric_cols), figsize=(5*len(metric_cols), 5))
    if len(metric_cols) == 1:
        axes = [axes]
    for ax, mc in zip(axes, metric_cols):
        ax.bar(seasonal_compare["is_seasonal"], seasonal_compare[mc]*100,
               color=[KAKAO_YELLOW, '#FF6B00'], edgecolor='#333', width=0.5)
        ax.set_title(mc.replace("avg_","").replace("_"," ").title(), fontsize=11)
        ax.set_ylabel("%")
        ax.grid(axis='y', alpha=0.3)
        for i, val in enumerate(seasonal_compare[mc]):
            ax.text(i, val*100 + 0.05, f"{val*100:.1f}%", ha='center', fontsize=10)
    plt.suptitle("시즌 vs 일반 캠페인 성과 비교", fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/layer5_seasonal_vs_normal.png", dpi=150, bbox_inches='tight')
    plt.close()
    print("  layer5_seasonal_vs_normal.png 저장 완료")

# --- Chart 4: 비용 vs 예상 수익 버블 ---
fig, ax = plt.subplots(figsize=(12, 7))
cmap = plt.cm.Set1(np.linspace(0, 1, len(rfm_summary)))
for i, (_, row) in enumerate(rfm_summary.iterrows()):
    ax.scatter(row["campaign_cost"]/1e6, row["expected_revenue"]/1e6,
               s=row["user_count"]/50, color=cmap[i], alpha=0.7,
               edgecolors='white', linewidth=1.5, label=row["segment"])
    ax.annotate(row["segment"],
                xy=(row["campaign_cost"]/1e6, row["expected_revenue"]/1e6),
                xytext=(5, 5), textcoords='offset points', fontsize=8)
max_cost = rfm_summary["campaign_cost"].max() / 1e6
ax.plot([0, max_cost], [0, max_cost], 'k--', alpha=0.4, linewidth=1, label='손익분기(ROAS=1)')
ax.set_xlabel("캠페인 비용 (백만원)", fontsize=11)
ax.set_ylabel("예상 수익 (백만원)", fontsize=11)
ax.set_title(f"세그먼트별 비용 vs 예상 수익\n(K-factor {KFACTOR_CORRECTED} 반영, 점 크기=유저 수)",
             fontsize=12, fontweight='bold')
ax.legend(fontsize=8, loc='upper left')
ax.grid(alpha=0.2)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_cost_vs_revenue.png", dpi=150, bbox_inches='tight')
plt.close()
print("  layer5_cost_vs_revenue.png 저장 완료")

# --- Chart 5: ROAS 감도분석 ---
fig, ax = plt.subplots(figsize=(13, 6))
segments_s = sens_pivot.sort_values("15원/건", ascending=False).index.tolist()
x = np.arange(len(segments_s))
w = 0.25
for i, (cost, col, lbl) in enumerate(zip(
        [10, 15, 20],
        ["#2ED573", "#FEE500", "#FF4757"],
        ["10원/건 (최저)","15원/건 (기본)","20원/건 (최고)"])):
    vals = [sens_pivot.loc[s, f"{cost}원/건"] if s in sens_pivot.index else 0
            for s in segments_s]
    ax.bar(x + (i-1)*w, vals, width=w, color=col, edgecolor='#333', label=lbl, alpha=0.85)
ax.axhline(y=100, color='gray', linestyle='--', linewidth=1, label='ROAS 100x 기준선')
ax.set_xticks(x)
ax.set_xticklabels(segments_s, rotation=20, ha='right', fontsize=9)
ax.set_ylabel("ROAS (배수)", fontsize=11)
ax.set_title(f"ROAS 감도분석 - 비용 10/15/20원/건 시나리오\n"
             f"(K-factor {KFACTOR_CORRECTED} 바이럴 승수 포함)",
             fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_roas_sensitivity.png", dpi=150, bbox_inches='tight')
plt.close()
print("  layer5_roas_sensitivity.png 저장 완료")

# --- Chart 6: A/B 검정 결과 (신규) ---
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
ab_plot_metrics = ["CTR (클릭률)", "CVR (전환율)", "Block Rate (차단율)"]
pair_labels = ["curation", "ranking"]

for ax, metric_name in zip(axes, ab_plot_metrics):
    row = ab_df[ab_df["지표"] == metric_name]
    if row.empty:
        ax.set_visible(False)
        continue
    row = row.iloc[0]
    values  = [row["curation"], row["ranking"]]
    colors  = ["#2E86AB", "#A23B72"]
    bars    = ax.bar(pair_labels, values, color=colors, edgecolor='white', width=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + max(values)*0.01,
                f"{val:.2f}%", ha='center', fontsize=11, fontweight='bold')
    sig_text = (f"p_corrected={row['p_corrected']:.4f}\n"
                f"{'*** 유의미한 차이' if row['significant'] else 'n.s. 유의하지 않음'}")
    ax.text(0.5, 0.92, sig_text, transform=ax.transAxes,
            ha='center', va='top', fontsize=9,
            color='#C73E1D' if row['significant'] else '#555',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#f9f9f9', alpha=0.8))
    ax.set_title(metric_name, fontsize=11, fontweight='bold')
    ax.set_ylabel("%")
    ax.grid(axis='y', alpha=0.3)

plt.suptitle(f"A/B 검정: curation vs ranking 메시지 전략\n"
             f"(Holm-Bonferroni 보정 적용, n_curation={n_curation:,} / n_ranking={n_ranking:,})",
             fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer5_ab_test_result.png", dpi=150, bbox_inches='tight')
plt.close()
print("  layer5_ab_test_result.png 저장 완료 (신규)")

# --- Chart 7: Segment × Message CVR 히트맵 (신규) ---
if not seg_msg_pivot.empty:
    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(
        seg_msg_pivot * 100,  # % 단위
        annot=True, fmt=".2f", cmap="YlOrRd",
        linewidths=0.5, linecolor='white',
        ax=ax, cbar_kws={"label": "CVR (%)"}
    )
    ax.set_title("세그먼트 × 메시지 타입별 CVR 매트릭스\n"
                 "(어떤 세그먼트에 어떤 메시지가 효과적인가)",
                 fontsize=12, fontweight='bold')
    ax.set_xlabel("메시지 타입", fontsize=11)
    ax.set_ylabel("타겟 세그먼트", fontsize=11)
    plt.tight_layout()
    plt.savefig(f"{CHART_DIR}/layer5_segment_message_matrix.png",
                dpi=150, bbox_inches='tight')
    plt.close()
    print("  layer5_segment_message_matrix.png 저장 완료 (신규)")

# ─────────────────────────────────────────────────────────────
# 최종 요약
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[Layer 5 v2 완료] 최종 요약")
print("=" * 65)
print(f"  최고 ROAS 세그먼트: {rfm_summary.iloc[0]['segment']} ({rfm_summary.iloc[0]['roas']:,.0f}x)")
print(f"  전체 예상 수익 합계: {rfm_summary['expected_revenue'].sum()/1e8:.2f}억원 (K={KFACTOR_CORRECTED})")
print(f"  A/B 검정 유의 지표: {sig_metrics if sig_metrics else '없음 (두 전략 동등)'}")
print(f"  Power 충족: {power_adequate} (필요={n_required:,}명, 실제={min(n_curation,n_ranking):,}명)")
print(f"  Golden Time 적용: 수신 후 {GOLDEN_TIME_DAYS}일 내 리마인더 캠페인 설계")
print(f"  저장 차트: 7개 (layer5_*.png)")
