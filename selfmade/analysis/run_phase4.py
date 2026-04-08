"""Phase 4 Viral Loop 분석 — 로컬 실행용"""
import pandas as pd
import numpy as np
from datetime import timedelta
import sys, os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..')

# ── 데이터 로드 ──────────────────────────────────────────────
print('데이터 로딩...')
users = pd.read_csv(f'{DATA_DIR}/users.csv')
orders = pd.read_csv(f'{DATA_DIR}/orders.csv', parse_dates=['created_at', 'updated_at'])
receipts = pd.read_csv(f'{DATA_DIR}/gift_receipts.csv', parse_dates=['accepted_at', 'expires_at'])

orders_ok = orders[orders['order_status'] == 'accepted'].copy()
receipts_ok = receipts[receipts['receipt_status'] == 'accepted'].copy()

print(f'  users: {len(users):,}행 / orders(accepted): {len(orders_ok):,}행 / receipts(accepted): {len(receipts_ok):,}행')

# ══════════════════════════════════════════════════════════════
# Section 1. 사전 작업 — is_viral_converted
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 1. 사전 작업')
print('='*60)

recv = receipts_ok.groupby('receiver_user_id').agg(
    received_count=('receipt_id', 'count'),
    first_received_at=('accepted_at', 'min')
).reset_index().rename(columns={'receiver_user_id': 'user_id'})

sent = orders_ok.groupby('sender_user_id').agg(
    sent_count=('order_id', 'count'),
    first_sent_at=('created_at', 'min')
).reset_index().rename(columns={'sender_user_id': 'user_id'})

df_base = users[['user_id', 'referral_generation']].merge(recv, on='user_id', how='left').merge(sent, on='user_id', how='left')
df_base['received_count'] = df_base['received_count'].fillna(0).astype(int)
df_base['sent_count'] = df_base['sent_count'].fillna(0).astype(int)
df_base['is_viral_converted'] = (
    df_base['first_sent_at'].notna() &
    df_base['first_received_at'].notna() &
    (df_base['first_sent_at'] > df_base['first_received_at'])
)
df_base['days_to_convert'] = (df_base['first_sent_at'] - df_base['first_received_at']).dt.days

total = len(df_base)
recv_users = (df_base['received_count'] > 0).sum()
sent_users = (df_base['sent_count'] > 0).sum()
viral_users = df_base['is_viral_converted'].sum()
print(f'  전체 유저: {total:,}명')
print(f'  수신 경험 유저: {recv_users:,}명 ({recv_users/total:.1%})')
print(f'  발신 경험 유저: {sent_users:,}명 ({sent_users/total:.1%})')
print(f'  바이럴 전환 유저: {viral_users:,}명 ({viral_users/total:.1%})')

# ══════════════════════════════════════════════════════════════
# Section 2. K-factor
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 2. K-factor')
print('='*60)

df_recv = df_base[df_base['received_count'] > 0].copy()
avg_invites = df_recv['received_count'].mean()
conv_rate = df_recv['is_viral_converted'].mean()
k_factor = avg_invites * conv_rate

print(f'  평균 수신 횟수 (i): {avg_invites:.3f}')
print(f'  바이럴 전환율 (c):  {conv_rate:.3f} ({conv_rate:.1%})')
print(f'  K-factor (i × c):   {k_factor:.3f}')
print(f'  → {"K≥1 바이럴 성장" if k_factor >= 1 else "K<1 바이럴 감쇠"}')

# ══════════════════════════════════════════════════════════════
# Section 3. 수신 횟수별 전환율 곡선
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 3. 수신 횟수별 전환율')
print('='*60)

df_conv = df_recv.groupby('received_count').agg(
    user_count=('user_id', 'count'),
    converted=('is_viral_converted', 'sum')
).reset_index()
df_conv['conversion_rate'] = df_conv['converted'] / df_conv['user_count']

df_plot = df_conv[df_conv['received_count'] <= 20].copy()
print(df_plot[['received_count', 'user_count', 'converted', 'conversion_rate']].to_string(index=False))

rate_4 = df_conv.loc[df_conv['received_count'] == 4, 'conversion_rate']
if not rate_4.empty:
    print(f'\n  수신 4회 시 전환율: {rate_4.values[0]:.1%} (카카오 공식 30%+ 기준)')

# Section 3-2. delta 분석
print('\n--- delta 분석 (마케팅 집중 구간) ---')
df_delta = df_plot[['received_count', 'conversion_rate', 'user_count']].copy()
df_delta['prev_rate'] = df_delta['conversion_rate'].shift(1)
df_delta['delta'] = df_delta['conversion_rate'] - df_delta['prev_rate']
df_delta = df_delta.dropna(subset=['delta']).reset_index(drop=True)
q75 = df_delta['delta'].quantile(0.75)

def label(d):
    if d >= q75: return '*** 집중 공략'
    elif d >= df_delta['delta'].quantile(0.50): return '  * 관심 구간'
    else: return '    일반'

df_delta['priority'] = df_delta['delta'].apply(label)
for _, row in df_delta.iterrows():
    r = int(row['received_count'])
    print(f'  {r-1}→{r}회: +{row["delta"]:.1%}  ({row["priority"].strip()})')

# ══════════════════════════════════════════════════════════════
# Section 4. Reciprocity Index
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 4. Reciprocity Index')
print('='*60)

# 수신 이벤트별 다음 발신까지 소요일 계산
recv_events = receipts_ok[['receiver_user_id', 'accepted_at']].copy()
recv_events.columns = ['user_id', 'accepted_at']

# 유저별 발신 이벤트
send_events = orders_ok[['sender_user_id', 'created_at']].copy()
send_events.columns = ['user_id', 'sent_at']

merged = recv_events.merge(send_events, on='user_id', how='left')
merged = merged[merged['sent_at'] > merged['accepted_at']].copy()
merged['days'] = (merged['sent_at'] - merged['accepted_at']).dt.days

# 수신 이벤트별 최소 days만 남기기
min_days = merged.groupby(['user_id', 'accepted_at'])['days'].min().reset_index()

total_events = len(recv_events)
r7 = (min_days['days'].between(1, 7)).sum() / total_events
r14 = (min_days['days'].between(1, 14)).sum() / total_events
r30 = (min_days['days'].between(1, 30)).sum() / total_events
r90 = (min_days['days'].between(1, 90)).sum() / total_events

print(f'  총 수신 이벤트: {total_events:,}건')
print(f'   7일 내 재발신: {r7:.1%}')
print(f'  14일 내 재발신: {r14:.1%}')
print(f'  30일 내 재발신: {r30:.1%}')
print(f'  90일 내 재발신: {r90:.1%}')
print(f'  → 7~14일 추가 전환: {(r14-r7):.1%}')

# ══════════════════════════════════════════════════════════════
# Section 5. 자기선물 vs 타인선물 유저 K-factor 비교
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 5. 자기선물 vs 타인선물 유저 K-factor 비교')
print('='*60)

# 자기선물 유저 분류 (gift_occasion == 'self_gift' 주문이 1건이라도 있으면)
self_gift_user_ids = set(
    orders_ok[orders_ok['gift_occasion'] == 'self_gift']['sender_user_id'].unique()
)
df_base['user_type'] = df_base['user_id'].apply(
    lambda x: '자기선물 유저' if x in self_gift_user_ids else '타인선물 유저'
)

# "진짜" 바이럴 전환: 첫 발신이 타인에게 간 경우 (자기선물 첫발신 제외)
first_other_send = (
    orders_ok[orders_ok['gift_occasion'] != 'self_gift']
    .groupby('sender_user_id')['created_at'].min()
    .reset_index()
    .rename(columns={'sender_user_id': 'user_id', 'created_at': 'first_other_sent_at'})
)
df_base = df_base.merge(first_other_send, on='user_id', how='left')

df_base['is_true_viral'] = (
    df_base['first_other_sent_at'].notna() &
    df_base['first_received_at'].notna() &
    (df_base['first_other_sent_at'] > df_base['first_received_at'])
)

print(f'\n  자기선물 유저 수: {len(self_gift_user_ids):,}명 ({len(self_gift_user_ids)/len(df_base):.1%})')
print(f'  타인선물 유저 수: {(df_base["user_type"]=="타인선물 유저").sum():,}명\n')

results = []
for gtype in ['자기선물 유저', '타인선물 유저']:
    grp_all = df_base[df_base['user_type'] == gtype]
    grp_recv = grp_all[grp_all['received_count'] > 0]
    avg_recv = grp_recv['received_count'].mean()          # i
    conv_rate = grp_recv['is_true_viral'].mean()          # c
    k = avg_recv * conv_rate
    results.append({'유저 유형': gtype, '유저 수': len(grp_all),
                    '평균 수신 횟수(i)': round(avg_recv, 3),
                    '바이럴 전환율(c)': f'{conv_rate:.1%}',
                    'K-factor': round(k, 3)})
    print(f'  [{gtype}]')
    print(f'    평균 수신 횟수 (i): {avg_recv:.3f}')
    print(f'    바이럴 전환율  (c): {conv_rate:.1%}')
    print(f'    K-factor (i × c):  {k:.3f}')

k_self = results[0]['K-factor']
k_other = results[1]['K-factor']
print(f'\n  → 타인선물 유저 K-factor가 자기선물 유저 대비 {k_other/k_self:.2f}x 높음' if k_self > 0 else '')

# ══════════════════════════════════════════════════════════════
# Section 6. 첫 전환까지 소요일
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 6. 첫 전환까지 소요일')
print('='*60)

df_converted = df_base[
    (df_base['is_viral_converted']) &
    (df_base['days_to_convert'] >= 1) &
    (df_base['days_to_convert'] <= 365)
].copy()

med = df_converted['days_to_convert'].median()
p25 = df_converted['days_to_convert'].quantile(0.25)
p75 = df_converted['days_to_convert'].quantile(0.75)
print(f'  바이럴 전환 유저 수: {len(df_converted):,}명')
print(f'  중앙값: {med:.0f}일')
print(f'  25%: {p25:.0f}일 / 75%: {p75:.0f}일')
print(f'  14일 이내 전환 비율: {(df_converted["days_to_convert"] <= 14).mean():.1%}')

# ══════════════════════════════════════════════════════════════
# Section 7. 방향성 상호성
# ══════════════════════════════════════════════════════════════
print('\n' + '='*60)
print('Section 7. 방향성 상호성 심층 분석')
print('='*60)

# 전체 발신 페어 구성
sent_pairs = orders_ok.merge(receipts[['order_id', 'receiver_user_id']], on='order_id', how='inner')
sent_pairs = sent_pairs[['sender_user_id', 'receiver_user_id', 'created_at', 'total_amount_krw']].copy()
sent_pairs.columns = ['user_a', 'user_b', 'sent_at', 'sent_amount']

# Step 1. pair 추출
print('\n--- Step 1. 양방향 pair 추출 ---')
pairs = sent_pairs.merge(
    sent_pairs,
    left_on=['user_a', 'user_b'],
    right_on=['user_b', 'user_a'],
    suffixes=('_ab', '_ba')
)
pairs = pairs[pairs['sent_at_ba'] > pairs['sent_at_ab']].copy()
pairs['days_to_reciprocate'] = (pairs['sent_at_ba'] - pairs['sent_at_ab']).dt.days
pairs = pairs[pairs['days_to_reciprocate'] <= 180].copy()

print(f'  양방향 교환 쌍: {len(pairs):,}건')
print(f'  평균 되갚기 소요일: {pairs["days_to_reciprocate"].mean():.1f}일')

# Step 2. 부채감 해소형 vs 감사 확산형
print('\n--- Step 2. 부채감 해소형 vs 감사 확산형 ---')

recv_with_order = receipts_ok[['order_id', 'receiver_user_id', 'accepted_at']].copy()
recv_with_sender = recv_with_order.merge(
    orders_ok[['order_id', 'sender_user_id', 'total_amount_krw']],
    on='order_id', how='left'
)
recv_with_sender.columns = ['order_id', 'user_id', 'accepted_at', 'original_sender', 'received_amount']

# 수신 후 90일 이내 발신 JOIN
next_sends = orders_ok.merge(
    receipts[['order_id', 'receiver_user_id']],
    on='order_id', how='inner'
)[['sender_user_id', 'receiver_user_id', 'created_at', 'total_amount_krw']]
next_sends.columns = ['user_id', 'new_recipient', 'send_at', 'sent_amount']

rws = recv_with_sender.merge(next_sends, on='user_id', how='inner')
rws = rws[(rws['send_at'] > rws['accepted_at']) &
          (rws['send_at'] <= rws['accepted_at'] + pd.Timedelta(days=90))].copy()

direct = (rws['original_sender'] == rws['new_recipient'])
direct_count = direct.sum()
forward_count = (~direct).sum()
total_rws = len(rws)

direct_rate = direct_count / total_rws if total_rws > 0 else 0
forward_rate = forward_count / total_rws if total_rws > 0 else 0
direct_aov = rws.loc[direct, 'sent_amount'].mean()
forward_aov = rws.loc[~direct, 'sent_amount'].mean()

print(f'  부채감 해소형(A→B→A): {direct_count:,}건 ({direct_rate:.1%}) AOV {direct_aov:,.0f}원')
print(f'  감사 확산형(A→B→C):   {forward_count:,}건 ({forward_rate:.1%}) AOV {forward_aov:,.0f}원')
winner = '부채감 해소형' if direct_rate > forward_rate else '감사 확산형'
print(f'  → 카카오는 {winner}이 더 강함')

# Step 3. 양방향 vs 단방향 AOV
print('\n--- Step 3. 양방향 vs 단방향 AOV ---')
bilateral_senders = set(pairs['user_a_ab'].unique())
orders_with_type = orders_ok.copy()
orders_with_type['pair_type'] = orders_with_type['sender_user_id'].apply(
    lambda x: '양방향' if x in bilateral_senders else '단방향'
)
aov_by_type = orders_with_type.groupby('pair_type')['total_amount_krw'].agg(['mean', 'count']).reset_index()
aov_by_type.columns = ['pair_type', 'aov', 'order_count']
print(aov_by_type.to_string(index=False))
bi_aov = aov_by_type.loc[aov_by_type['pair_type'] == '양방향', 'aov'].values
uni_aov = aov_by_type.loc[aov_by_type['pair_type'] == '단방향', 'aov'].values
if len(bi_aov) > 0 and len(uni_aov) > 0 and uni_aov[0] > 0:
    print(f'  → 배율: {bi_aov[0]/uni_aov[0]:.2f}x (Leider 2009 예상: 1.52x)')

# Step 4. 체인 단계별 AOV
print('\n--- Step 4. 체인 단계별 AOV ---')
aov_ab = pairs['sent_amount_ab'].mean()
aov_ba = pairs['sent_amount_ba'].mean()
ratio = pairs['sent_amount_ba'] / pairs['sent_amount_ab'].replace(0, np.nan)
symmetric = (ratio >= 0.9).mean()
higher = (ratio > 1.0).mean()
print(f'  A→B 평균 AOV: {aov_ab:,.0f}원')
print(f'  B→A 평균 AOV: {aov_ba:,.0f}원')
print(f'  대칭 비율 (B→A ≥ 90% of A→B): {symmetric:.1%}')
print(f'  답례가 더 비싼 비율 (B→A > A→B): {higher:.1%}')

# Step 5. 가격 스위트 스팟
print('\n--- Step 5. 가격 스위트 스팟 ---')

recv_orders = receipts_ok.merge(orders_ok[['order_id', 'total_amount_krw']], on='order_id')

def price_band(x):
    if x < 10000: return '①1만원 미만'
    elif x < 30000: return '②1~3만원'
    elif x < 50000: return '③3~5만원'
    elif x < 100000: return '④5~10만원'
    else: return '⑤10만원 이상'

recv_orders['price_band'] = recv_orders['total_amount_krw'].apply(price_band)

# 수신 후 90일 이내 발신 여부
recv_orders_with_reply = recv_orders.merge(
    orders_ok[['sender_user_id', 'created_at', 'total_amount_krw']].rename(
        columns={'sender_user_id': 'receiver_user_id', 'created_at': 'reply_at', 'total_amount_krw': 'reply_amount'}
    ),
    on='receiver_user_id', how='left'
)
recv_orders_with_reply = recv_orders_with_reply[
    (recv_orders_with_reply['reply_at'].isna()) |
    ((recv_orders_with_reply['reply_at'] > recv_orders_with_reply['accepted_at']) &
     (recv_orders_with_reply['reply_at'] <= recv_orders_with_reply['accepted_at'] + pd.Timedelta(days=90)))
].copy()
recv_orders_with_reply['is_reciprocated'] = recv_orders_with_reply['reply_at'].notna()

sweet = recv_orders_with_reply.groupby('price_band').agg(
    total=('is_reciprocated', 'count'),
    reciprocated=('is_reciprocated', 'sum'),
    reply_aov=('reply_amount', 'mean')
).reset_index()
sweet['rate'] = sweet['reciprocated'] / sweet['total']
sweet = sweet.sort_values('price_band')

for _, row in sweet.iterrows():
    print(f'  {row["price_band"]}: reciprocity {row["rate"]:.1%}  reply AOV {row["reply_aov"]:,.0f}원')

best = sweet.loc[sweet['rate'].idxmax()]
print(f'  → 스위트 스팟: {best["price_band"]} (rate: {best["rate"]:.1%})')

# Step 6. 기념일 자연 발생 보답
print('\n--- Step 6. 기념일 자연 발생 보답 ---')

pairs_dates = pairs.copy()
pairs_dates['mmdd'] = pairs_dates['sent_at_ba'].dt.strftime('%m-%d')

def holiday_group(mmdd):
    m, d = int(mmdd[:2]), int(mmdd[3:])
    if 11 <= m == 11 and 4 <= d <= 18: return '빼빼로데이'
    if m == 5 and 1 <= d <= 15: return '어버이날'
    if m == 3 and 7 <= d <= 21: return '화이트데이'
    if m == 2 and 7 <= d <= 21: return '발렌타인'
    return '일반일'

pairs_dates['holiday'] = pairs_dates['mmdd'].apply(holiday_group)

holiday_stats = pairs_dates.groupby('holiday').agg(
    total_replies=('user_a_ab', 'count'),
    unique_days=('mmdd', 'nunique')
).reset_index()
holiday_stats['avg_daily'] = holiday_stats['total_replies'] / holiday_stats['unique_days']
holiday_stats = holiday_stats.sort_values('avg_daily', ascending=False)

for _, row in holiday_stats.iterrows():
    print(f'  {row["holiday"]}: {row["total_replies"]:,}건 / {row["unique_days"]}일 = 일평균 {row["avg_daily"]:.1f}건')

normal_daily = holiday_stats.loc[holiday_stats['holiday'] == '일반일', 'avg_daily'].values
if len(normal_daily) > 0 and normal_daily[0] > 0:
    for _, row in holiday_stats[holiday_stats['holiday'] != '일반일'].iterrows():
        mult = row['avg_daily'] / normal_daily[0]
        print(f'  → {row["holiday"]}: 일반일 대비 {mult:.1f}x')

# ══════════════════════════════════════════════════════════════
# Section 8. 추가 분석 — Viral 전환 트리거: Occasion 계기 가설 검증
# ══════════════════════════════════════════════════════════════
# 가설: K>1을 만드는 것은 수신 횟수·경과일이 아니라
#       "선물할 이유(occasion)"가 생겼을 때 비로소 전환이 일어남
print('\n' + '='*60)
print('Section 8. Viral 전환 트리거: Occasion 계기 가설 검증')
print('='*60)

from scipy.stats import chi2_contingency, pearsonr

# --- 8-1. 수신 횟수 vs 전환율 선형 상관 검증 ---
print('\n--- 8-1. 수신 횟수 vs 전환율: Pearson 상관 (반증) ---')

df_c8 = df_base[df_base['received_count'] > 0].groupby('received_count').agg(
    user_count=('user_id', 'count'),
    converted=('is_true_viral', 'sum')
).reset_index()
df_c8['conv_rate'] = df_c8['converted'] / df_c8['user_count']
df_c8_trim = df_c8[df_c8['received_count'] <= 20].copy()  # 1~20회 (표본 충분한 구간)

r_val, p_corr = pearsonr(df_c8_trim['received_count'], df_c8_trim['conv_rate'])
print(f'  Pearson r (수신 횟수 1~20 vs 전환율): {r_val:.3f}  p={p_corr:.4f}')
print(f'  → {"약한 상관 — 수신 횟수 단독으로는 전환 설명 어려움 (occasion 가설 지지)" if abs(r_val) < 0.5 else "강한 상관 — 수신 횟수 영향 큼 (가설 기각 필요)"}')

# --- 8-2. 바이럴 전환 유저의 첫 발신 occasion vs 오가닉 유저 첫 발신 occasion ---
print('\n--- 8-2. 첫 발신 occasion: 바이럴 전환 vs 오가닉 유저 비교 ---')

orders_no_self = orders_ok[orders_ok['gift_occasion'] != 'self_gift'].copy()

# ① 바이럴 전환 유저 첫 발신 occasion
true_viral_df = df_base[df_base['is_true_viral']].copy()
viral_first = orders_no_self.merge(
    true_viral_df[['user_id', 'first_other_sent_at']],
    left_on=['sender_user_id', 'created_at'],
    right_on=['user_id', 'first_other_sent_at'],
    how='inner'
)[['user_id', 'gift_occasion', 'occasion_category', 'occasion_subcategory', 'created_at']]

# ② 오가닉 유저 (수신 이력 없거나, 발신이 수신보다 먼저) 첫 발신 occasion
organic_df = df_base[
    (df_base['first_sent_at'].notna()) &
    (
        df_base['first_received_at'].isna() |
        (df_base['first_sent_at'] <= df_base['first_received_at'])
    )
].copy()
organic_first = orders_no_self.merge(
    organic_df[['user_id', 'first_sent_at']],
    left_on=['sender_user_id', 'created_at'],
    right_on=['user_id', 'first_sent_at'],
    how='inner'
)[['user_id', 'gift_occasion', 'occasion_category', 'occasion_subcategory', 'created_at']]

print(f'  바이럴 전환 유저 첫 발신: {len(viral_first):,}건')
print(f'  오가닉 유저 첫 발신: {len(organic_first):,}건')

# occasion_category 비율 비교
viral_cat = viral_first['occasion_category'].value_counts(normalize=True)
organic_cat = organic_first['occasion_category'].value_counts(normalize=True)
print('\n  [occasion_category 비율 비교]')
for cat in ['special', 'daily']:
    v = viral_cat.get(cat, 0)
    o = organic_cat.get(cat, 0)
    print(f'    {cat}: 바이럴={v:.1%}  /  오가닉={o:.1%}  (diff {v-o:+.1%})')

# Chi-square 검정 (occasion_category 기준)
all_cats = sorted(set(viral_first['occasion_category'].unique()) | set(organic_first['occasion_category'].unique()))
contingency = np.array([
    [viral_first['occasion_category'].eq(c).sum() for c in all_cats],
    [organic_first['occasion_category'].eq(c).sum() for c in all_cats]
])
chi2_val, p_chi, dof, _ = chi2_contingency(contingency)
print(f'\n  Chi-square: χ²={chi2_val:.3f}, p={p_chi:.4f}, dof={dof}')
if p_chi < 0.05:
    print('  → p<0.05: 두 그룹의 occasion 분포가 통계적으로 유의미하게 다름')
else:
    print('  → p≥0.05: 두 그룹 모두 첫 발신 시 비슷한 occasion 패턴 → 둘 다 occasion이 트리거')

# Top occasion 목록
print('\n  [Top 5 gift_occasion — 바이럴 전환 첫 발신]')
for occ, pct in viral_first['gift_occasion'].value_counts(normalize=True).head(5).items():
    print(f'    {occ}: {pct:.1%}')
print('\n  [Top 5 gift_occasion — 오가닉 첫 발신]')
for occ, pct in organic_first['gift_occasion'].value_counts(normalize=True).head(5).items():
    print(f'    {occ}: {pct:.1%}')

# --- 8-3. 전환 시점 계절성 (월별) ---
print('\n--- 8-3. 바이럴 전환 시점 계절성 ---')

viral_first_copy = viral_first.copy()
viral_first_copy['month'] = pd.to_datetime(viral_first_copy['created_at']).dt.month
monthly = viral_first_copy.groupby('month').size().reset_index(name='count')
monthly['pct'] = monthly['count'] / monthly['count'].sum()

season_label = {1: '신정', 2: '발렌타인', 3: '화이트데이', 5: '어버이날/스승의날',
                11: '빼빼로데이', 12: '크리스마스'}
for _, row in monthly.iterrows():
    m = int(row['month'])
    bar = '█' * int(row['pct'] * 100)
    label = f'  [{season_label[m]}]' if m in season_label else ''
    print(f'  {m:2d}월: {row["count"]:4,}건 ({row["pct"]:.1%}) {bar}{label}')

peak_month = int(monthly.loc[monthly['count'].idxmax(), 'month'])
print(f'\n  → 최다 전환 월: {peak_month}월 ({season_label.get(peak_month, "기타 시즌")})')

# 시즌 월(2,3,5,11,12) vs 비시즌 월 전환 비율
season_months = {2, 3, 5, 11, 12}
season_pct = monthly[monthly['month'].isin(season_months)]['count'].sum() / monthly['count'].sum()
non_season_pct = 1 - season_pct
print(f'  시즌 월(2,3,5,11,12) 전환 집중도: {season_pct:.1%}  /  비시즌: {non_season_pct:.1%}')
print(f'  → 시즌 월 5개(41.7% 기간)에서 전환의 {season_pct:.1%} 발생 — 기대값 대비 {"높음 (occasion 가설 지지)" if season_pct > 0.417 else "낮음"}')

# --- 8-4. 미전환 수신 유저 — "아직 계기가 없는 것" 분석 ---
print('\n--- 8-4. 미전환 수신 유저 — 계기 대기 가설 ---')

non_conv = df_base[
    (df_base['received_count'] > 0) &
    (~df_base['is_true_viral']) &
    (df_base['first_received_at'].notna())
].copy()

analysis_end = pd.Timestamp('2024-12-31')
non_conv['days_since_recv'] = (analysis_end - non_conv['first_received_at']).dt.days

bins = [0, 30, 90, 180, 365, 730, 9999]
labels_b = ['< 1개월', '1~3개월', '3~6개월', '6~12개월', '1~2년', '2년+']
non_conv['wait_bucket'] = pd.cut(non_conv['days_since_recv'], bins=bins, labels=labels_b)
bucket_dist = non_conv['wait_bucket'].value_counts().sort_index()

print(f'  미전환 수신 유저 총계: {len(non_conv):,}명')
for bucket, cnt in bucket_dist.items():
    pct = cnt / len(non_conv)
    bar = '█' * int(pct * 50)
    print(f'  {str(bucket):10s}: {cnt:5,}명 ({pct:.1%}) {bar}')

recent3m = (bucket_dist.get('< 1개월', 0) + bucket_dist.get('1~3개월', 0))
long_wait = (bucket_dist.get('1~2년', 0) + bucket_dist.get('2년+', 0))
print(f'\n  최근 3개월 이내 수신 (계기 아직 없을 가능성): {recent3m:,}명 ({recent3m/len(non_conv):.1%})')
print(f'  1년+ 장기 미전환 (계기가 영원히 없거나 서비스 이탈): {long_wait:,}명 ({long_wait/len(non_conv):.1%})')
print('  → 해석: 장기 미전환 유저가 많다면 단순 시간 경과로는 전환 불가 — occasion 트리거가 필요함을 시사')

# ── 결과 요약 저장 (Notion 업데이트용) ──
print('\n' + '─'*60)
print('Section 8 핵심 수치 요약')
print('─'*60)
print(f'  [8-1] 수신 횟수 vs 전환율 Pearson r: {r_val:.3f}  (p={p_corr:.4f})')
print(f'  [8-2] 바이럴 첫 발신 special 비율: {viral_cat.get("special", 0):.1%}  '
      f'/ 오가닉: {organic_cat.get("special", 0):.1%}')
print(f'        Chi-square p={p_chi:.4f}')
print(f'  [8-3] 시즌 월 전환 집중도: {season_pct:.1%} (비시즌 {non_season_pct:.1%})')
print(f'        최다 전환 월: {peak_month}월')
print(f'  [8-4] 최근 3개월 미전환: {recent3m/len(non_conv):.1%} / 1년+ 장기 미전환: {long_wait/len(non_conv):.1%}')

print('\n' + '='*60)
print('Phase 4 분석 완료!')
print('='*60)
