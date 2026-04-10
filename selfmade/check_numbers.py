# -*- coding: utf-8 -*-
import sys, pandas as pd, numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

logs = pd.read_csv('selfmade/campaign_logs.csv')
camps = pd.read_csv('selfmade/campaigns.csv')
orders = pd.read_csv('selfmade/orders.csv')

W = sys.stdout.buffer.write

W(b"=" * 60 + b"\n")
W("[1] 전체 퍼널 수치\n".encode('utf-8'))
W(b"=" * 60 + b"\n")
funnel = logs['event_type'].value_counts()
send = funnel.get('send', 0)
open_ = funnel.get('open', 0)
click = funnel.get('click', 0)
purchase = funnel.get('purchase', 0)
block = funnel.get('block', 0)
W(f"발송: {send:,}건  100%\n".encode('utf-8'))
W(f"오픈: {open_:,}건  {open_/send*100:.2f}%\n".encode('utf-8'))
W(f"클릭: {click:,}건  {click/send*100:.2f}% (발송기준), {click/open_*100:.2f}% (오픈기준)\n".encode('utf-8'))
W(f"구매: {purchase:,}건  {purchase/send*100:.2f}%\n".encode('utf-8'))
W(f"차단: {block:,}건  {block/send*100:.2f}%\n".encode('utf-8'))

W(b"\n" + b"=" * 60 + b"\n")
W("[2] A/B 테스트: Ranking vs Curation\n".encode('utf-8'))
W(b"=" * 60 + b"\n")

logs_m = logs.merge(camps[['campaign_id','message_type']], on='campaign_id', how='left', suffixes=('_log','_camp'))
# logs에 message_type 컬럼 있으면 _camp 붙음, 없으면 그냥 message_type
mt_col = 'message_type_camp' if 'message_type_camp' in logs_m.columns else 'message_type'
ab = logs_m[logs_m[mt_col].isin(['ranking','curation'])]
pivot = ab.groupby([mt_col,'event_type']).size().unstack(fill_value=0)
W(pivot.to_string().encode('utf-8') + b"\n\n")

for mt in ['ranking','curation']:
    row = pivot.loc[mt] if mt in pivot.index else None
    if row is None:
        continue
    s = row.get('send', 0)
    o = row.get('open', 0)
    c = row.get('click', 0)
    p = row.get('purchase', 0)
    bl = row.get('block', 0)
    W(f"[{mt.upper()}]\n".encode('utf-8'))
    W(f"  발송: {s:,}\n".encode('utf-8'))
    W(f"  오픈율(발송기준):  {o/s*100:.2f}%\n".encode('utf-8'))
    W(f"  클릭율(발송기준):  {c/s*100:.2f}%\n".encode('utf-8'))
    W(f"  클릭율(오픈기준):  {c/o*100:.2f}%\n".encode('utf-8'))
    W(f"  구매CVR(발송기준): {p/s*100:.2f}%\n".encode('utf-8'))
    W(f"  구매CVR(클릭기준): {p/c*100:.2f}% (클릭→구매)\n".encode('utf-8'))
    W(f"  차단율(발송기준):  {bl/s*100:.2f}%\n\n".encode('utf-8'))

W(b"=" * 60 + b"\n")
W("[3] RFM 세그먼트 수치\n".encode('utf-8'))
W(b"=" * 60 + b"\n")

rfm = pd.read_csv('analysis/rfm_result.csv')
seg_counts = rfm['segment'].value_counts()
total_users = len(rfm)
W(f"총 유저: {total_users:,}\n".encode('utf-8'))
for seg, cnt in seg_counts.items():
    W(f"  {seg}: {cnt:,}명 ({cnt/total_users*100:.1f}%)\n".encode('utf-8'))

# GMV 기여도
rfm_orders = orders.merge(rfm[['sender_user_id','segment']], on='sender_user_id', how='left')
seg_gmv = rfm_orders.groupby('segment')['total_amount_krw'].sum()
total_gmv = rfm_orders['total_amount_krw'].sum()
W(f"\n총 GMV: ₩{total_gmv/1e8:.1f}억\n".encode('utf-8'))
top3 = ['Champions', "Can't Lose Them", 'Loyal Customers']
top3_users = rfm[rfm['segment'].isin(top3)]['sender_user_id'].nunique()
top3_gmv = rfm_orders[rfm_orders['segment'].isin(top3)]['total_amount_krw'].sum()
W(f"상위3개 세그먼트 유저: {top3_users:,}명 ({top3_users/total_users*100:.1f}%)\n".encode('utf-8'))
W(f"상위3개 세그먼트 GMV: ₩{top3_gmv/1e8:.1f}억 ({top3_gmv/total_gmv*100:.1f}%)\n".encode('utf-8'))

W(b"\n")
for seg in top3:
    gmv = seg_gmv.get(seg, 0)
    cnt = seg_counts.get(seg, 0)
    W(f"  {seg}: {cnt:,}명 ({cnt/total_users*100:.1f}%), GMV {gmv/total_gmv*100:.1f}%\n".encode('utf-8'))

W(b"=" * 60 + b"\n")
W("[4] GMV 수치\n".encode('utf-8'))
W(b"=" * 60 + b"\n")

orders['year'] = pd.to_datetime(orders['created_at']).dt.year
gmv_by_year = orders.groupby('year')['total_amount_krw'].sum()
orders_by_year = orders.groupby('year').size()
for yr in [2023, 2024]:
    g = gmv_by_year.get(yr, 0)
    o = orders_by_year.get(yr, 0)
    W(f"{yr}: GMV ₩{g/1e8:.1f}억, 주문 {o:,}건\n".encode('utf-8'))
yoy = (gmv_by_year.get(2024,0) - gmv_by_year.get(2023,0)) / gmv_by_year.get(2023,1) * 100
W(f"YoY: +{yoy:.1f}%\n".encode('utf-8'))

W(b"=" * 60 + b"\n")
W("[5] K-factor 수치\n".encode('utf-8'))
W(b"=" * 60 + b"\n")

receipts = pd.read_csv('selfmade/gift_receipts.csv')
W(f"총 수신 건수: {len(receipts):,}\n".encode('utf-8'))
# 바이럴 전환: 수신자 중 나중에 발신자가 된 유저
receivers = set(receipts['receiver_user_id'].unique())
senders = set(orders['sender_user_id'].unique())
viral_users = receivers & senders
W(f"수신자 수: {len(receivers):,}\n".encode('utf-8'))
W(f"발신자도 된 수신자(바이럴 전환): {len(viral_users):,}명 ({len(viral_users)/len(receivers)*100:.1f}%)\n".encode('utf-8'))

# K-factor = avg invites * conversion rate
# avg_invites: 발신자 1명당 평균 수신자 수
avg_invites = orders.groupby('sender_user_id').size().mean()
cvr_viral = len(viral_users) / len(receivers)
kfactor = avg_invites * cvr_viral
W(f"평균 발송수(1인당): {avg_invites:.3f}\n".encode('utf-8'))
W(f"전환율(수신→발신): {cvr_viral*100:.1f}%\n".encode('utf-8'))
W(f"K-factor: {kfactor:.3f}\n".encode('utf-8'))

W(b"=" * 60 + b"\n")
W("[6] ROAS 수치 검증\n".encode('utf-8'))
W(b"=" * 60 + b"\n")

base_cvr = 0.0062
cvr_map = {
    'Champions': base_cvr * 1.9,
    "Can't Lose Them": base_cvr * 1.6,
    'Loyal Customers': base_cvr * 1.5,
    'Potential Loyalists': base_cvr * 1.2,
    'New Customers': base_cvr * 1.0,
    'Casual': base_cvr * 0.9,
    'At Risk': base_cvr * 0.7,
    'Dormant': base_cvr * 0.5,
}
kf = 1.559
rfm_aov = orders.merge(rfm[['sender_user_id','segment']], on='sender_user_id', how='left')
seg_aov_map = rfm_aov.groupby('segment')['total_amount_krw'].mean().to_dict()
overall_aov = orders['total_amount_krw'].mean()

rfm_sum = rfm.groupby('segment').agg(user_count=('sender_user_id','count')).reset_index()
rfm_sum['aov'] = rfm_sum['segment'].apply(lambda s: seg_aov_map.get(s, overall_aov))
rfm_sum['cvr'] = rfm_sum['segment'].apply(lambda s: cvr_map.get(s, base_cvr))

for cost in [10, 15, 20]:
    rfm_sum[f'roas_{cost}'] = (rfm_sum['user_count'] * rfm_sum['cvr'] * rfm_sum['aov'] * kf) / (rfm_sum['user_count'] * cost)

W(rfm_sum[['segment','user_count','aov','cvr','roas_10','roas_15','roas_20']].sort_values('roas_15', ascending=False).to_string(index=False).encode('utf-8') + b"\n")

for cost in [10, 15, 20]:
    total_cost = (rfm_sum['user_count'] * cost).sum()
    total_rev = (rfm_sum['user_count'] * rfm_sum['cvr'] * rfm_sum['aov'] * kf).sum()
    W(f"전체 ROAS({cost}원/건): {total_rev/total_cost:.1f}x\n".encode('utf-8'))
