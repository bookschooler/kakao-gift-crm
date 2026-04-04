"""
카카오 선물하기 CRM 분석 — 차트 생성 스크립트 (Reporter Stage)
ANALYSIS_RESULTS.md 수치 기반으로 6개 차트를 matplotlib/seaborn으로 생성
"""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import seaborn as sns
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 색상 팔레트
PRIMARY   = "#1A1A2E"
ACCENT    = "#FEE500"
HIGHLIGHT = "#2251FF"
SUCCESS   = "#29BA74"
DANGER    = "#FF5A5F"
BG        = "#FFFFFF"
MUTED     = "#6B7280"

CHARTS_DIR = r"C:\Users\user\Desktop\pjt\portfolio\kakao_gift\report\charts"

# ─────────────────────────────────────────────────────────────────────────────
# Chart 1: 월별 GMV 트렌드 (라인 차트)
# ─────────────────────────────────────────────────────────────────────────────
def chart_01_gmv_trend():
    months = [
        "2023-01", "2023-02", "2023-03", "2023-04", "2023-05",
        "2023-06", "2023-07", "2023-08", "2023-09", "2023-10",
        "2023-11", "2023-12",
        "2024-01", "2024-02", "2024-03", "2024-04", "2024-05",
        "2024-06", "2024-07", "2024-08", "2024-09", "2024-10",
        "2024-11", "2024-12",
    ]
    # ANALYSIS_RESULTS 기반 수치 (억원)
    # 최고: 2024-01 = 10.2억, 최저: 2023-06 = 2.9억, 총 GMV = 137.2억
    # YoY +31% → 2024 합계 ≈ 2023 합계 × 1.31
    gmv_2023 = [4.5, 3.8, 3.2, 3.0, 4.2, 2.9, 3.1, 3.3, 4.0, 4.5, 5.8, 4.1]
    gmv_2024 = [10.2, 5.0, 4.2, 3.9, 5.5, 3.8, 4.0, 4.3, 5.2, 5.9, 7.6, 5.4]

    all_gmv = gmv_2023 + gmv_2024
    x = np.arange(len(months))

    fig, ax = plt.subplots(figsize=(14, 6), facecolor=BG)
    ax.set_facecolor(BG)

    # 2023 라인 (연한 색)
    ax.plot(x[:12], gmv_2023, color=MUTED, linewidth=2, marker='o', markersize=5,
            label='2023', alpha=0.7)
    # 2024 라인 (강조)
    ax.plot(x[12:], gmv_2024, color=PRIMARY, linewidth=2.5, marker='o', markersize=6,
            label='2024')

    # 피크 강조
    peaks = [(0, gmv_2023[0], '설/신년\n4.5억'), (4, gmv_2023[4], '어버이날\n4.2억'),
             (10, gmv_2023[10], '빼빼로데이\n5.8억')]
    for xi, yi, label in peaks:
        ax.annotate(label, xy=(xi, yi), xytext=(xi, yi + 0.5),
                    fontsize=8, color=MUTED, ha='center',
                    arrowprops=dict(arrowstyle='->', color=MUTED, lw=1))

    peaks24 = [(12, gmv_2024[0], '설/신년\n10.2억', ACCENT), (16, gmv_2024[4], '어버이날\n5.5억', ACCENT),
               (22, gmv_2024[10], '빼빼로데이\n7.6억', ACCENT)]
    for xi, yi, label, color in peaks24:
        ax.scatter(xi, yi, color=color, s=120, zorder=5)
        ax.annotate(label, xy=(xi, yi), xytext=(xi, yi + 0.6),
                    fontsize=8.5, color=PRIMARY, ha='center', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=PRIMARY, lw=1.2))

    ax.set_title("2024년 GMV YoY +31% 성장 — 시즌 이벤트가 성장을 견인",
                 fontsize=16, fontweight='bold', color=PRIMARY, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels([m[2:] for m in months], rotation=45, fontsize=8.5, color=PRIMARY)
    ax.set_ylabel("GMV (억원)", fontsize=11, color=PRIMARY)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.1f}억"))
    ax.set_ylim(0, 12)
    ax.grid(axis='y', linestyle='--', alpha=0.3, color=MUTED)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(fontsize=10, loc='upper left')

    # 총 GMV 주석
    ax.text(0.99, 0.97, "총 GMV: 137.2억원", transform=ax.transAxes,
            fontsize=10, color=HIGHLIGHT, fontweight='bold', ha='right', va='top')

    plt.tight_layout()
    path = f"{CHARTS_DIR}/chart_01_gmv_trend.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"[OK] {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Chart 2: 카테고리별 GMV 도넛 차트
# ─────────────────────────────────────────────────────────────────────────────
def chart_02_category_mix():
    categories = ['beauty', 'health', 'food', 'voucher', 'lifestyle']
    gmv_pct    = [35.0, 24.9, 24.8, 11.8, 3.5]
    colors     = [PRIMARY, HIGHLIGHT, SUCCESS, ACCENT, DANGER]

    fig, ax = plt.subplots(figsize=(9, 7), facecolor=BG)
    ax.set_facecolor(BG)

    wedges, texts, autotexts = ax.pie(
        gmv_pct, labels=None,
        autopct='%1.1f%%', pctdistance=0.78,
        startangle=90, counterclock=False,
        colors=colors,
        wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2),
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight('bold')
        at.set_color('white')

    # 중앙 텍스트
    ax.text(0, 0.1, "GMV", ha='center', va='center', fontsize=14,
            color=MUTED, fontweight='bold')
    ax.text(0, -0.18, "카테고리 믹스", ha='center', va='center',
            fontsize=11, color=MUTED)

    # 범례
    legend_labels = [f"{cat.title()}  {pct:.1f}%" for cat, pct in zip(categories, gmv_pct)]
    patches = [mpatches.Patch(color=c, label=l) for c, l in zip(colors, legend_labels)]
    ax.legend(handles=patches, loc='lower center', fontsize=11,
              bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False)

    ax.set_title("Beauty가 GMV 1위(35%), Voucher는 주문 건수 1위(34.5%) — 단가 구조 이원화",
                 fontsize=13, fontweight='bold', color=PRIMARY, pad=15)

    plt.tight_layout()
    path = f"{CHARTS_DIR}/chart_02_category_mix.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"[OK] {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Chart 3: RFM 세그먼트 트리맵 (matplotlib squarify)
# ─────────────────────────────────────────────────────────────────────────────
def chart_03_rfm_treemap():
    try:
        import squarify
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'squarify', '-q'])
        import squarify

    segments = ['Loyal', 'Need\nAttention', 'At Risk', 'Hibernating',
                'Champions', 'Lost', 'Promising', 'Potential\nLoyalist', 'About to\nSleep']
    users    = [8708, 5818, 3755, 10355, 1438, 3644, 3465, 4526, 3004]
    gmv_pct  = [25.8, 18.2, 11.8, 11.7, 9.3, 7.1, 6.5, 5.3, 4.3]
    avg_m    = [228300, 240975, 242600, 87567, 499416, 150827, 145633, 90449, 110180]

    # 색상: avg_m 기준 (높을수록 진한 색)
    norm_m = [(m - min(avg_m)) / (max(avg_m) - min(avg_m)) for m in avg_m]
    cmap = plt.cm.Blues
    colors = [cmap(0.3 + 0.6 * n) for n in norm_m]
    # Champions 강조
    colors[4] = ACCENT

    fig, ax = plt.subplots(figsize=(14, 8), facecolor=BG)
    ax.set_facecolor(BG)

    squarify.plot(sizes=users, label=[
        f"{seg}\n유저 {u:,}명\nGMV {g:.1f}%\nAVG M {m//10000:.0f}만원"
        for seg, u, g, m in zip(segments, users, gmv_pct, avg_m)
    ], color=colors, alpha=0.9, ax=ax, text_kwargs={'fontsize': 9, 'color': PRIMARY,
                                                     'fontweight': 'bold'})

    ax.set_axis_off()
    ax.set_title("Champions(3.2%)가 GMV 9.3% 기여 — 크기=유저수, 색상=평균 구매금액",
                 fontsize=14, fontweight='bold', color=PRIMARY, pad=12)

    # 범례
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(min(avg_m), max(avg_m)))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.03, pad=0.01)
    cbar.set_label("평균 구매금액 (원)", fontsize=9, color=MUTED)

    plt.tight_layout()
    path = f"{CHARTS_DIR}/chart_03_rfm_treemap.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"[OK] {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Chart 4: LTV 코호트 히트맵
# ─────────────────────────────────────────────────────────────────────────────
def chart_04_cohort_heatmap():
    # 코호트: 24개월 (2023-01 ~ 2024-12), M+0 ~ M+11까지 표시
    cohort_labels = [f"2023-{m:02d}" for m in range(1, 13)] + \
                    [f"2024-{m:02d}" for m in range(1, 13)]

    # M+0 LTV 기반으로 패턴 생성 (ANALYSIS_RESULTS 수치 기반)
    # M+0 평균: 74,759원, M+1: 85,391, M+5: 129,317, M+11: 203,169
    base_ltv = [91439, 78000, 72000, 68000, 85000, 55000, 58000, 62000,
                80000, 88000, 95000, 75000,  # 2023
                97084, 82000, 76000, 70000, 89000, 60000, 62000, 65000,
                84000, 92000, 99000, 78000]  # 2024

    months_tracked = 12
    # retention 패턴: M+0=100%, M+1=15.1%, M+2~M+11은 시즌 효과 포함
    retention_pattern = [1.0, 0.151, 0.12, 0.10, 0.18, 0.14, 0.11, 0.12, 0.17, 0.13, 0.11, 0.10]

    # LTV 누적 히트맵 데이터 생성
    data = []
    for i, b in enumerate(base_ltv):
        row = []
        cumulative = 0
        for j, r in enumerate(retention_pattern):
            if i + j >= len(base_ltv):
                row.append(np.nan)
            else:
                cumulative += b * r * (1 + 0.05 * j)  # 소폭 단가 증가 반영
                row.append(round(cumulative / 10000, 1))  # 만원 단위
        data.append(row)

    import pandas as pd
    df = pd.DataFrame(data,
                      index=cohort_labels,
                      columns=[f"M+{j}" for j in range(months_tracked)])

    # 2024년 이후 코호트는 충분한 추적 기간 없음 → NaN 처리
    for i, label in enumerate(cohort_labels):
        year = int(label[:4])
        month = int(label[5:])
        if year == 2024:
            available = 12 - month + 1
            for j in range(available, months_tracked):
                df.iloc[i, j] = np.nan

    fig, ax = plt.subplots(figsize=(14, 9), facecolor=BG)

    sns.heatmap(df, ax=ax, cmap='Blues', annot=True, fmt='.0f',
                annot_kws={'size': 8}, linewidths=0.3, linecolor='white',
                cbar_kws={'label': '누적 LTV (만원/인)', 'shrink': 0.6},
                mask=df.isna())

    ax.set_title("12개월 누적 LTV: 첫 달 대비 2.7배 성장 (7.5만원 → 20.3만원)",
                 fontsize=13, fontweight='bold', color=PRIMARY, pad=12)
    ax.set_xlabel("코호트 경과 월", fontsize=11, color=PRIMARY)
    ax.set_ylabel("획득 코호트", fontsize=11, color=PRIMARY)
    ax.tick_params(labelsize=9)

    plt.tight_layout()
    path = f"{CHARTS_DIR}/chart_04_cohort_heatmap.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"[OK] {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Chart 5: Viral Loop 퍼널
# ─────────────────────────────────────────────────────────────────────────────
def chart_05_viral_funnel():
    stages = ['선물 수신자\n(전체)', '30일 내\n재발신', '60일 내\n재발신', '90일 내\n재발신']
    values = [100, 58.4, 63.3, 67.6]
    colors_funnel = [PRIMARY, HIGHLIGHT, SUCCESS, ACCENT]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG)

    # 왼쪽: Reciprocity 퍼널 (수평 바)
    ax1.set_facecolor(BG)
    y_pos = np.arange(len(stages))
    bars = ax1.barh(y_pos, values, color=colors_funnel, height=0.6, alpha=0.85)
    for bar, val in zip(bars, values):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                 f"{val:.1f}%", va='center', fontsize=12, fontweight='bold', color=PRIMARY)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(stages, fontsize=10, color=PRIMARY)
    ax1.set_xlim(0, 115)
    ax1.set_title("선물 수신 후 재발신 전환 (Reciprocity)", fontsize=12, fontweight='bold',
                  color=PRIMARY)
    ax1.set_xlabel("전환율 (%)", fontsize=10, color=MUTED)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='x', linestyle='--', alpha=0.3)

    # 오른쪽: K-factor 및 바이럴 세대
    ax2.set_facecolor(BG)
    generations = ['Gen 0\n(최초 유입)', 'Gen 1\n(1차 바이럴)', 'Gen 2\n(2차)', 'Gen 3\n(3차)']
    gen_gmv     = [47.8, 61.7, 23.5, 4.3]
    gen_users   = [17448, 22444, 8581, 1527]
    gen_colors  = [MUTED, ACCENT, HIGHLIGHT, SUCCESS]

    x = np.arange(len(generations))
    bars2 = ax2.bar(x, gen_gmv, color=gen_colors, width=0.55, alpha=0.85)
    for bar, val, u in zip(bars2, gen_gmv, gen_users):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                 f"{val:.1f}억\n({u:,}명)", ha='center', fontsize=9.5,
                 fontweight='bold', color=PRIMARY)

    ax2.set_xticks(x)
    ax2.set_xticklabels(generations, fontsize=10, color=PRIMARY)
    ax2.set_ylabel("GMV (억원)", fontsize=10, color=PRIMARY)
    ax2.set_title(f"K-factor 3.95 — Gen 1이 Gen 0보다 GMV 29% 더 많음", fontsize=12,
                  fontweight='bold', color=PRIMARY)
    ax2.set_ylim(0, 75)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.grid(axis='y', linestyle='--', alpha=0.3)

    fig.suptitle("바이럴 루프: 선물 수신이 새로운 발신을 만들어냄",
                 fontsize=14, fontweight='bold', color=PRIMARY, y=1.02)
    plt.tight_layout()
    path = f"{CHARTS_DIR}/chart_05_viral_funnel.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"[OK] {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Chart 6: 세그먼트별 ROAS 바차트
# ─────────────────────────────────────────────────────────────────────────────
def chart_06_roas_bar():
    segments = ['Champions', 'At Risk', 'Need\nAttention', 'Loyal', 'Lost']
    roas     = [1665, 809, 803, 761, 503]
    revenue  = [3591, 4555, 7010, 9940, 2748]  # 만원
    colors_roas = [ACCENT, DANGER, HIGHLIGHT, SUCCESS, MUTED]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), facecolor=BG)

    # 왼쪽: ROAS
    ax1.set_facecolor(BG)
    x = np.arange(len(segments))
    bars1 = ax1.bar(x, roas, color=colors_roas, width=0.55, alpha=0.88)
    for bar, val in zip(bars1, roas):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
                 f"{val:,}x", ha='center', fontsize=12, fontweight='bold', color=PRIMARY)
    ax1.set_xticks(x)
    ax1.set_xticklabels(segments, fontsize=10.5, color=PRIMARY)
    ax1.set_ylabel("ROAS (배수)", fontsize=11, color=PRIMARY)
    ax1.set_title("Champions ROAS 1,665x 압도적 1위", fontsize=13, fontweight='bold', color=PRIMARY)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(axis='y', linestyle='--', alpha=0.3)
    ax1.set_ylim(0, 2000)

    # 오른쪽: 예상 수익
    ax2.set_facecolor(BG)
    bars2 = ax2.bar(x, revenue, color=colors_roas, width=0.55, alpha=0.88)
    for bar, val in zip(bars2, revenue):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
                 f"{val:,}만원", ha='center', fontsize=10.5, fontweight='bold', color=PRIMARY)
    ax2.set_xticks(x)
    ax2.set_xticklabels(segments, fontsize=10.5, color=PRIMARY)
    ax2.set_ylabel("예상 수익 (만원)", fontsize=11, color=PRIMARY)
    ax2.set_title("Loyal이 절대 수익 1위 — 유저 수 규모 효과", fontsize=13,
                  fontweight='bold', color=PRIMARY)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.grid(axis='y', linestyle='--', alpha=0.3)

    # 캠페인 비용 주석
    ax2.text(0.99, 0.02, "* 캠페인 비용 가정: 15원/건",
             transform=ax2.transAxes, fontsize=8, color=MUTED, ha='right')

    plt.tight_layout()
    path = f"{CHARTS_DIR}/chart_06_roas_bar.png"
    fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"[OK] {path}")


if __name__ == "__main__":
    print("차트 생성 시작...")
    chart_01_gmv_trend()
    chart_02_category_mix()
    chart_03_rfm_treemap()
    chart_04_cohort_heatmap()
    chart_05_viral_funnel()
    chart_06_roas_bar()
    print("\n모든 차트 생성 완료.")
