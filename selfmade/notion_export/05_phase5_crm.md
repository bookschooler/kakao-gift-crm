# Phase 5 — CRM 전략 수립

## 분석 목적
- Phase 1~4 인사이트를 실행 가능한 CRM 전략으로 전환
- A/B 테스트로 메시지 타입 최적화 (ranking vs curation)
- ROAS 시뮬레이션으로 캠페인 경제성 입증
- 시즌/비시즌 캠페인 전략 차별화

---

## Section 0 — Phase 4 연결 포인트

Phase 4에서 도출된 핵심 인사이트가 Phase 5 전략의 입력값:
- K=1.559 → 바이럴 캠페인 ROI 계산 기준
- Golden Time 30일 → 수신 후 캠페인 타이밍
- Occasion 트리거 → 메시지 개인화 방향

---

## Section 1 — 캠페인 퍼널 분석

### 전체 캠페인 성과

| 단계 | 수치 |
|------|------|
| 발송 수 | 전체 타겟 사용자 |
| Open Rate | **53.68%** |
| Click Rate (CTR) | 추적됨 |
| Conversion Rate (CVR) | **0.53%** |

> Open Rate 53.68%는 업계 평균(~20%)의 2.5배 — 카카오톡 플랫폼 내 메시지라 열람율 자체가 높음

---

## Section 2 — A/B 테스트 설계 및 결과

### 테스트 설계
- **A그룹 (Ranking)**: 인기 상품 순위 기반 추천
- **B그룹 (Curation)**: RFM 세그먼트 기반 개인화 큐레이션

### 통계 검정
- 검정 방법: Chi-squared test (카이제곱 검정)
- χ² = **2002.6**
- p-value = **< 0.0001** (통계적으로 매우 유의미)

### 결과

| 그룹 | 지표 | 수치 |
|------|------|------|
| Ranking (A) | CTR | **15.16%** |
| Curation (B) | CVR | **12.73%** |

### 해석
- **Ranking이 CTR 우세**: 인기 상품은 클릭을 더 많이 유도
- **Curation이 CVR 우세**: 개인화 추천은 실제 구매로 더 잘 연결
- 전략: CTR 목표 → Ranking / CVR·매출 목표 → Curation

---

## Section 3 — 시즌 vs 비시즌 캠페인 비교

| 구분 | 시즌 캠페인 | 비시즌 캠페인 |
|------|------------|--------------|
| 목표 | 대량 발송, 고 Open Rate | 개인화, 고 CVR |
| 메시지 타입 | Ranking (인기 상품) | Curation (맞춤 추천) |
| 타이밍 | 이벤트 D-7 ~ D-1 | Golden Time (수신 후 30일) |
| 기대 효과 | 광범위 도달 | 전환율 극대화 |

---

## Section 4 — ROAS 시뮬레이션

### 세그먼트별 ROAS

| 세그먼트 | ROAS | 특징 |
|----------|------|------|
| **Champions** | **2,595배** | 최고 ROI |
| Loyal Customers | 890배 | 높은 ROI |
| At Risk | 340배 | 재활성화 가치 |
| 전체 평균 | 137배 | 3종 캠페인 기준 |

### 총 캠페인 성과
| 지표 | 값 |
|------|-----|
| 총 캠페인 GMV | **₩6.02억** |
| 3종 캠페인 ROAS | **137배** |
| 캠페인 비용 | ₩1.23억 (추정) |

---

## Section 5 — ROAS 감도 분석

ROAS 민감도 시뮬레이션 (Reviewer 지적 반영):
- **낙관적 시나리오** (+20% CVR): ROAS 165배
- **기본 시나리오**: ROAS 137배
- **보수적 시나리오** (-20% CVR): ROAS 110배

> 어떤 시나리오에서도 ROAS > 100배 — 캠페인 경제성 강건(Robust)

---

## Section 6 — CRM 액션 플랜

### 3종 CRM 캠페인 구성

| 캠페인 | 타겟 | 메시지 | 타이밍 |
|--------|------|--------|--------|
| **VIP 로열티** | Champions | "당신만을 위한 얼리 액세스" | 상시 |
| **재활성화** | At Risk / Can't Lose Them | "오랫동안 뵙지 못했어요" + 쿠폰 | 마지막 구매 D+60 |
| **Occasion 트리거** | 전 세그먼트 | 생일/기념일 맞춤 | D-30 |

### 세그먼트 × 메시지 타입 매트릭스

|  | Ranking | Curation | 할인 쿠폰 |
|--|---------|----------|---------|
| Champions | ✗ | ✓ (최고급 큐레이션) | ✗ (할인 불필요) |
| At Risk | ✗ | ✓ | ✓ (재활성화) |
| Recent Customers | ✓ | ✗ | ✗ |
| Potential Loyalists | ✓ | ✓ | △ |

---

## Section 7 — 다음 단계 제언

1. **실시간 Occasion 감지 파이프라인 구축**
   - 생일 D-30 자동 트리거 시스템
   - 수신 후 D+7, D+14, D+30 자동 넛지

2. **세그먼트 자동 업데이트**
   - 월 1회 RFM 재계산 → 세그먼트 자동 갱신
   - Champions 이탈 감지 알럿

3. **A/B 테스트 고도화**
   - 현재: Ranking vs Curation (이분법)
   - 다음: Hybrid (CTR 목적 Ranking + CVR 목적 Curation) 멀티암 테스트

4. **LTV 기반 CAC 상한선 설정**
   - M+11 LTV ₩203,169 기준
   - 세그먼트별 허용 CAC 차등화

---

## DESA vs Selfmade 비교

| 항목 | DESA | Selfmade |
|------|------|----------|
| A/B 테스트 검정 | 기술통계 | χ²=2002.6, p<0.0001 |
| ROAS 분석 | 단일값 | 감도 분석 포함 |
| 세그먼트 연결 | 부분적 | Phase 2 RFM 완전 연결 |
| 액션 플랜 | 3줄 요약 | 세그먼트×메시지 매트릭스 |

---

## 분석 파일
- `selfmade/analysis/05_crm_strategy.py`
- 생성 차트: `charts/layer5_campaign_funnel.png`, `layer5_roas_simulation.png`, `layer5_roas_sensitivity.png`, `layer5_seasonal_vs_normal.png`, `layer5_cost_vs_revenue.png`