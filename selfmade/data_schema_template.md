# 데이터 스키마 설계 템플릿

> 새로운 프로젝트에서 테이블을 설계할 때 이 파일을 Claude에게 참조시키고 아래 프롬프트를 사용할 것.

---

## 사용법

Claude에게 테이블 설계를 요청할 때 이 파일을 첨부하거나 내용을 붙여넣고 아래 프롬프트를 사용한다.

---

## 데이터 스키마 설계 요청 프롬프트 템플릿

```
[이 파일(data_schema_template.md)의 설계 조건을 모두 준수하여 아래 프로젝트의 데이터 테이블 스키마를 설계해줘.]

## 프로젝트 컨텍스트
- 서비스명: _______________
- 분석 목적: _______________ (예: RFM 세그멘테이션 / A/B 테스트 / 퍼널 분석 / LTV 코호트 등)
- 기술 스택: _______________ (예: BigQuery + Python + Jupyter)
- 데이터 기간: _______________
- 예상 행 수: _______________ (테이블별)
- 핵심 분석 지표(KPI): _______________

## 이 서비스의 고유한 구조
(일반 이커머스와 다른 점, 특수한 관계 등 자유 기술)
_______________
```

---

## 설계 조건 (Claude가 반드시 준수할 원칙)

### 1. 정규화 (Normalization)
- raw 테이블에 파생값(집계 결과) 넣지 말 것
  - 파생값 예시: `total_sent_count`, `first_sent_at` 처럼 다른 테이블에서 COUNT/MIN으로 계산 가능한 값
  - 이런 값은 분석용 집계 뷰(View) 또는 쿼리로 처리
- 단, 포트폴리오 분석 편의를 위해 비정규화가 명백히 유리한 경우 → 이유 명시 후 허용하고 목록화

### 2. 정합성 (Consistency)
- 같은 개념을 표현하는 컬럼이 두 테이블에 중복되지 않을 것
  - 중복 예시: `orders.created_at`과 `gift_receipts.sent_at`이 같은 시각이면 하나 제거
- FK 관계가 있는 모든 컬럼 명시 (어느 테이블의 어느 컬럼을 참조하는지)
- NULL 허용 여부와 그 이유를 각 컬럼에 명시

### 3. 무결성 (Integrity)
- 상태값(status) 컬럼은 테이블별 관점을 명확히 분리할 것
  - 예: `order_status`=결제 관점, `receipt_status`=수신자 행동 관점
- BOOL 컬럼은 반드시 파생 조건을 명시할 것
  - 예: `is_viral_converted = (first_received_at < first_sent_at)`
- 동기화 위험이 있는 컬럼(파생값을 raw에 둔 경우)은 주석으로 명시

### 4. 택소노미 (Taxonomy)
- 카테고리성 STRING 컬럼은 반드시 전체 허용값(enum) 목록을 설계 단계에서 확정할 것
  - "등" 또는 "예시" 로 얼버무리지 말고 전체 값 목록 확정
- 계층 구조가 있는 경우(대분류→중분류→세부값) 3단 계층으로 설계하고 매핑표 포함
- 값 네이밍 규칙 통일:
  - 케이스: `snake_case` 전체
  - 이벤트명: `verb_object` 패턴 (예: `send_gift`, `accept_gift`)
  - 타임스탬프: `_at` suffix (예: `created_at`, `accepted_at`)
  - 금액: `_krw` suffix (예: `total_amount_krw`)
  - ID: `_id` suffix
  - 비율: `_rate` / `_cvr` / `_ctr`
  - 불리언: `is_` prefix
  - 카운트: `_count` suffix
  - 세그먼트: `_segment` suffix

### 5. 분석 가능성 검증 (설계 완료 후 체크리스트)
설계 후 아래 항목을 체크리스트로 확인하고 커버 여부를 표로 제출할 것:

- [ ] 핵심 KPI 각각 어느 테이블·컬럼으로 계산하는지 매핑
- [ ] 발신자/수신자(또는 행위자 간) 추적 JOIN 경로
- [ ] 퍼널 단계별 이벤트 추적 가능 여부
- [ ] 시계열 분석 (Daily/MoM/YoY) 가능 여부
- [ ] 세그먼트 분석 (연령/성별/채널별) 가능 여부
- [ ] 중복 컬럼 없음 확인
- [ ] 파생값 raw 테이블 미포함 확인

---

## 산출물 형식 (Claude가 반드시 이 순서로 제출)

1. **ERD 설명** — 테이블 간 관계 텍스트 요약 (1:1 / 1:N 관계)
2. **테이블별 컬럼 정의표** — 아래 형식 준수

   | # | 컬럼명 | 타입 | NULL | 허용값(enum) | 설명 | 분석 용도 |
   |---|---|---|---|---|---|---|

3. **택소노미 매핑표** — 계층형 카테고리 컬럼 전체 값 목록
4. **분석 가능성 체크리스트** — KPI별 커버 여부 표
5. **비정규화 항목 목록** — raw에 파생값을 넣은 경우 이유 명시
6. **집계 뷰 예시 쿼리** — 정규화로 제거된 파생값을 계산하는 SQL
7. **dbdiagram.io DBML 코드** — ERD 시각화용

---

## 과거 적용 사례

### 카카오톡 선물하기 (2026-04)
- 파일 위치: `c:/Users/user/Desktop/pjt/portfolio/kakao_gift/PLAN.md`
- 테이블 5개: `users`, `orders`, `gift_receipts`, `campaigns`, `campaign_logs`
- 주요 설계 결정:
  - `joined_at`, `total_sent_count` 등 파생값 → raw 제거, 집계 뷰로 처리
  - `gift_receipts.sent_at` 삭제 (orders.created_at과 중복)
  - occasion 3단 계층: `occasion_category(special/daily)` → `occasion_subcategory` → `gift_occasion(21개)`
  - `is_anonymous` → `is_code_gift`로 rename (카카오 코드선물 기능 반영)
  - campaign channel: `friendtalk` / `brand_message` / `in_app_message` (alimtalk은 트랜잭션용이라 제외)
