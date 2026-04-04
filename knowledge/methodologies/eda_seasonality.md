---
title: "Layer 1 — EDA & 시즌 분석 (Seasonality Analysis)"
date: 2026-04-04
tags: [eda, seasonality, stl, time-series]
---

# EDA & 시즌 분석

## 핵심 질문
카카오톡 선물하기의 GMV는 명확한 계절성(seasonality)을 보이는가?
어떤 시점에서 피크가 나타나는가?

## 선택 방법론
**STL (Seasonal-Trend decomposition using LOESS)** + **Event-based Manual Labeling**

## 수학적 기초

### STL 분해 모형
```
Y(t) = Trend(t) × Seasonal(t) × Residual(t)  [승법성]
또는
Y(t) = Trend(t) + Seasonal(t) + Residual(t)  [가법성]
```

**선택 이유:** 카카오톡은 승법성 (시즌 변동폭이 trend level에 비례)

### LOESS 평활화
- Trend: robust LOESS with bandwidth ≈ 150% of seasonal period
- Seasonal: LOESS fit of detrended series
- Residual: Y - Trend - Seasonal

## 구현 코드 (Python)

```python
from statsmodels.tsa.seasonal import STL
import pandas as pd
import matplotlib.pyplot as plt

# 1. 데이터 로드 및 전처리
daily_gmv = pd.read_csv('daily_gmv.csv', parse_dates=['date'])
daily_gmv = daily_gmv.set_index('date').sort_index()

# 2. STL 분해
stl = STL(
    daily_gmv['gmv'],
    seasonal=365,           # 연간 주기
    trend=int(365 * 1.5),  # trend 평활 윈도우
    robust=True             # 이상치 강건성
)

result = stl.fit()

# 3. 결과 추출
trend = result.trend
seasonal = result.seasonal
residual = result.resid

# 4. 시각화
fig, axes = plt.subplots(4, 1, figsize=(12, 10))

daily_gmv.plot(ax=axes[0], title='Original')
trend.plot(ax=axes[1], title='Trend')
seasonal.plot(ax=axes[2], title='Seasonal')
residual.plot(ax=axes[3], title='Residual')

plt.tight_layout()
plt.show()
```

## 검증 방법

### 1. ACF (Autocorrelation Function) 검사
```python
from statsmodels.graphics.tsaplots import plot_acf

# Residual의 자기상관 검사
plot_acf(residual, lags=30)
# Lag-1 < 0.2이면 good
```

### 2. 시계열 피크 탐지
```python
from scipy.signal import find_peaks

# Seasonal component에서 피크 찾기
peaks, properties = find_peaks(seasonal.values, distance=30)

# 실제 이벤트 달력과 비교
event_dates = {
    'pepero_day': pd.Timestamp('2024-11-11'),
    'seollal': pd.Timestamp('2024-02-10'),
    'parents_day': pd.Timestamp('2024-05-08'),
    'chuseok': pd.Timestamp('2024-09-18')
}

for event_name, event_date in event_dates.items():
    # seasonal 피크가 event_date ± 3일 내에 있는가?
    pass
```

### 3. Variance 분해
```python
total_var = daily_gmv['gmv'].var()
seasonal_var = seasonal.var()
trend_var = trend.var()
residual_var = residual.var()

seasonal_ratio = seasonal_var / total_var
print(f"Seasonal accounts for {seasonal_ratio:.1%} of variance")
# >= 20% 이면 seasonality 유의미
```

## 주의사항

1. **Period 설정 중요**
   - Day-level: period=365 또는 52 (선택)
   - Week-level: period=52
   - 잘못된 period → 분해 실패

2. **robust=True 권장**
   - 이상치(서버 다운, 이벤트) 처리
   - False면 이상치에 과민반응

3. **분석 기간 충분성**
   - 최소 2개 주기 이상 필요 (2년)
   - 1년 데이터면 부족

## 참고 자료
- [statsmodels STL Documentation](https://www.statsmodels.org/generated/statsmodels.tsa.seasonal.STL.html)
- Cleveland et al. (1990). STL: A Seasonal-Trend Decomposition
