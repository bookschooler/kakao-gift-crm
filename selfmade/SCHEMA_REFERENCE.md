# 실무 CRM/RFM 스키마 설계 레퍼런스

> 작성일: 2026-04-03
> 목적: 카카오 선물하기 포트폴리오 스키마 설계를 위한 실무 참고 자료

---

## 1. 오픈소스 레퍼런스 요약

| 레퍼런스 | 특징 | 우리 프로젝트에 쓸 것 |
|---|---|---|
| **fivetran/dbt_shopify** | 실전 e-커머스 스키마, customers+orders+line_items | orders 테이블 컬럼 구조 |
| **Braze Currents** | CRM 메시지 send/open/click/block 이벤트 로그 | campaign_logs 테이블 구조 |
| **Klaviyo Data Model** | Profile + Metric + Event 3요소, JSON properties | crm_events 설계 |
| **Snowplow Ecommerce dbt** | 이벤트 스트림 → 트랜잭션 집계 패턴 | 퍼널 분석 쿼리 패턴 |
| **Rittman Analytics RFM** | dbt + BigQuery RFM 마트 실제 구현 | RFM 스코어링 SQL |

---

## 2. 선물하기 고유 스키마 설계 원칙

### 2-1. 일반 e-커머스 vs 선물하기 핵심 차이

| 항목 | 일반 e-커머스 | 선물하기 |
|---|---|---|
| 구매자 = 수령자 | ✅ 동일 | ❌ 발신자 ≠ 수신자 |
| 결제 완료 = 배송 시작 | ✅ | ❌ 수신자 수락 후 배송 |
| 바이럴 루프 | 없음 | 수신자 → 발신자 전환 추적 필요 |
| 시즌성 분석 | MoM으로 충분 | YoY 필수 (연 1회 이벤트) |
| 이탈 지표 | 장바구니 이탈 | 선물 미수락/만료 + 채널 차단 |

### 2-2. Braze Currents 기반 CRM 이벤트 로그 표준 컬럼

```
event_id              -- 이벤트 고유 ID (UUID)
user_id               -- 플랫폼 user ID
campaign_id           -- 캠페인 ID
campaign_name
message_variation_id  -- A/B 테스트 variant ID
dispatch_id           -- 동일 배치 발송 그룹핑 키
event_type            -- 'send' / 'open' / 'click' / 'block' / 'purchase'
channel               -- 'kakao_channel' / 'in_app' / 'push'
platform              -- 'ios' / 'android'
occurred_at           -- 이벤트 발생 시각
```

### 2-3. 바이럴 루프 추적 핵심 컬럼

수신자 → 발신자 전환을 추적하려면 반드시 필요:

```sql
-- gift_receipts 테이블
receipt_id            -- PK
order_id              -- FK → orders.order_id
receiver_user_id      -- 수신자 user_id (카카오 계정 연동 시)
received_at           -- 수신자가 선물 수락한 시각
gift_occasion         -- 'birthday' / 'pepero_day' / 'parents_day' 등

-- users 테이블 추가 컬럼
first_received_at     -- 처음 선물 받은 날짜 (바이럴 전환 기산점)
total_received_count  -- 누적 수신 횟수 (4회 이상이면 구매 전환율 30%+)
is_viral_converted    -- 수신자→발신자 전환 여부
referral_generation   -- 0=오가닉, 1=1차 수신자전환, 2=2차...
```

---

## 3. dbt 레이어 컨벤션 (실무 표준)

```
models/
├── staging/          # stg_* : source 1:1, 컬럼 rename/type cast만
│   ├── stg_kakao_gift__users.sql
│   ├── stg_kakao_gift__orders.sql
│   ├── stg_kakao_gift__gift_receipts.sql
│   └── stg_kakao_gift__campaign_logs.sql
│
├── intermediate/     # int_* : 비즈니스 로직 단위 집계, 재사용 목적
│   ├── int_users__rfm_inputs.sql        -- user별 R/F/M 원값
│   ├── int_orders__gift_journey.sql     -- 수신자→발신자 전환 연결
│   └── int_crm__campaign_funnel.sql     -- send→open→click→purchase
│
└── marts/
    ├── mart_rfm_segments.sql            -- RFM 스코어 + 세그먼트 레이블
    ├── mart_ltv_cohort.sql              -- 월별 코호트 × 누적 LTV
    ├── mart_viral_loop.sql              -- 수신 횟수별 전환율
    ├── mart_campaign_performance.sql    -- CTR/CVR/block_rate/ROAS
    └── mart_seasonal_yoy.sql            -- 시즌 이벤트 YoY 비교
```

> 참고: 포트폴리오에서 dbt를 실제로 돌리지 않더라도,
> 이 레이어 구조로 SQL 파일을 분리해두면 "실무 데이터 모델링 이해"를 어필 가능.

---

## 4. RFM 스코어링 SQL 패턴 (BigQuery)

```sql
-- int_users__rfm_inputs.sql
WITH base AS (
    SELECT
        sender_user_id AS user_id,
        DATE_DIFF(CURRENT_DATE(), MAX(DATE(created_at)), DAY) AS days_since_last_order,
        COUNT(DISTINCT order_id)                               AS order_count_12m,
        SUM(total_amount)                                      AS gmv_12m
    FROM stg_kakao_gift__orders
    WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
      AND order_status = 'accepted'
    GROUP BY 1
)
SELECT
    user_id,
    days_since_last_order,
    order_count_12m,
    gmv_12m,
    NTILE(5) OVER (ORDER BY days_since_last_order ASC)  AS recency_score,
    NTILE(5) OVER (ORDER BY order_count_12m DESC)       AS frequency_score,
    NTILE(5) OVER (ORDER BY gmv_12m DESC)               AS monetary_score
FROM base
```

```sql
-- 세그먼트 매핑 (mart_rfm_segments.sql)
CASE
    WHEN recency_score >= 4 AND frequency_score >= 4                        THEN 'Champions'
    WHEN recency_score >= 3 AND frequency_score >= 3                        THEN 'Loyal Customers'
    WHEN recency_score >= 4 AND frequency_score <= 2                        THEN 'New Customers'
    WHEN recency_score >= 3 AND frequency_score <= 2                        THEN 'Potential Loyalists'
    WHEN recency_score = 3  AND frequency_score = 3                         THEN 'Need Attention'
    WHEN recency_score <= 2 AND frequency_score >= 4                        THEN 'At Risk'
    WHEN recency_score <= 2 AND frequency_score >= 2 AND monetary_score >= 3 THEN "Can't Lose Them"
    WHEN recency_score <= 2 AND frequency_score <= 2                        THEN 'Lost'
    ELSE 'Hibernating'
END AS rfm_segment
```

---

## Sources

- [fivetran/dbt_shopify (GitHub)](https://github.com/fivetran/dbt_shopify)
- [Braze Currents — Message Engagement Events](https://www.braze.com/docs/user_guide/data/distribution/braze_currents/event_glossary/message_engagement_events)
- [Klaviyo Developer — Data Model](https://developers.klaviyo.com/en/docs/introduction_to_klaviyos_data_model)
- [dbt — How We Structure Our Projects](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [Rittman Analytics — RFM with dbt + BigQuery](https://rittmananalytics.com/blog/2021/6/20/rfm-analysis-and-customer-segmentation-using-looker-dbt-and-google-bigquery)
- [GrabGifts Product Breakdown (Medium)](https://anirudhkannanvp.medium.com/decoding-grabgifts-product-breakdown-of-grab-a-technical-product-managers-comprehensive-d90d1cd1aa4f)
- [카카오 기술블로그 — 데이터 파이프라인](https://tech.kakao.com/2022/04/19/2022-kakao-tech-internship-data/)
