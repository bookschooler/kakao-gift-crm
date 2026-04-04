"""
Layer 4: Viral Loop 분석
=========================
목적: 카카오 선물하기의 바이럴 루프 메커니즘 — 선물 수신 → 구매 전환, 상호성(reciprocity),
      K-factor를 분석하여 유기적 성장 동력을 정량화한다.

핵심 인사이트:
  - 수신 횟수별 구매 전환율 (4회 수신 시 30%+ 가설 검증)
  - reciprocity_index: 선물 받은 후 재발신 비율
  - referral_generation별 유저/GMV
  - K-factor: 바이럴 계수
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
print("[Layer 4] Viral Loop 분석 시작")
print("=" * 60)

# ─────────────────────────────────────────
# 1. 데이터 로딩
# ─────────────────────────────────────────
orders = pd.read_csv(f"{BASE}/orders.csv", parse_dates=["created_at"])
users  = pd.read_csv(f"{BASE}/users.csv")
gift_receipts = pd.read_csv(f"{BASE}/gift_receipts.csv", parse_dates=["accepted_at", "expires_at"])

orders_active = orders[orders["order_status"] != "cancelled"].copy()

print(f"유효 주문: {len(orders_active):,}건")
print(f"gift_receipts: {len(gift_receipts):,}건")
print(f"users: {len(users):,}명")

# ─────────────────────────────────────────
# 2. 수신 횟수별 구매 전환율
# ─────────────────────────────────────────
# 각 수신자(receiver_user_id)의 수신 횟수 집계
# gift_receipts에 order_id가 있으므로 orders와 join하여 sent_at 추출
receipts_with_date = gift_receipts.merge(
    orders_active[["order_id", "created_at", "sender_user_id"]],
    on="order_id",
    how="left"
)
receipts_with_date = receipts_with_date.rename(columns={"created_at": "sent_at"})

# 수신자별 총 수신 횟수 집계
recv_count = (
    receipts_with_date.groupby("receiver_user_id")["receipt_id"]
    .count()
    .reset_index()
    .rename(columns={"receipt_id": "recv_count"})
)

# 수신자가 나중에 발신자로 전환했는지 확인
# "구매 전환" = receiver_user_id가 orders_active의 sender_user_id에 존재
purchaser_set = set(orders_active["sender_user_id"].unique())
recv_count["converted"] = recv_count["receiver_user_id"].isin(purchaser_set)

print(f"\n총 수신자: {len(recv_count):,}명")
print(f"구매 전환자: {recv_count['converted'].sum():,}명")

# 수신 횟수 그룹핑 (1, 2, 3, 4, 5+)
def group_recv(n):
    if n >= 5:
        return "5회+"
    return f"{n}회"

recv_count["recv_group"] = recv_count["recv_count"].apply(group_recv)

# 그룹별 전환율
group_order = ["1회", "2회", "3회", "4회", "5회+"]
conv_by_group = (
    recv_count.groupby("recv_group")["converted"]
    .agg(["sum", "count", "mean"])
    .reset_index()
    .rename(columns={"sum": "converted_users", "count": "total_users", "mean": "cvr"})
)
conv_by_group["cvr_pct"] = conv_by_group["cvr"] * 100
conv_by_group["recv_group"] = pd.Categorical(conv_by_group["recv_group"], categories=group_order, ordered=True)
conv_by_group = conv_by_group.sort_values("recv_group")

print("\n--- 수신 횟수별 구매 전환율 ---")
print(conv_by_group[["recv_group", "total_users", "converted_users", "cvr_pct"]].to_string(index=False))

# 가설 검증: 4회 수신 시 30%+ 전환
row_4 = conv_by_group[conv_by_group["recv_group"] == "4회"]
if len(row_4) > 0:
    cvr_4 = row_4["cvr_pct"].values[0]
    hypothesis = "검증됨" if cvr_4 >= 30 else "기각됨"
    print(f"\n[가설 검증] 4회 수신 시 30%+ 전환 → {hypothesis} (실제: {cvr_4:.1f}%)")
else:
    print("\n4회 수신 그룹 데이터 없음")

# ─────────────────────────────────────────
# 3. Reciprocity Index
# ─────────────────────────────────────────
# 선물 받은 후 30/60/90일 내에 발신(구매)한 비율
# receipts_with_date에서 수신 이벤트, orders_active에서 발신 이벤트

# 수신자의 수신 날짜 목록
recv_events = receipts_with_date[
    receipts_with_date["receiver_user_id"].notna() &
    receipts_with_date["sent_at"].notna()
][["receiver_user_id", "sent_at"]].copy()
recv_events = recv_events.rename(columns={"receiver_user_id": "user_id"})

# 각 유저의 첫 수신 날짜
first_recv = recv_events.groupby("user_id")["sent_at"].min().reset_index().rename(columns={"sent_at": "first_recv_date"})

# 각 유저의 첫 발신 날짜 (수신 이후)
first_send = orders_active.groupby("sender_user_id")["created_at"].min().reset_index()
first_send = first_send.rename(columns={"sender_user_id": "user_id", "created_at": "first_send_date"})

# 수신 후 발신 분석
reciprocity_df = first_recv.merge(first_send, on="user_id", how="left")
reciprocity_df["days_to_send"] = (reciprocity_df["first_send_date"] - reciprocity_df["first_recv_date"]).dt.days

total_receivers = len(reciprocity_df)
recip_30  = (reciprocity_df["days_to_send"] <= 30).sum()
recip_60  = (reciprocity_df["days_to_send"] <= 60).sum()
recip_90  = (reciprocity_df["days_to_send"] <= 90).sum()
never_sent = reciprocity_df["first_send_date"].isna().sum()

print(f"\n--- Reciprocity Index ---")
print(f"  총 수신 경험 유저: {total_receivers:,}명")
print(f"  30일 내 재발신: {recip_30:,}명 ({recip_30/total_receivers*100:.1f}%)")
print(f"  60일 내 재발신: {recip_60:,}명 ({recip_60/total_receivers*100:.1f}%)")
print(f"  90일 내 재발신: {recip_90:,}명 ({recip_90/total_receivers*100:.1f}%)")
print(f"  미전환(발신 없음): {never_sent:,}명 ({never_sent/total_receivers*100:.1f}%)")

# ─────────────────────────────────────────
# 4. Referral Generation 분포
# ─────────────────────────────────────────
gen_dist = users["referral_generation"].value_counts().sort_index()
gen_gmv = (
    orders_active.merge(users[["user_id", "referral_generation"]], left_on="sender_user_id", right_on="user_id", how="left")
    .groupby("referral_generation")["total_amount_krw"]
    .sum()
    .reset_index()
    .rename(columns={"total_amount_krw": "gmv"})
)
gen_gmv["gmv_bn"] = gen_gmv["gmv"] / 1e8

print(f"\n--- Referral Generation 분포 ---")
print(gen_dist)
print(f"\n--- Generation별 GMV ---")
print(gen_gmv.to_string(index=False))

# ─────────────────────────────────────────
# 5. K-factor 계산
# ─────────────────────────────────────────
# K-factor = 평균 초대수(발신 건수) × 전환율
# 평균 초대수: 각 발신자가 보낸 선물 수 (unique receiver 기준)

# 발신자별 고유 수신자 수
# receipts_with_date에는 sender_user_id가 이미 포함됨 (orders와 join 완료)
avg_invites = receipts_with_date.groupby("sender_user_id")["receiver_user_id"].nunique().mean()

# 전환율: gift_received 채널 유저 / 총 수신자 수
# (실제 바이럴 전환 = gift_received 채널 신규 유저)
gift_received_users = (users["acquisition_channel"] == "gift_received").sum()
total_recv_unique = recv_count["receiver_user_id"].nunique()
overall_cvr = recv_count["converted"].mean()

k_factor = avg_invites * overall_cvr

print(f"\n--- K-factor 계산 ---")
print(f"  평균 초대수 (발신자당 고유 수신자): {avg_invites:.2f}명")
print(f"  전체 수신자 전환율: {overall_cvr*100:.1f}%")
print(f"  K-factor: {k_factor:.3f}")
print(f"  → K-factor {'> 1 (바이럴 성장)' if k_factor > 1 else '< 1 (선형 성장)'}")

# ─────────────────────────────────────────
# 6. 차트 저장
# ─────────────────────────────────────────

# Chart 1: 수신 횟수별 전환율
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(conv_by_group))
bars = ax.bar(x, conv_by_group["cvr_pct"],
              color=["#FEE500" if pct < 30 else "#FF4757" for pct in conv_by_group["cvr_pct"]],
              edgecolor='#333', width=0.6)
ax.axhline(y=30, color='red', linestyle='--', linewidth=1.5, label='30% 기준선')
ax.set_xticks(x)
ax.set_xticklabels(conv_by_group["recv_group"].astype(str), fontsize=11)
ax.set_ylabel("구매 전환율 (%)", fontsize=11)
ax.set_title("선물 수신 횟수별 구매 전환율\n(빨간색=30% 초과 달성)", fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(axis='y', alpha=0.3)

for i, (pct, cnt) in enumerate(zip(conv_by_group["cvr_pct"], conv_by_group["total_users"])):
    ax.text(i, pct + 0.5, f"{pct:.1f}%\n(n={cnt:,})", ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer4_conversion_by_recv.png", dpi=150, bbox_inches='tight')
plt.close()
print("\n차트 저장: layer4_conversion_by_recv.png")

# Chart 2: Reciprocity Index
fig, ax = plt.subplots(figsize=(9, 5))
recip_data = {
    '30일 내': recip_30 / total_receivers * 100,
    '60일 내': recip_60 / total_receivers * 100,
    '90일 내': recip_90 / total_receivers * 100,
    '미전환':  never_sent / total_receivers * 100
}
colors_r = ['#2ED573', '#7BED9F', '#A4FFCB', '#A4B0BE']
bars = ax.bar(recip_data.keys(), recip_data.values(), color=colors_r, edgecolor='#333')
ax.set_ylabel("비율 (%)", fontsize=11)
ax.set_title("Reciprocity Index\n(선물 수신 후 발신 전환 시점별 비율)", fontsize=13, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, recip_data.values()):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f"{val:.1f}%", ha='center', fontsize=10, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer4_reciprocity.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer4_reciprocity.png")

# Chart 3: Referral Generation 분포 + GMV
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

gen_labels = gen_dist.index.astype(str)
ax1.bar(gen_labels, gen_dist.values, color='#FEE500', edgecolor='#333')
ax1.set_title("Referral Generation별 유저 수", fontsize=12, fontweight='bold')
ax1.set_xlabel("세대 (Generation)")
ax1.set_ylabel("유저 수")
ax1.grid(axis='y', alpha=0.3)

ax2.bar(gen_gmv["referral_generation"].astype(str), gen_gmv["gmv_bn"],
        color='#FF6B00', edgecolor='#333', alpha=0.85)
ax2.set_title("Referral Generation별 GMV", fontsize=12, fontweight='bold')
ax2.set_xlabel("세대 (Generation)")
ax2.set_ylabel("GMV (억원)")
ax2.grid(axis='y', alpha=0.3)

plt.suptitle("바이럴 세대별 분석", fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer4_referral_generation.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer4_referral_generation.png")

# Chart 4: K-factor 시각화 (인포그래픽 스타일)
fig, ax = plt.subplots(figsize=(8, 5))
ax.axis('off')
ax.text(0.5, 0.85, "K-factor (바이럴 계수)", ha='center', va='center', fontsize=14, fontweight='bold', transform=ax.transAxes)
ax.text(0.5, 0.65, f"{k_factor:.3f}", ha='center', va='center', fontsize=48,
        fontweight='bold', color='#FF4757' if k_factor > 0.5 else '#747D8C', transform=ax.transAxes)
ax.text(0.5, 0.48, f"= 평균 초대수 {avg_invites:.2f}명 × 전환율 {overall_cvr*100:.1f}%",
        ha='center', va='center', fontsize=12, transform=ax.transAxes)
ax.text(0.5, 0.32,
        f"{'바이럴 성장 (K>1)' if k_factor > 1 else '선형 성장 (K<1) — 유기적 보완 필요'}",
        ha='center', va='center', fontsize=11,
        color='#2ED573' if k_factor > 1 else '#FFA502', transform=ax.transAxes)
ax.set_facecolor('#F8F9FA')
fig.patch.set_facecolor('#F8F9FA')
plt.tight_layout()
plt.savefig(f"{CHART_DIR}/layer4_kfactor.png", dpi=150, bbox_inches='tight')
plt.close()
print("차트 저장: layer4_kfactor.png")

print(f"\n[Layer 4 완료]")
print(f"  K-factor: {k_factor:.3f}")
print(f"  90일 내 reciprocity: {recip_90/total_receivers*100:.1f}%")
