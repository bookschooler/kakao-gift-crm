# 실무 빅데이터 툴 & BigQuery 과금 가이드

> 작성일: 2026-04-03
> 목적: 포트폴리오 프로젝트 설계를 위한 실무 참고 자료

---

## 1. 한국 주요 기업 데이터 도구 현황

### 1-1. 기업별 스택 요약

| 기업 | 클라우드 | 주요 DW/쿼리 엔진 | 특징 |
|---|---|---|---|
| **쿠팡** | AWS | Spark + Presto + S3 | 자체 데이터 레이크, Redshift → EMR 전환 |
| **네이버** | NAVER Cloud (자체) | Hadoop + Trino + Hive + Flink | 완전 자체 플랫폼, 외부 SaaS 미사용 |
| **카카오** | 자체 + GCP 일부 | Spark + Presto + 자체 스케줄러 | 자체 AI 인프라 병행 |
| **토스** | AWS | Kafka + Flink + Spark | 실시간 스트리밍 중심 |
| **중소 이커머스** | AWS 또는 GCP | BigQuery(GCP) 또는 Redshift(AWS) | 관리 편의성으로 SaaS DW 선택 |
| **스타트업** | GCP | BigQuery + Looker Studio | 서버리스, 초기 비용 없음 |

### 1-2. 핵심 인사이트

**대기업은 BigQuery/Snowflake를 안 쓴다**
- 카카오·네이버·쿠팡은 모두 오픈소스(Spark, Presto/Trino, Hadoop) 기반 자체 플랫폼 운영
- 이유: 데이터 규모가 페타바이트급이라 SaaS DW 비용이 천문학적, 커스터마이징 필요

**중소·스타트업은 BigQuery가 현실적 선택**
- 인프라 관리 인력 불필요 (서버리스)
- GCP 메인 사용 기업이라면 BigQuery가 자연스러운 선택
- 한국 채용 JD에서 BigQuery 언급 빈도 ↑

**한국 클라우드 시장 점유율 (2023년)**
- AWS 약 60% → Spark/Presto/Redshift 스택
- Azure 약 24%
- GCP 약 20% → BigQuery 스택
- NAVER Cloud 약 20% (국내 자체)

> 출처: Coupang Engineering Blog, NAVER Career 공식 채용 페이지

---

## 2. Google BigQuery 과금 구조 (2025년 기준)

### 2-1. 쿼리 비용

| 항목 | 내용 |
|---|---|
| 무료 한도 | **월 1 TiB (≈ 1,099 GB)** 영구 무료 |
| 초과 단가 | **$6.25 / TiB** (≈ $0.0061 / GB) |
| 과금 기준 | **스캔한 데이터 용량** (결과 행 수 아님) |

> BigQuery는 컬럼형(Columnar) 스토리지 → SELECT * 하면 모든 컬럼 읽음 → 불필요한 비용 발생

### 2-2. 스토리지 비용

| 구분 | 단가 | 무료 한도 |
|---|---|---|
| Active Storage (90일 이내 수정) | $0.023 / GB / 월 | 월 10 GB 무료 |
| Long-term Storage (90일+ 미수정) | $0.016 / GB / 월 | 동일 |

### 2-3. 신규 가입 혜택

- **BigQuery Sandbox**: 신용카드 없이 Google 계정만으로 사용 가능
- **신규 GCP 가입**: $300 무료 크레딧 (90일)

---

## 3. 이 프로젝트의 예상 데이터 크기 & 비용

### 3-1. 테이블별 예상 크기

| 테이블 | 행 수 | 예상 크기 |
|---|---|---|
| `users` | 50,000 | ~5–8 MB |
| `gifts` (거래 로그) | ~180,000 | ~25–35 MB |
| `gift_receipts` (수신 기록) | ~180,000 | ~20–30 MB |
| `campaigns` | ~24건 | ~0.1 MB |
| `campaign_logs` | ~60,000 | ~8–12 MB |
| **총합** | **~490,000행** | **~60–85 MB** |

### 3-2. 쿼리 비용 시뮬레이션

| 쿼리 유형 | 예상 스캔량 | 예상 비용 |
|---|---|---|
| `SELECT * FROM gifts` (풀 스캔) | ~35 MB | **$0.0002** |
| 3개 테이블 JOIN (RFM 계산) | ~100 MB | **$0.0006** |
| 월간 분석 쿼리 100회 실행 | ~5 GB | **$0.03** |
| **무료 한도 소진까지** | **1,024 GB** | 수만 번 쿼리 가능 |

**결론: 이 프로젝트는 사실상 비용 $0으로 운영 가능**

---

## 4. BigQuery 비용 최적화 Best Practices

### 4-1. 파티셔닝 (Partitioning) — 날짜 기준 분할

```sql
-- 테이블 생성 시 파티셔닝 적용
CREATE TABLE kakao_gift.gifts
PARTITION BY DATE(gift_timestamp)
AS SELECT * FROM ...;

-- 쿼리 시 반드시 파티션 필터 포함
SELECT sender_id, amount, category
FROM kakao_gift.gifts
WHERE DATE(gift_timestamp) BETWEEN '2024-01-01' AND '2024-03-31';
-- → 해당 기간 파티션만 읽음 (전체 대비 약 75% 비용 절감)
```

### 4-2. 클러스터링 (Clustering) — 자주 필터링하는 컬럼 기준 정렬

```sql
-- 파티셔닝 + 클러스터링 동시 적용
CREATE TABLE kakao_gift.gifts
PARTITION BY DATE(gift_timestamp)
CLUSTER BY category, sender_segment
AS SELECT * FROM ...;

-- 클러스터 컬럼을 WHERE에 포함 시 블록 프루닝 효과
SELECT *
FROM kakao_gift.gifts
WHERE DATE(gift_timestamp) = '2024-11-11'  -- 빼빼로데이
  AND category = 'snack';
```

### 4-3. SELECT * 금지

```sql
-- 나쁜 예: 컬럼 20개 × 전체 행 스캔
SELECT * FROM kakao_gift.gifts;

-- 좋은 예: 필요한 컬럼만
SELECT sender_id, receiver_id, amount, gift_timestamp
FROM kakao_gift.gifts;
-- → 최대 80~90% 비용 절감 가능
```

### 4-4. Dry Run — 실행 전 비용 확인

**방법 1: BigQuery Console UI**
→ 쿼리 입력 후 우측 상단에 "이 쿼리는 X.X GB를 처리합니다" 자동 표시

**방법 2: Python**
```python
from google.cloud import bigquery

client = bigquery.Client()
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)

query = """
SELECT sender_id, SUM(amount) as total_spend
FROM kakao_gift.gifts
WHERE DATE(gift_timestamp) >= '2024-01-01'
GROUP BY sender_id
"""

job = client.query(query, job_config=job_config)
print(f"예상 스캔 용량: {job.total_bytes_processed / 1e6:.2f} MB")
print(f"예상 비용: ${job.total_bytes_processed / 1e12 * 6.25:.6f}")
```

### 4-5. 캐시 활용

- 동일 쿼리를 24시간 내 재실행 시 캐시 반환 → **비용 $0**
- 조건: 쿼리 텍스트 동일 + 테이블 데이터 미변경

### 4-6. Preview 탭 활용

- BigQuery Console에서 테이블 클릭 후 **"Preview" 탭** = 완전 무료
- 데이터 구조 확인할 때는 항상 Preview 먼저

### 4-7. 일일 비용 상한선 설정 (안전망)

```
Google Cloud Console > BigQuery > Settings > Custom quotas
→ 1일 최대 스캔량 제한 설정 가능 (예: 10 GB/일)
→ 실수로 대규모 쿼리 실행해도 과금 방지
```

---

## 5. BigQuery vs Snowflake — 포트폴리오 관점 비교

| 항목 | BigQuery | Snowflake |
|---|---|---|
| 무료 쿼리 | **월 1 TB 영구 무료** | 없음 (트라이얼만) |
| 무료 스토리지 | **월 10 GB 영구 무료** | 없음 |
| 트라이얼 | $300 크레딧 | $400 크레딧, **30일 제한** |
| 신용카드 | Sandbox는 불필요 | 필요 |
| 트라이얼 후 | 무료 티어 계속 사용 | 계정 중지 |
| 한국 JD 출현 빈도 | **높음** | 낮음 |
| Looker Studio 연동 | **무료 연동 가능** | 유료 |
| 아키텍처 | Serverless | Storage-Compute 분리 |
| 글로벌 기업 타겟 | △ | ✅ |

**→ 한국 기업 취업 포트폴리오: BigQuery 추천**

---

## 6. 면접 어필 포인트

이 프로젝트에서 아래 내용을 경험했다고 어필 가능:

1. **"파티셔닝/클러스터링을 적용해 쿼리 비용을 최소화하는 테이블을 설계했습니다"**
2. **"Dry Run으로 실행 전 비용을 확인하는 습관을 들였습니다"**
3. **"BigQuery의 컬럼형 스토리지 특성을 이해하고 SELECT * 대신 필요한 컬럼만 명시했습니다"**
4. **"대기업(카카오·네이버)은 Spark+Presto 기반 자체 플랫폼을, 스타트업은 BigQuery/Redshift를 사용한다는 실무 맥락을 파악했습니다"**

---

> Sources:
> - Coupang Engineering Blog (Medium)
> - NAVER Career — AI Data Platform
> - Google Cloud BigQuery Pricing (공식)
> - DataCamp — BigQuery vs Snowflake
> - e6data — BigQuery Cost Optimization 2025
> - dbt Labs — Reduce BigQuery Costs
