"""
슬라이드 7용 — 발신 빈도별 유저 세그먼트 차트 생성
layer1_send_frequency.png 으로 저장
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Malgun Gothic'  # Windows 한글 폰트
matplotlib.rcParams['axes.unicode_minus'] = False
from google.cloud import bigquery

client = bigquery.Client(project="ds-ysy")

def bq(sql):
    return client.query(sql).to_dataframe()

# 발신 빈도별 세그먼트 집계
route_analysis = bq("""
SELECT
  o.sender_user_id,
  COUNT(DISTINCT r.receiver_user_id) AS receiver_cnt,
  COUNT(o.order_id)                  AS send_cnt
FROM `ds-ysy.kakao_gift.orders` o
JOIN `ds-ysy.kakao_gift.gift_receipts` r ON o.order_id = r.order_id
WHERE o.order_status != 'refunded'
GROUP BY 1
""")

route_analysis['send_segment'] = pd.cut(
    route_analysis['send_cnt'],
    bins=[0, 1, 3, 7, 999],
    labels=['이탈형\n(1회)', '일반형\n(2~3회)', '충성형\n(4~7회)', '헤비유저\n(8회+)']
)

seg_dist = route_analysis.groupby('send_segment', observed=True).agg(
    user_cnt=('sender_user_id', 'count'),
    avg_receivers=('receiver_cnt', 'mean')
).reset_index()

seg_dist['user_pct'] = seg_dist['user_cnt'] / seg_dist['user_cnt'].sum() * 100

# ── 차트 ──────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(8, 10))
fig.suptitle('발신 빈도별 유저 세그먼트', fontsize=16, fontweight='bold')

colors = ['#AAAAAA', '#1A56DB', '#FFE812', '#C81E1E']

# 왼쪽: 유저 비중 막대
bars = axes[0].bar(seg_dist['send_segment'], seg_dist['user_pct'], color=colors, edgecolor='white', linewidth=1.5)
axes[0].set_title('세그먼트별 유저 비중 (%)', fontsize=13)
axes[0].set_ylabel('유저 비중 (%)')
axes[0].set_ylim(0, seg_dist['user_pct'].max() * 1.2)
for bar, pct in zip(bars, seg_dist['user_pct']):
    axes[0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f'{pct:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

# 오른쪽: 평균 수신자 수 막대
bars2 = axes[1].bar(seg_dist['send_segment'], seg_dist['avg_receivers'], color=colors, edgecolor='white', linewidth=1.5)
axes[1].set_title('세그먼트별 평균 수신자 수 (명)', fontsize=13)
axes[1].set_ylabel('평균 수신자 수')
axes[1].set_ylim(0, seg_dist['avg_receivers'].max() * 1.2)
for bar, val in zip(bars2, seg_dist['avg_receivers']):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f'{val:.2f}명', ha='center', va='bottom', fontsize=11, fontweight='bold')

plt.tight_layout()
out_path = 'selfmade/ppt_charts/layer1_send_frequency.png'
plt.savefig(out_path, dpi=150, bbox_inches='tight')
print(f'저장 완료: {out_path}')
plt.show()
