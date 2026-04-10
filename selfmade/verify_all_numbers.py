# -*- coding: utf-8 -*-
"""
PPT 수치 전체 검증 스크립트
각 Phase 노트북 로직 그대로 재현하여 실측값 산출
"""
import sys, warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.tsa.seasonal import STL
from statsmodels.stats.multitest import multipletests

W = sys.stdout.buffer.write
BASE = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift\selfmade"

# ── 데이터 로딩 ──────────────────────────────────────────
orders   = pd.read_csv(f"{BASE}/orders.csv", parse_dates=["created_at"])
users    = pd.read_csv(f"{BASE}/users.csv")
receipts = pd.read_csv(f"{BASE}/gift_receipts.csv")
campaigns= pd.read_csv(f"{BASE}/campaigns.csv")
logs     = pd.read_csv(f"{BASE}/campaign_logs.csv")
rfm      = pd.read_csv(r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift\analysis\rfm_result.csv")

orders_active = orders[orders["order_status"] != "cancelled"].copy()
orders_active["year"] = orders_active["created_at"].dt.year

# ════════════════════════════════════════════════════════
W(b"=" * 60 + b"\n")
W("PHASE 1 — EDA & GMV\n".encode("utf-8"))
W(b"=" * 60 + b"\n")

gmv_2023 = orders_active[orders_active["year"]==2023]["total_amount_krw"].sum()
gmv_2024 = orders_active[orders_active["year"]==2024]["total_amount_krw"].sum()
cnt_2023 = len(orders_active[orders_active["year"]==2023])
cnt_2024 = len(orders_active[orders_active["year"]==2024])
yoy = (gmv_2024 - gmv_2023) / gmv_2023 * 100

W(f"2023 GMV: ₩{gmv_2023/1e8:.1f}억  주문: {cnt_2023:,}건\n".encode("utf-8"))
W(f"2024 GMV: ₩{gmv_2024/1e8:.1f}억  주문: {cnt_2024:,}건\n".encode("utf-8"))
W(f"YoY: +{yoy:.1f}%\n".encode("utf-8"))
W(f"전체 유저 수(users.csv): {len(users):,}명\n".encode("utf-8"))
W(f"전체 주문 건수(active): {len(orders_active):,}건\n".encode("utf-8"))

# 수신→발신 전환율 (Page 1, 8)
receivers = set(receipts["receiver_user_id"].unique())
senders   = set(orders_active["sender_user_id"].unique())
viral_users = receivers & senders
conv_rate = len(viral_users) / len(receivers) * 100
W(f"\n수신자: {len(receivers):,}명  발신자가 된 수신자: {len(viral_users):,}명\n".encode("utf-8"))
W(f"수신→발신 전환율: {conv_rate:.1f}%\n".encode("utf-8"))

# 선물 수락률
total_receipts = len(receipts)
accepted = receipts[receipts["receipt_status"] == "accepted"] if "receipt_status" in receipts.columns else receipts
accept_rate = len(accepted) / total_receipts * 100 if total_receipts > 0 else 0
W(f"선물 수락률: {accept_rate:.1f}%  (총 수신: {total_receipts:,}건, 수락: {len(accepted):,}건)\n".encode("utf-8"))

# 시즌 이벤트 수치 (Page 6)
W("\n--- 시즌 이벤트 수치 ---\n".encode("utf-8"))
o24 = orders_active[orders_active["year"]==2024]
for occasion in ["설날", "빼빼로데이"]:
    if "gift_occasion" in o24.columns:
        mask = o24["gift_occasion"].str.contains(occasion, na=False)
        sub = o24[mask]
        if len(sub) > 0:
            W(f"{occasion}: {len(sub):,}건, GMV ₩{sub['total_amount_krw'].sum()/1e8:.2f}억, AOV ₩{sub['total_amount_krw'].mean():,.0f}\n".encode("utf-8"))

# 카테고리 수치 (Page 7)
W("\n--- 카테고리 수치 (2024) ---\n".encode("utf-8"))
if "category" in o24.columns:
    cat_gmv = o24.groupby("category").agg(gmv=("total_amount_krw","sum"), cnt=("order_id","count"), aov=("total_amount_krw","mean"))
    for cat, row in cat_gmv.sort_values("gmv", ascending=False).head(6).iterrows():
        W(f"  {cat}: GMV ₩{row.gmv/1e8:.1f}억, 주문 {row.cnt:,}건, AOV ₩{row.aov:,.0f}\n".encode("utf-8"))

# ════════════════════════════════════════════════════════
W(b"\n" + b"=" * 60 + b"\n")
W("PHASE 2 — RFM 세그먼트\n".encode("utf-8"))
W(b"=" * 60 + b"\n")

total_rfm = len(rfm)
seg_counts = rfm["segment"].value_counts()
total_gmv_all = orders_active["total_amount_krw"].sum()

# RFM 유저 GMV 기여
rfm_orders = orders_active.merge(rfm[["sender_user_id","segment"]], on="sender_user_id", how="left")
seg_gmv = rfm_orders.groupby("segment")["total_amount_krw"].sum()

W(f"RFM 분석 대상 유저: {total_rfm:,}명\n".encode("utf-8"))
W(f"전체 GMV(active): ₩{total_gmv_all/1e8:.1f}억\n\n".encode("utf-8"))

W("세그먼트        유저수    비율   GMV기여%   monetary(평균)\n".encode("utf-8"))
for seg, cnt in seg_counts.items():
    gmv_pct = seg_gmv.get(seg, 0) / total_gmv_all * 100
    avg_mon = rfm[rfm["segment"]==seg]["monetary"].mean()
    W(f"  {seg:<22} {cnt:>5,}명  {cnt/total_rfm*100:>5.1f}%  {gmv_pct:>6.1f}%  ₩{avg_mon:>10,.0f}\n".encode("utf-8"))

# 상위 3개 세그먼트
top3 = ["Champions", "Can't Lose Them", "Loyal Customers"]
top3_cnt = rfm[rfm["segment"].isin(top3)]["sender_user_id"].nunique()
top3_gmv = rfm_orders[rfm_orders["segment"].isin(top3)]["total_amount_krw"].sum()
W(f"\n상위 3개(Champions+Can't Lose+Loyal) 유저: {top3_cnt:,}명 ({top3_cnt/total_rfm*100:.1f}%)\n".encode("utf-8"))
W(f"상위 3개 GMV: ₩{top3_gmv/1e8:.1f}억 ({top3_gmv/total_gmv_all*100:.1f}%)\n".encode("utf-8"))

# Champions + Can't Lose만
top2 = ["Champions", "Can't Lose Them"]
top2_cnt = rfm[rfm["segment"].isin(top2)]["sender_user_id"].nunique()
top2_gmv = rfm_orders[rfm_orders["segment"].isin(top2)]["total_amount_krw"].sum()
W(f"Champions + Can't Lose Them 유저: {top2_cnt:,}명 ({top2_cnt/total_rfm*100:.1f}%)\n".encode("utf-8"))
W(f"Champions + Can't Lose Them GMV: {top2_gmv/total_gmv_all*100:.1f}%\n".encode("utf-8"))

# ════════════════════════════════════════════════════════
W(b"\n" + b"=" * 60 + b"\n")
W("PHASE 3 — LTV 코호트\n".encode("utf-8"))
W(b"=" * 60 + b"\n")

# 코호트 = 첫 구매 월 기준
first_purchase = orders_active.groupby("sender_user_id")["created_at"].min().reset_index()
first_purchase.columns = ["sender_user_id","cohort_date"]
first_purchase["cohort_month"] = first_purchase["cohort_date"].dt.to_period("M")

orders_coh = orders_active.merge(first_purchase, on="sender_user_id")
orders_coh["order_month"] = orders_coh["created_at"].dt.to_period("M")
orders_coh["months_since"] = (orders_coh["order_month"] - orders_coh["cohort_month"]).apply(lambda x: x.n)

# M+0 ~ M+11 누적 LTV
ltv_data = orders_coh[orders_coh["months_since"].between(0,11)]
cohort_ltv = ltv_data.groupby(["cohort_month","sender_user_id"])["total_amount_krw"].sum().reset_index()
avg_ltv_m11 = cohort_ltv["total_amount_krw"].mean()

# M+0 만
m0_ltv = orders_coh[orders_coh["months_since"]==0].groupby("sender_user_id")["total_amount_krw"].sum().mean()

W(f"M+0 평균 LTV: ₩{m0_ltv:,.0f}\n".encode("utf-8"))
W(f"M+11 누적 평균 LTV: ₩{avg_ltv_m11:,.0f}\n".encode("utf-8"))
W(f"M+0 대비 성장: {avg_ltv_m11/m0_ltv:.1f}배\n".encode("utf-8"))

# LTV:CAC 기준 최대 CAC
margin_rate = 0.20
profit_ltv = avg_ltv_m11 * margin_rate
max_cac = profit_ltv / 3
W(f"이익 LTV(수수료 20%): ₩{profit_ltv:,.0f}\n".encode("utf-8"))
W(f"권장 최대 CAC(LTV:CAC=3:1): ₩{max_cac:,.0f}\n".encode("utf-8"))

# ════════════════════════════════════════════════════════
W(b"\n" + b"=" * 60 + b"\n")
W("PHASE 4 — 바이럴 루프\n".encode("utf-8"))
W(b"=" * 60 + b"\n")

# K-factor 계산 방식 확인
# 노트북 방식: avg_invites(발신자 1명당 평균 수신자) * conversion_rate(수신→발신)
sender_recv_cnt = orders_active.groupby("sender_user_id").size()
avg_invites_all = sender_recv_cnt.mean()

# 바이럴 전환: 수신 경험 후 발신자가 된 유저
viral_conv_rate = len(viral_users) / len(receivers)
kfactor_all = avg_invites_all * viral_conv_rate

W(f"발신자 1인당 평균 수신자: {avg_invites_all:.3f}명\n".encode("utf-8"))
W(f"수신→발신 전환율: {viral_conv_rate*100:.1f}%\n".encode("utf-8"))
W(f"K-factor(전체): {kfactor_all:.3f}\n".encode("utf-8"))

# 자기선물 vs 타인선물
if "is_self_gift" in orders_active.columns:
    self_gift = orders_active[orders_active["is_self_gift"]==True]
    other_gift = orders_active[orders_active["is_self_gift"]==False]
    W(f"자기선물 발신자: {self_gift['sender_user_id'].nunique():,}명\n".encode("utf-8"))
    W(f"타인선물 발신자: {other_gift['sender_user_id'].nunique():,}명\n".encode("utf-8"))
    self_avg = self_gift.groupby("sender_user_id").size().mean()
    other_avg = other_gift.groupby("sender_user_id").size().mean()
    W(f"자기선물 1인당 평균 발송수: {self_avg:.3f}\n".encode("utf-8"))
    W(f"타인선물 1인당 평균 발송수: {other_avg:.3f}\n".encode("utf-8"))
else:
    W("is_self_gift 컬럼 없음 - receiver_user_id == sender_user_id 로 판별\n".encode("utf-8"))
    self_gift_mask = orders_active.merge(
        receipts[["order_id","receiver_user_id"]], on="order_id", how="left"
    )
    self_mask = self_gift_mask["receiver_user_id"] == self_gift_mask["sender_user_id"]
    W(f"자기선물 주문: {self_mask.sum():,}건\n".encode("utf-8"))

# 바이럴 전환 유저 수 (PPT: 22,034명, 44.1%)
viral_pct_of_total = len(viral_users) / len(users) * 100
W(f"\n바이럴 전환 유저: {len(viral_users):,}명 (전체 유저 {len(users):,}명 대비 {viral_pct_of_total:.1f}%)\n".encode("utf-8"))
W(f"수신 경험 유저: {len(receivers):,}명 (전체 대비 {len(receivers)/len(users)*100:.1f}%)\n".encode("utf-8"))

# 발신 횟수별 세그먼트 (Page 8)
W("\n--- 발신 횟수별 유저 분포 ---\n".encode("utf-8"))
freq = orders_active.groupby("sender_user_id").size().reset_index(name="freq")
grp_loyal  = freq[(freq["freq"]>=4) & (freq["freq"]<=7)]
grp_normal = freq[(freq["freq"]>=2) & (freq["freq"]<=3)]
grp_heavy  = freq[freq["freq"]>=8]
W(f"충성형(4-7회): {len(grp_loyal):,}명 ({len(grp_loyal)/len(freq)*100:.1f}%)\n".encode("utf-8"))
W(f"일반형(2-3회): {len(grp_normal):,}명 ({len(grp_normal)/len(freq)*100:.1f}%)\n".encode("utf-8"))
W(f"헤비(8회+):    {len(grp_heavy):,}명 ({len(grp_heavy)/len(freq)*100:.1f}%)\n".encode("utf-8"))

# GMV 기여 (충성형)
loyal_users_set = set(grp_loyal["sender_user_id"])
loyal_gmv = orders_active[orders_active["sender_user_id"].isin(loyal_users_set)]["total_amount_krw"].sum()
W(f"충성형 GMV 기여: {loyal_gmv/total_gmv_all*100:.1f}%\n".encode("utf-8"))

# ════════════════════════════════════════════════════════
W(b"\n" + b"=" * 60 + b"\n")
W("PHASE 5 — CRM 전략\n".encode("utf-8"))
W(b"=" * 60 + b"\n")

# 퍼널
funnel = logs["event_type"].value_counts()
send = funnel.get("send", 0)
open_ = funnel.get("open", 0)
click = funnel.get("click", 0)
purchase = funnel.get("purchase", 0)
block = funnel.get("block", 0)
W(f"총 캠페인 발송: {send:,}건\n".encode("utf-8"))
W(f"오픈: {open_:,}건 ({open_/send*100:.2f}%)\n".encode("utf-8"))
W(f"클릭: {click:,}건 ({click/send*100:.2f}% 발송기준 / {click/open_*100:.2f}% 오픈기준)\n".encode("utf-8"))
W(f"구매: {purchase:,}건 ({purchase/send*100:.2f}%)\n".encode("utf-8"))
W(f"차단: {block:,}건 ({block/send*100:.2f}%)\n".encode("utf-8"))
W(f"클릭→구매: {purchase/click*100:.1f}%\n".encode("utf-8"))

# A/B 테스트
W("\n--- A/B 테스트: Ranking vs Curation ---\n".encode("utf-8"))
logs_m = logs.merge(campaigns[["campaign_id","message_type"]], on="campaign_id", how="left", suffixes=("","_camp"))
mt_col = "message_type_camp" if "message_type_camp" in logs_m.columns else "message_type"
ab = logs_m[logs_m[mt_col].isin(["ranking","curation"])]
pivot = ab.groupby([mt_col,"event_type"]).size().unstack(fill_value=0)

for mt in ["ranking","curation"]:
    if mt not in pivot.index:
        continue
    row = pivot.loc[mt]
    s = row.get("send", 0)
    o = row.get("open", 0)
    c = row.get("click", 0)
    p = row.get("purchase", 0)
    bl = row.get("block", 0)
    W(f"\n[{mt.upper()}] 발송 {s:,}건\n".encode("utf-8"))
    W(f"  오픈율:          {o/s*100:.2f}%\n".encode("utf-8"))
    W(f"  CTR(발송기준):   {c/s*100:.2f}%\n".encode("utf-8"))
    W(f"  CTR(오픈기준):   {c/o*100:.2f}%\n".encode("utf-8"))
    W(f"  CVR(발송기준):   {p/s*100:.2f}%\n".encode("utf-8"))
    W(f"  CVR(클릭기준):   {p/c*100:.2f}%\n".encode("utf-8"))
    W(f"  Block Rate:      {bl/s*100:.2f}%\n".encode("utf-8"))

# 캠페인 수
ranking_camps = campaigns[campaigns["message_type"]=="ranking"]
curation_camps = campaigns[campaigns["message_type"]=="curation"]
W(f"\n캠페인 수 - ranking: {len(ranking_camps)}개, curation: {len(curation_camps)}개, 전체: {len(campaigns)}개\n".encode("utf-8"))

# ROAS
W("\n--- ROAS 시뮬레이션 ---\n".encode("utf-8"))
base_cvr = purchase / send  # 실측 발송기준 CVR
W(f"실측 base_cvr(발송기준): {base_cvr*100:.4f}%\n".encode("utf-8"))

cvr_mult = {
    "Champions": 1.9, "Can't Lose Them": 1.6, "Loyal Customers": 1.5,
    "Potential Loyalists": 1.2, "New Customers": 1.0,
    "Casual": 0.9, "At Risk": 0.7, "Dormant": 0.5,
}
rfm_orders2 = orders_active.merge(rfm[["sender_user_id","segment"]], on="sender_user_id", how="left")
seg_aov = rfm_orders2.groupby("segment")["total_amount_krw"].mean()
overall_aov = orders_active["total_amount_krw"].mean()
rfm_sum = rfm.groupby("segment").agg(user_count=("sender_user_id","count")).reset_index()
rfm_sum["aov"]  = rfm_sum["segment"].apply(lambda s: seg_aov.get(s, overall_aov))
rfm_sum["cvr"]  = rfm_sum["segment"].apply(lambda s: base_cvr * cvr_mult.get(s, 1.0))
kf = 1.559
for cost in [10, 15, 20]:
    rfm_sum[f"roas_{cost}"] = (rfm_sum["user_count"] * rfm_sum["cvr"] * rfm_sum["aov"] * kf) / (rfm_sum["user_count"] * cost)

W(rfm_sum[["segment","user_count","aov","cvr","roas_10","roas_15","roas_20"]].sort_values("roas_15", ascending=False).to_string(index=False).encode("utf-8") + b"\n\n")
for cost in [10,15,20]:
    tot_cost = (rfm_sum["user_count"] * cost).sum()
    tot_rev  = (rfm_sum["user_count"] * rfm_sum["cvr"] * rfm_sum["aov"] * kf).sum()
    W(f"전체 ROAS({cost}원/건): {tot_rev/tot_cost:.1f}x\n".encode("utf-8"))
