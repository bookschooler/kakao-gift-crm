"""
Phase 4: Viral Loop 분석 (v2 — Selfmade 확장판)
================================================
Section 1.  사전 작업: 유저별 수신/발신 피처 생성
Section 2.  K-factor
Section 3.  수신 횟수별 전환율 곡선 + 로지스틱 피팅
Section 3-2. 마케팅 집중 구간 (delta 분석)
Section 4.  Reciprocity Index (7/14/30/90일)
Section 5.  바이럴 세대 분포 + LTV
Section 6.  첫 전환까지 소요일 분포
Section 7.  방향성 상호성 (6단계)
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

BASE = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift\selfmade"

# ─────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────
users    = pd.read_csv(f"{BASE}/users.csv")
orders   = pd.read_csv(f"{BASE}/orders.csv",        parse_dates=["created_at", "updated_at"])
receipts = pd.read_csv(f"{BASE}/gift_receipts.csv", parse_dates=["accepted_at", "expires_at"])

# order_status='accepted' / receipt_status='accepted' 필터
orders_ok   = orders[orders["order_status"]   == "accepted"].copy()
receipts_ok = receipts[receipts["receipt_status"] == "accepted"].copy()

print("=" * 65)
print("[Phase 4] Viral Loop 분석")
print("=" * 65)
print(f"orders_ok: {len(orders_ok):,}  receipts_ok: {len(receipts_ok):,}  users: {len(users):,}")

# ─────────────────────────────────────────
# SECTION 1. 사전 작업
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 1. 사전 작업 - 유저별 수신/발신 피처")
print("=" * 65)

# 수신 통계 (receipts_ok 기준)
recv_stats = (
    receipts_ok.groupby("receiver_user_id")
    .agg(received_count=("order_id", "count"),
         first_received_at=("accepted_at", "min"))
    .reset_index()
    .rename(columns={"receiver_user_id": "user_id"})
)

# 발신 통계 (orders_ok 기준)
sent_stats = (
    orders_ok.groupby("sender_user_id")
    .agg(sent_count=("order_id", "count"),
         first_sent_at=("created_at", "min"))
    .reset_index()
    .rename(columns={"sender_user_id": "user_id"})
)

# 유저 테이블 베이스
df = users[["user_id", "referral_generation"]].copy()
df = df.merge(recv_stats, on="user_id", how="left")
df = df.merge(sent_stats, on="user_id", how="left")

# is_viral_converted: 수신 후 발신
df["is_viral_converted"] = (
    df["first_sent_at"].notna()
    & df["first_received_at"].notna()
    & (df["first_sent_at"] > df["first_received_at"])
)

# days_to_convert
df["days_to_convert"] = (df["first_sent_at"] - df["first_received_at"]).dt.days

recv_has = df["received_count"].notna()
print(f"전체 유저: {len(df):,}")
print(f"수신 경험자 (received_count>0): {recv_has.sum():,}  ({recv_has.mean()*100:.1f}%)")
print(f"발신 경험자 (sent_count>0): {df['sent_count'].notna().sum():,}  ({df['sent_count'].notna().mean()*100:.1f}%)")
print(f"viral_converted (수신→발신): {df['is_viral_converted'].sum():,}  ({df['is_viral_converted'].mean()*100:.1f}%)")

# ─────────────────────────────────────────
# SECTION 2. K-factor
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 2. K-factor")
print("=" * 65)

# 수신 경험자 기준
recv_df = df[recv_has].copy()

avg_invites = recv_df["received_count"].mean()           # 평균 received_count
conv_rate   = recv_df["is_viral_converted"].mean()       # viral_converted 비율
k_factor    = avg_invites * conv_rate

print(f"수신 경험자 수: {len(recv_df):,}")
print(f"avg_invites (평균 received_count): {avg_invites:.4f}")
print(f"conv_rate (viral_converted 비율): {conv_rate*100:.2f}%")
print(f"K-factor = {avg_invites:.4f} × {conv_rate:.4f} = {k_factor:.4f}")
print(f"→ K-factor {'> 1 (바이럴 성장)' if k_factor > 1 else '< 1 (선형 성장, 유기 보완 필요)'}")

# ─────────────────────────────────────────
# SECTION 3. 수신 횟수별 전환율 곡선
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 3. 수신 횟수별 전환율 곡선")
print("=" * 65)

# received_count 20회 이하 필터, NaN 제거
curve_df = recv_df[recv_df["received_count"] <= 20].copy()
conv_curve = (
    curve_df.groupby("received_count")["is_viral_converted"]
    .agg(["sum", "count", "mean"])
    .reset_index()
    .rename(columns={"sum": "converted", "count": "total", "mean": "conv_rate"})
)
conv_curve["conv_pct"] = conv_curve["conv_rate"] * 100

print(conv_curve[["received_count", "total", "converted", "conv_pct"]].to_string(index=False))

# 수신 4회 전환율
row4 = conv_curve[conv_curve["received_count"] == 4]
if len(row4):
    print(f"\n[수신 4회 전환율] {row4['conv_pct'].values[0]:.1f}%  (n={row4['total'].values[0]:,})")
else:
    print("\n수신 4회 데이터 없음")

# 로지스틱 회귀 피팅
try:
    from scipy.optimize import curve_fit

    def logistic(x, L, k, x0):  # 로지스틱 함수: L=최대값, k=기울기, x0=변곡점
        return L / (1 + np.exp(-k * (x - x0)))

    x_data = conv_curve["received_count"].values.astype(float)
    y_data = conv_curve["conv_rate"].values.astype(float)
    popt, _ = curve_fit(logistic, x_data, y_data, p0=[1, 0.3, 5], maxfev=10000)
    L, k_fit, x0 = popt
    print(f"\n[로지스틱 피팅] L={L:.3f}, k={k_fit:.3f}, x0(변곡점)={x0:.2f}회")
    print(f"  → 포화 전환율 추정: {L*100:.1f}%  |  변곡점: {x0:.1f}회 수신 시")
except Exception as e:
    print(f"\n[로지스틱 피팅 실패] {e}")

# ─────────────────────────────────────────
# SECTION 3-2. 마케팅 집중 구간 (delta 분석)
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 3-2. 마케팅 집중 구간 (delta 분석)")
print("=" * 65)

conv_curve_sorted = conv_curve.sort_values("received_count").reset_index(drop=True)
conv_curve_sorted["delta"] = conv_curve_sorted["conv_pct"].diff()  # 인접 구간 전환율 차이

q75 = conv_curve_sorted["delta"].quantile(0.75)
focus_zones = conv_curve_sorted[conv_curve_sorted["delta"] >= q75][["received_count", "conv_pct", "delta"]]

print(f"delta 상위 25% 임계값: {q75:.2f}%p")
print("\n집중 공략 구간 (delta 상위 25%):")
print(focus_zones.to_string(index=False))
print(f"\n→ 마케팅 집중 구간: received_count {focus_zones['received_count'].min()}~{focus_zones['received_count'].max()}회")

# ─────────────────────────────────────────
# SECTION 4. Reciprocity Index
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 4. Reciprocity Index")
print("=" * 65)

# gift_receipts에서 accepted_at + orders.created_at JOIN
recip_base = (
    receipts_ok[["order_id", "receiver_user_id", "accepted_at"]]
    .merge(orders_ok[["order_id", "created_at"]], on="order_id", how="left")
)

# 각 수신자의 accepted_at 이후 최초 발신 일자 찾기
# → orders_ok에서 해당 유저의 발신 이벤트
recip_base2 = recip_base.merge(
    orders_ok[["sender_user_id", "created_at"]].rename(columns={"sender_user_id": "receiver_user_id", "created_at": "sent_at"}),
    on="receiver_user_id", how="left"
)

# 수신 후 발신이어야 함 (sent_at > accepted_at)
recip_base2 = recip_base2[recip_base2["sent_at"] > recip_base2["accepted_at"]].copy()
recip_base2["days_diff"] = (recip_base2["sent_at"] - recip_base2["accepted_at"]).dt.days

# 수신자별 최소 days_diff (가장 빠른 재발신)
min_days = recip_base2.groupby("receiver_user_id")["days_diff"].min().reset_index()

total_receivers = receipts_ok["receiver_user_id"].nunique()
r7  = (min_days["days_diff"] <=  7).sum()
r14 = (min_days["days_diff"] <= 14).sum()
r30 = (min_days["days_diff"] <= 30).sum()
r90 = (min_days["days_diff"] <= 90).sum()

print(f"수신 경험 유니크 유저: {total_receivers:,}")
print(f"7일  내 재발신: {r7:,}  ({r7/total_receivers*100:.1f}%)")
print(f"14일 내 재발신: {r14:,}  ({r14/total_receivers*100:.1f}%)")
print(f"30일 내 재발신: {r30:,}  ({r30/total_receivers*100:.1f}%)")
print(f"90일 내 재발신: {r90:,}  ({r90/total_receivers*100:.1f}%)")

# ─────────────────────────────────────────
# SECTION 5. 바이럴 세대 분포 + LTV
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 5. 바이럴 세대 분포 + LTV")
print("=" * 65)

gen_user = users.groupby("referral_generation").size().reset_index(name="user_count")

gen_gmv = (
    orders_ok.merge(users[["user_id", "referral_generation"]], left_on="sender_user_id", right_on="user_id", how="left")
    .groupby("referral_generation")["total_amount_krw"]
    .sum()
    .reset_index()
    .rename(columns={"total_amount_krw": "total_gmv"})
)

gen_stats = gen_user.merge(gen_gmv, on="referral_generation", how="left")
gen_stats["ltv_per_user"] = gen_stats["total_gmv"] / gen_stats["user_count"]

print(gen_stats.to_string(index=False))

# 0세대 대비 1세대 LTV 배율
ltv0 = gen_stats.loc[gen_stats["referral_generation"] == 0, "ltv_per_user"].values[0]
ltv1 = gen_stats.loc[gen_stats["referral_generation"] == 1, "ltv_per_user"].values[0]
print(f"\n0세대 LTV: {ltv0:,.0f}원")
print(f"1세대 LTV: {ltv1:,.0f}원")
print(f"1세대/0세대 LTV 배율: {ltv1/ltv0:.3f}x")

# ─────────────────────────────────────────
# SECTION 6. 첫 전환까지 소요일 분포
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 6. 첫 전환까지 소요일 분포")
print("=" * 65)

converted_days = df.loc[df["is_viral_converted"] & df["days_to_convert"].notna(), "days_to_convert"]
converted_days = converted_days[converted_days >= 0]  # 음수 제거

p25 = converted_days.quantile(0.25)
p50 = converted_days.quantile(0.50)
p75 = converted_days.quantile(0.75)

print(f"viral_converted 유저 수: {len(converted_days):,}")
print(f"25 퍼센타일: {p25:.0f}일")
print(f"중앙값     : {p50:.0f}일")
print(f"75 퍼센타일: {p75:.0f}일")
print(f"평균       : {converted_days.mean():.1f}일")
print(f"최대       : {converted_days.max():.0f}일")

# 누적 분포 (14/30/60/90/180일)
for d in [14, 30, 60, 90, 180]:
    pct = (converted_days <= d).mean() * 100
    print(f"  {d:>3}일 이내 전환: {pct:.1f}%")

# ─────────────────────────────────────────
# SECTION 7. 방향성 상호성
# ─────────────────────────────────────────
print("\n" + "=" * 65)
print("SECTION 7. 방향성 상호성")
print("=" * 65)

# A→B 이벤트: orders_ok + receipts_ok JOIN
ab_events = (
    orders_ok[["order_id", "sender_user_id", "created_at", "total_amount_krw"]]
    .merge(receipts_ok[["order_id", "receiver_user_id", "accepted_at"]], on="order_id", how="inner")
    .rename(columns={
        "sender_user_id":   "user_a",
        "receiver_user_id": "user_b",
        "created_at":       "a_to_b_at",
        "total_amount_krw": "a_to_b_amount"
    })
)
ab_events = ab_events[ab_events["user_a"] != ab_events["user_b"]]  # 자기 자신 제거

print(f"\n[Step 1] A→B 이벤트 수: {len(ab_events):,}")

# Step 1. A→B 이후 180일 이내 B→A pair 추출
# B→A: user_b가 발신자, user_a가 수신자
# ab_events를 B→A 관점으로 복사
ba_events = ab_events.rename(columns={
    "user_a": "user_b_orig",
    "user_b": "user_a_orig",
    "a_to_b_at": "b_to_a_at",
    "a_to_b_amount": "b_to_a_amount"
})[["user_b_orig", "user_a_orig", "b_to_a_at", "b_to_a_amount"]]

# JOIN: A→B와 B→A 매칭 (user_a == user_b_orig AND user_b == user_a_orig)
pairs = ab_events.merge(
    ba_events,
    left_on=["user_a", "user_b"],
    right_on=["user_b_orig", "user_a_orig"],
    how="inner"
)

# 180일 이내 조건
pairs["days_to_reciprocate"] = (pairs["b_to_a_at"] - pairs["a_to_b_at"]).dt.days
pairs_valid = pairs[(pairs["days_to_reciprocate"] > 0) & (pairs["days_to_reciprocate"] <= 180)].copy()

print(f"180일 이내 상호성 pair 수: {len(pairs_valid):,}")
print(f"평균 days_to_reciprocate: {pairs_valid['days_to_reciprocate'].mean():.1f}일")
print(f"중앙값 days_to_reciprocate: {pairs_valid['days_to_reciprocate'].median():.1f}일")

# Step 2. 부채감 해소형 vs 감사 확산형
# 수신 후 90일 이내 발신
# A→B 후 B가 90일 이내 발신
# original_sender == new_recipient  → 부채감 해소형 (A에게 되돌려 줌)
# original_sender != new_recipient  → 감사 확산형 (C에게 보냄)
print("\n[Step 2] 부채감 해소형 vs 감사 확산형")

# B가 90일 이내 보낸 모든 주문 찾기
# ab_events의 user_b (수신자) 가 90일 이내 발신한 것
ninety_day = ab_events.merge(
    ab_events.rename(columns={
        "user_a":         "new_sender",
        "user_b":         "new_receiver",
        "a_to_b_at":      "new_sent_at",
        "a_to_b_amount":  "new_amount",
        "order_id":       "new_order_id",
        "accepted_at":    "new_accepted_at"
    }),
    left_on="user_b",
    right_on="new_sender",
    how="inner"
)
ninety_day["days_gap"] = (ninety_day["new_sent_at"] - ninety_day["accepted_at"]).dt.days
ninety_day_90 = ninety_day[(ninety_day["days_gap"] > 0) & (ninety_day["days_gap"] <= 90)].copy()

# 부채감 해소형: new_receiver == user_a (원래 보낸 사람에게 되돌려 줌)
debt_relief = ninety_day_90[ninety_day_90["new_receiver"] == ninety_day_90["user_a"]]
# 감사 확산형: new_receiver != user_a
gratitude   = ninety_day_90[ninety_day_90["new_receiver"] != ninety_day_90["user_a"]]

total_90 = len(ninety_day_90)
print(f"90일 이내 재발신 이벤트: {total_90:,}")
print(f"부채감 해소형: {len(debt_relief):,}  ({len(debt_relief)/total_90*100:.1f}%)  AOV: {debt_relief['new_amount'].mean():,.0f}원")
print(f"감사 확산형  : {len(gratitude):,}  ({len(gratitude)/total_90*100:.1f}%)  AOV: {gratitude['new_amount'].mean():,.0f}원")

# Step 3. 양방향 vs 단방향 AOV
print("\n[Step 3] 양방향 vs 단방향 AOV")

bilateral_senders = set(pairs_valid["user_a"]) | set(pairs_valid["user_b_orig"])
orders_ok["is_bilateral"] = orders_ok["sender_user_id"].isin(bilateral_senders)
aov_bilateral   = orders_ok[orders_ok["is_bilateral"]]["total_amount_krw"].mean()
aov_unilateral  = orders_ok[~orders_ok["is_bilateral"]]["total_amount_krw"].mean()

print(f"양방향 페어 발신자 AOV: {aov_bilateral:,.0f}원")
print(f"단방향 발신자 AOV      : {aov_unilateral:,.0f}원")
print(f"차이 (배율)           : {aov_bilateral/aov_unilateral:.3f}x")

# Step 4. 체인 단계별 AOV + symmetric_rate
print("\n[Step 4] 체인 단계별 AOV + symmetric_rate")

mean_a2b = pairs_valid["a_to_b_amount"].mean()
mean_b2a = pairs_valid["b_to_a_amount"].mean()
symmetric_rate = (pairs_valid["b_to_a_amount"] >= pairs_valid["a_to_b_amount"] * 0.9).mean()

print(f"A→B 평균 금액: {mean_a2b:,.0f}원")
print(f"B→A 평균 금액: {mean_b2a:,.0f}원")
print(f"symmetric_rate (b_to_a >= a_to_b×90%): {symmetric_rate*100:.1f}%")

# Step 5. 가격 스위트 스팟
print("\n[Step 5] 가격대별 상호성 (수신 금액대 → reciprocity_rate)")

def price_band(amt):
    if amt < 10000:   return "1만원 미만"
    elif amt < 30000: return "1~3만원"
    elif amt < 50000: return "3~5만원"
    elif amt < 100000: return "5~10만원"
    else:              return "10만원+"

ab_events["price_band"] = ab_events["a_to_b_amount"].apply(price_band)

# pair 내 a_to_b_amount 기반 price_band
pairs_valid2 = pairs_valid.copy()
pairs_valid2["price_band"] = pairs_valid2["a_to_b_amount"].apply(price_band)

# 전체 이벤트 대비 pair 된 것 비율
ab_events_band_cnt = ab_events.groupby("price_band").size().reset_index(name="total_recv")
pair_band_cnt = pairs_valid2.groupby("price_band").size().reset_index(name="pair_cnt")
pair_band_aov = pairs_valid2.groupby("price_band")["b_to_a_amount"].mean().reset_index(name="reply_aov")

sweet_spot = ab_events_band_cnt.merge(pair_band_cnt, on="price_band", how="left").merge(pair_band_aov, on="price_band", how="left")
sweet_spot["pair_cnt"] = sweet_spot["pair_cnt"].fillna(0)
sweet_spot["reciprocity_rate"] = sweet_spot["pair_cnt"] / sweet_spot["total_recv"]

band_order = ["1만원 미만", "1~3만원", "3~5만원", "5~10만원", "10만원+"]
sweet_spot["price_band"] = pd.Categorical(sweet_spot["price_band"], categories=band_order, ordered=True)
sweet_spot = sweet_spot.sort_values("price_band")

print(sweet_spot[["price_band", "total_recv", "pair_cnt", "reciprocity_rate", "reply_aov"]].to_string(index=False))

# Step 6. 기념일 자연 발생 보답
print("\n[Step 6] 기념일 근처 보답 비율")

ANNIVERSARIES = [
    (11, 11),  # 빼빼로데이
    ( 5,  8),  # 어버이날
    ( 3, 14),  # 화이트데이
    ( 2, 14),  # 발렌타인
    ( 5,  5),  # 어린이날
]

def is_near_anniversary(dt, window=7):
    if pd.isna(dt): return False
    for month, day in ANNIVERSARIES:
        ann = pd.Timestamp(year=dt.year, month=month, day=day)
        if abs((dt - ann).days) <= window:
            return True
    return False

pairs_valid["near_ann"] = pairs_valid["b_to_a_at"].apply(is_near_anniversary)

near_rate   = pairs_valid["near_ann"].mean()
near_count  = pairs_valid["near_ann"].sum()
total_pairs = len(pairs_valid)

# 기념일 근처 vs 일반일 일평균 보답 건수
# 분석 기간 추정
date_min = pairs_valid["b_to_a_at"].min()
date_max = pairs_valid["b_to_a_at"].max()
total_days = (date_max - date_min).days + 1

# 기념일 근처 날짜 수 (5개 기념일 × ±7일 = 각 15일, 겹침 없다고 가정)
ann_days_approx = min(5 * 15, total_days)
non_ann_days    = max(total_days - ann_days_approx, 1)

daily_near = near_count / ann_days_approx
daily_non  = (total_pairs - near_count) / non_ann_days

print(f"전체 pair: {total_pairs:,}  |  기념일 ±7일 내: {near_count:,}  ({near_rate*100:.1f}%)")
print(f"기념일 근처 일평균 보답: {daily_near:.2f}건/일")
print(f"일반일 일평균 보답    : {daily_non:.2f}건/일")
print(f"기념일 효과 배율      : {daily_near/daily_non:.2f}x")

print("\n" + "=" * 65)
print("[Phase 4 완료]")
print("=" * 65)
