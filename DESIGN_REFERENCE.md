# 데이터 분석 프레젠테이션 디자인 레퍼런스

> 조사일: 2026-04-04
> 출처: Google Design, SlideWorks, McKinsey/BCG 공개 자료, Netflix Tech Blog, Airbnb Engineering Blog

---

## 1. 조직별 스타일 요약

| 조직 | 주색 | 배경 | 폰트 | 핵심 철학 |
|---|---|---|---|---|
| **McKinsey** | `#2251FF` (Blue) | `#FFFFFF` | Georgia / Arial | 심플 화이트 + 파란 강조. 슬라이드 제목 = 완전한 문장. SCQA 구조 |
| **BCG** | `#29BA74` (Green) | `#FFFFFF` | Trebuchet MS | 정보 밀도 높음. Pyramid Principle. 핵심 데이터에 초록 강조 |
| **Google** | Material Primary | `#FFFFFF` | System (Material) | 데이터-잉크 비율 최대화. 접근성(WCAG) 필수. Chart Junk 금지 |
| **Apple** | Brand-based | `#FFFFFF` | San Francisco | 극도 미니멀. 슬라이드당 숫자 1개. 불필요한 모든 요소 제거 |
| **Netflix** | `#E50914` (Red) | `#221F1F` (Dark) | Hawkins (사내) | Quantile 기반 시각화. 콘텐츠 우선. 통계적 명확성 |
| **Airbnb** | `#FF5A5F` (Rausch) | `#FFFFFF` | Cereal (사내) | 따뜻함 + 인터랙티브. Superset 기반 대시보드 |

---

## 2. 핵심 디자인 원칙 (공통)

### 색상
- **강조색은 1~2개만** — McKinsey(파랑), BCG(초록), Apple(거의 없음)
- 강조색은 **인사이트/핵심 수치에만** 사용 (장식용 사용 금지)
- **색각이상 고려**: 빨강+초록 동시 사용 지양, WCAG AA 이상

### 타이포그래피
- **폰트 최대 2종** (헤드라인 + 본문)
- 위계: 헤드라인 > 서브헤드 > 본문 > 캡션 (크기+굵기로만 구분)
- 슬라이드 제목은 **완전한 문장** (라벨 아님) — McKinsey/BCG 공통 원칙

### 차트
- **데이터-잉크 비율 최대화** (Google 원칙) — 그리드라인 최소화
- 범례 대신 **직접 라벨(Direct Label)** 사용
- 차트 제목은 **인사이트 문장** ("매출 추세" ✗ → "2024년 GMV +31% 성장" ✓)

### 레이아웃
- **한 슬라이드 = 한 메시지**
- 넓은 여백(Whitespace) 활용
- 왼쪽 상단 → 오른쪽 하단 시선 흐름 고려
- **Pyramid Principle (BCG)**: 결론 먼저 → 근거 → 데이터 순

---

## 3. 카카오 선물하기 프로젝트 디자인 방향

### 색상 팔레트

```
Primary:   #1A1A2E  (딥 네이비 — 신뢰/전문성)
Accent:    #FEE500  (카카오 옐로우 — 브랜드 연결)
Highlight: #2251FF  (McKinsey Blue — 핵심 수치 강조)
Success:   #29BA74  (BCG Green — 긍정 지표)
Danger:    #FF5A5F  (Airbnb Red — 이탈/위험 세그먼트)
BG:        #FFFFFF  (흰색 배경)
Text:      #1A1A2E  (딥 네이비)
Muted:     #6B7280  (회색 — 보조 텍스트)
```

### 타이포그래피
```
Headline:  Pretendard Bold  (한글 지원 최적 — Google Noto Sans 대체 가능)
Body:      Pretendard Regular
Accent:    IBM Plex Mono  (수치/코드 강조용)
```

### 슬라이드 원칙
1. **McKinsey식 타이틀**: 각 슬라이드 제목 = 핵심 인사이트 1문장
2. **BCG식 논리 구조**: 결론(Takeaway) → 근거 차트 → 세부 데이터
3. **Google식 차트**: 그리드 최소화, 직접 라벨, 데이터-잉크 비율 최대화
4. **Apple식 숫자 강조**: 핵심 KPI는 크게(72pt+), 맥락은 작게

### 슬라이드별 컴포넌트 구조
```
[Header Bar]   슬라이드 번호 + 섹션명
[Title]        핵심 인사이트 문장 (Pretendard Bold 28pt)
[Takeaway Box] 한 줄 결론 (카카오 옐로우 배경, 굵게)
[Chart Area]   메인 시각화 (70% 공간)
[Footnote]     데이터 출처 / 가정 (8pt, 회색)
```

---

## 4. 차트 도구 선택 기준

| 차트 유형 | 도구 | 이유 |
|---|---|---|
| 시계열 GMV 트렌드 | Plotly (`go.Scatter`) | 인터랙티브 + HTML 삽입 가능 |
| 코호트 히트맵 | Seaborn (`heatmap`) | 색상 그라데이션이 직관적 |
| RFM 세그먼트 분포 | Plotly (`go.Treemap`) | 비율과 계층 동시 표현 |
| 캠페인 성과 바차트 | Plotly (`go.Bar`) | 그룹 비교에 최적 |
| 퍼널 분석 | Plotly (`go.Funnel`) | 전환율 시각화 표준 |
| KPI 카드 | python-pptx (텍스트박스) | PPTX 슬라이드 직접 삽입 |

---

## 5. 참고 자료

- [Google: Six Principles for Designing Any Chart](https://medium.com/google-design/redefining-data-visualization-at-google-9bdcf2e447c6)
- [McKinsey Visual Identity 해석](https://slideworks.io/resources/decoding-mckinseys-visual-identity-and-powerpoint-template)
- [BCG 슬라이드 접근법](https://slideworks.io/resources/bcg-approach-to-great-slides-practical-guide-from-former-consultant)
- [Apple 발표 기법](https://www.inc.com/carmine-gallo/apples-top-leaders-use-this-simple-presentation-hack-to-make-their-slides-instantly-memorable.html)
- [Netflix Hawkins 디자인 시스템](https://netflixtechblog.com/hawkins-diving-into-the-reasoning-behind-our-design-system-964a7357547)
- [Airbnb Cereal 타이포그래피](https://medium.com/airbnb-design/working-type-81294544608b)
- [Storytelling with Data (Cole Nussbaumer Knaflic)](https://www.storytellingwithdata.com/)
