fig, ax1 = plt.subplots(figsize=(14, 6))

# cumsum 직전 SEGMENT_ORDER 기준 명시적 재정렬 (cell 실행 순서 무관하게 보장)
seg_stats = seg_stats.sort_values('order').reset_index(drop=True)

x      = np.arange(len(seg_stats))
colors = [colors_map.get(s, GRAY) for s in seg_stats['rfm_segment']]
bars   = ax1.bar(x, seg_stats['gmv_pct'], color=colors, alpha=0.85, edgecolor='white', width=0.6)

ax1.set_ylabel('GMV 기여 비중 (%)', fontsize=11)
ax1.set_xticks(x)
ax1.set_xticklabels(seg_stats['rfm_segment'], rotation=30, ha='right', fontsize=10)
ax1.set_ylim(0, seg_stats['gmv_pct'].max() * 1.3)

for bar, (_, row) in zip(bars, seg_stats.iterrows()):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
             f"{row['gmv_pct']:.1f}%", ha='center', va='bottom', fontsize=9)
    if row['gmv_pct'] > 3:
        label = '유저
' + f"{row['user_pct']:.1f}%"  # f-string literal newline 방지
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
                 label, ha='center', va='center',
                 fontsize=8, color='white', fontweight='bold')

# 누적 GMV 선 (첫 점이 Champions GMV와 일치하도록 정렬 후 cumsum)
ax2 = ax1.twinx()
cumulative = seg_stats['gmv_pct'].cumsum()
ax2.plot(x, cumulative, color=RED, linewidth=2, marker='o', markersize=5,
         label='누적 GMV %')
ax2.axhline(80, color=RED, linestyle='--', linewidth=1, alpha=0.5,
            label='80% 기준선')
ax2.set_ylabel('누적 GMV (%)', fontsize=11)
ax2.set_ylim(0, 115)
ax2.text(len(seg_stats)-1, 82, '80% 기준선', fontsize=9, color=RED)
ax2.legend(loc='upper left', fontsize=9)

ax1.set_title('세그먼트별 GMV 기여도 및 Pareto 검증', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('charts/rfm_gmv_pareto.png', dpi=150, bbox_inches='tight')
plt.show()

# 핵심 수치 — 세그먼트별 개별 출력
print('=== Pareto 검증: 세그먼트별 GMV 기여 ===')
cumulative_gmv = 0
for _, row in seg_stats.iterrows():
    cumulative_gmv += row['gmv_pct']
    print(f'{row["rfm_segment"]:<20} GMV {row["gmv_pct"]:>5.1f}%  (누적 {cumulative_gmv:.1f}%)')
